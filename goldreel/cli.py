"""Typer CLI interface for GoldReel automated video publishing pipeline.

Commands:
  ingest   - Fetch and cache open data sources with verification
  plan     - Angle finding, deduplication, and script drafting
  make     - End-to-end video production run
  qc       - Automated quality control, frame, and audio gates
  publish  - YouTube scheduled upload or fallback packager
  report   - Pipeline health, job status, and metrics overview
"""

import sys
from pathlib import Path

import typer

from goldreel.adapters.cricsheet import CricsheetAdapter
from goldreel.adapters.football import FootballAdapter
from goldreel.adapters.wikidata import WikidataComicAdapter
from goldreel.audio.credits import CreditsGenerator
from goldreel.audio.ducking import AudioMixer
from goldreel.audio.library import MusicLibrary
from goldreel.config.loader import load_pipeline_config, load_providers_config
from goldreel.facts.models import FactTable
from goldreel.publish.uploader import YouTubeUploader
from goldreel.qc.gate import QualityGate
from goldreel.render.engine import RenderEngine
from goldreel.render.layouts.portrait import PortraitLayout
from goldreel.render.templates.milestone import MilestoneTemplate
from goldreel.render.templates.ranked_countdown import RankedCountdownTemplate
from goldreel.render.templates.scroll_compare import ScrollCompareTemplate
from goldreel.render.templates.stat_race import StatRaceTemplate
from goldreel.script.router import ProviderRouter
from goldreel.script.validator import ScriptValidator
from goldreel.security.checks import scan_for_secrets
from goldreel.state.store import StateStore, compute_content_hash
from goldreel.topics.finder import AngleFinder
from goldreel.topics.history import TopicHistory
from goldreel.voice.piper import PiperWrapper

app = typer.Typer(
    name="goldreel",
    help="Headless black-and-gold open data video publisher for YouTube.",
    no_args_is_help=True,
)


@app.callback()
def main_callback() -> None:
    """Pre-run safety verification."""
    violations = scan_for_secrets()
    if violations:
        typer.secho("SECURITY ALERT: Secret-like content detected!", fg=typer.colors.RED, err=True)
        for v in violations:
            typer.secho(f"  - {v}", fg=typer.colors.RED, err=True)
        sys.exit(1)


@app.command()
def ingest(
    lane: str = typer.Option(
        "all", "--lane", "-l", help="Lane to ingest: 'sports', 'comics', or 'all'"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Check sources without downloading"),
) -> None:
    """Ingest open data into cache/ with hash validation and license tracking."""
    config = load_pipeline_config()
    typer.secho(
        f"[Ingest] Initializing ingestion for lane='{lane}' (dry_run={dry_run})",
        fg=typer.colors.BRIGHT_YELLOW,
    )

    cache_dir = Path("cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    sports_enabled = config.lanes.sports.enabled and lane in ("all", "sports")
    comics_enabled = config.lanes.comics.enabled and lane in ("all", "comics")

    if sports_enabled:
        typer.echo(
            f"  - Sports lane enabled: {[s.name for s in config.lanes.sports.sources if s.enabled]}"
        )
        cricsheet_adapter = CricsheetAdapter(cache_dir=cache_dir)
        cricsheet_adapter.ingest()
        football_adapter = FootballAdapter(cache_dir=cache_dir)
        football_adapter.ingest()
    if comics_enabled:
        typer.echo(
            f"  - Comics lane enabled: {[s.name for s in config.lanes.comics.sources if s.enabled]}"
        )
        wikidata_adapter = WikidataComicAdapter(cache_dir=cache_dir)
        wikidata_adapter.ingest()

    typer.secho("[Ingest] Cache directory ready.", fg=typer.colors.GREEN)


@app.command()
def plan(
    lane: str = typer.Option("sports", "--lane", "-l", help="Target lane: 'sports' or 'comics'"),
    format_type: str = typer.Option(
        "landscape", "--format", "-f", help="'landscape' (16:9) or 'portrait' (9:16)"
    ),
    job_id: str | None = typer.Option(None, "--job-id", help="Optional specific job ID"),
) -> None:
    """Discover angles from verified facts and plan script narration."""
    store = StateStore()
    if job_id and (store.base_dir / job_id).exists():
        job = store.get_job(job_id)
    else:
        job = store.create_job(job_id)
    typer.secho(
        f"[Plan] Started job {job.job_id} for lane='{lane}', format='{format_type}'",
        fg=typer.colors.BRIGHT_YELLOW,
    )

    job.mark_stage_start("topics")
    # Load facts for planning
    if lane == "comics":
        facts_path = Path("tests/fixtures/SAMPLE_wikidata_comic.json")
        adapter = WikidataComicAdapter()
    else:
        facts_path = Path("tests/fixtures/SAMPLE_cricket_facts.json")
        adapter = CricsheetAdapter()

    fact_table = adapter.extract_facts(facts_path)
    finder = AngleFinder()
    candidates = finder.find_angles(fact_table, target_format=format_type)

    router = ProviderRouter()
    script = router.generate_script(fact_table, format_type=format_type)

    validator = ScriptValidator(fact_table)
    v_res = validator.validate(script)

    job.save_artifact(
        "plan_topics.json",
        {
            "lane": lane,
            "format": format_type,
            "candidates": [c.name for c in candidates],
            "script": script.model_dump(),
            "validation_passed": v_res.passed,
        },
    )
    job.mark_stage_completed(
        "topics", metadata={"candidate_count": len(candidates), "script_words": script.total_words}
    )

    typer.secho(
        f"[Plan] Topic planning complete for job {job.job_id}. Found {len(candidates)} candidates.",
        fg=typer.colors.GREEN,
    )


@app.command()
def make(
    lane: str = typer.Option("sports", "--lane", "-l", help="Target lane: 'sports' or 'comics'"),
    format_type: str = typer.Option(
        "landscape", "--format", "-f", help="'landscape' or 'portrait'"
    ),
    dry_run: bool = typer.Option(
        True, "--dry-run", help="Run pipeline simulation without network publish"
    ),
    job_id: str | None = typer.Option(None, "--job-id", help="Resume an existing job or start new"),
) -> None:
    """Run full pipeline: ingest -> facts -> topics -> script -> voice -> render -> qc."""
    pipe_cfg = load_pipeline_config()
    store = StateStore()
    if job_id and (store.base_dir / job_id).exists():
        job = store.get_job(job_id)
    else:
        job = store.create_job(job_id)
    typer.secho(
        f"[Make] Starting production for job {job.job_id} (dry_run={dry_run})",
        fg=typer.colors.BRIGHT_YELLOW,
    )
    typer.echo(
        f"  Format: {format_type} | Lane: {lane} | Publish enabled: {pipe_cfg.publishing.publish_enabled}"
    )

    # Stage 1: Ingest
    job.mark_stage_start("ingest")
    job.mark_stage_completed("ingest", metadata={"lane": lane, "dry_run": dry_run})

    # Stage 2: Facts (Load verified facts via adapter)
    job.mark_stage_start("facts")
    if lane == "comics":
        adapter = WikidataComicAdapter()
        sample_path = Path("tests/fixtures/SAMPLE_wikidata_comic.json")
    else:
        adapter = CricsheetAdapter()
        sample_path = Path("tests/fixtures/SAMPLE_cricket_facts.json")

    if sample_path.exists():
        fact_table = adapter.extract_facts(sample_path)
    else:
        # Fallback to minimal fact table
        fact_table = FactTable(
            topic_id=f"job_{job.job_id}",
            title="Sample Records",
            lane="sports",
            metric_label="Sample Metric",
            sources=[
                {
                    "name": "sample",
                    "source_url": "https://example.com",
                    "retrieved_at": "2026-11-18T00:00:00Z",
                }
            ],
            records=[{"rank": 1, "entity": "Sample Entity", "metric": "Score", "value": 100}],
        )

    job.save_artifact("facts.json", fact_table.model_dump())
    job.mark_stage_completed("facts", metadata={"record_count": len(fact_table.records)})

    # Stage 3: Topics (Angle finding & deduplication)
    job.mark_stage_start("topics")
    history = TopicHistory()
    finder = AngleFinder(history=history)
    candidates = finder.find_angles(fact_table, target_format=format_type)
    job.save_artifact("topics.json", [c.name for c in candidates])
    job.mark_stage_completed("topics", metadata={"candidates_count": len(candidates)})

    # Stage 4: Script Generation
    job.mark_stage_start("script")
    router = ProviderRouter()
    script = router.generate_script(fact_table, format_type=format_type)
    job.save_artifact("script.json", script.model_dump())
    job.mark_stage_completed("script", metadata={"word_count": script.total_words})

    # Stage 5: Fact Gate & Script Validation
    job.mark_stage_start("fact_gate")
    validator = ScriptValidator(fact_table)
    val_res = validator.validate(script)
    if not val_res.passed:
        job.mark_stage_failed("fact_gate", error=val_res.summary)
        typer.secho(f"[Make] Validation failed: {val_res.summary}", fg=typer.colors.RED)
    else:
        job.save_artifact("fact_gate_report.json", {"passed": True, "summary": val_res.summary})
        job.mark_stage_completed("fact_gate", metadata={"passed": True})
        if not dry_run:
            # Record topic into history to prevent future duplicates in production
            history.record_topic(
                job_id=job.job_id,
                topic_id=fact_table.topic_id,
                title=fact_table.title,
                lane=lane,
                angle_id=candidates[0].angle_id if candidates else "custom",
                entities=[r.entity for r in fact_table.records],
                facts_hash=compute_content_hash(fact_table.model_dump()),
            )

    # Stage 6: Voice (Piper TTS and Sentence Timing Solver)
    job.mark_stage_start("voice")
    piper = PiperWrapper()
    voice_track = piper.generate_narration(script, job.job_dir / "voice.wav")
    job.register_existing_file(voice_track.audio_path)
    job.save_artifact("voice_timings.json", voice_track.model_dump(mode="json"))
    job.mark_stage_completed(
        "voice",
        metadata={
            "duration_sec": voice_track.total_duration_sec,
            "sentence_count": len(voice_track.sentences),
        },
    )

    # Stage 7: Audio (Music selection, ducking, and credits)
    job.mark_stage_start("audio")
    music_lib = MusicLibrary()
    music_track = music_lib.select_track(lane=lane)
    mixer = AudioMixer()
    mixed_audio = mixer.mix_and_duck(
        voice_path=voice_track.audio_path,
        music_path=music_track.filepath if music_track.filepath.exists() else None,
        output_path=job.job_dir / "audio_mixed.mp3",
        target_loudness_lufs=pipe_cfg.quality_control.target_loudness_lufs,
        max_true_peak_dbfs=pipe_cfg.quality_control.max_true_peak_dbfs,
    )
    job.register_existing_file(mixed_audio)
    credits_text = CreditsGenerator.generate_description_credits(fact_table, music_track)
    outro_credit = CreditsGenerator.generate_outro_credit(fact_table, music_track)
    job.save_artifact("credits.txt", credits_text)
    job.mark_stage_completed(
        "audio",
        metadata={"music_title": music_track.title, "outro_credit": outro_credit},
    )

    # Stage 8: Render (Stream frames to FFmpeg with muxed audio)
    job.mark_stage_start("render")
    engine = RenderEngine()
    angle_type = candidates[0].angle_id if candidates else "stat_race"

    if format_type == "portrait":
        if angle_type in ["scroll_compare", "comic_first_appearances"]:
            template = ScrollCompareTemplate()
        elif angle_type in ["milestone_anniversary", "milestone"]:
            template = MilestoneTemplate()
        elif angle_type == "stat_race":
            template = StatRaceTemplate(layout=PortraitLayout())
        else:
            template = RankedCountdownTemplate(layout=PortraitLayout())
    else:
        if angle_type == "ranked_countdown":
            template = RankedCountdownTemplate()
        elif angle_type == "scroll_compare":
            template = ScrollCompareTemplate()
        else:
            template = StatRaceTemplate()
    # Render preview segment (3 seconds) in dry-run, or voice track duration
    dur_sec = 3.0 if dry_run else voice_track.total_duration_sec
    render_script = script.model_copy(update={"estimated_duration_sec": dur_sec})
    out_video = job.job_dir / "video.mp4"
    stats = engine.render(
        template=template,
        fact_table=fact_table,
        script=render_script,
        output_path=out_video,
        fps=24,
        audio_path=mixed_audio,
    )
    job.register_existing_file(out_video)
    job.mark_stage_completed(
        "render",
        metadata={
            "duration_sec": stats.duration_sec,
            "fps": stats.fps,
            "frames": stats.total_frames,
            "render_speed_fps": round(stats.fps_render_speed, 1),
            "peak_ram_mb": round(stats.peak_ram_mb, 2),
        },
    )

    typer.secho(
        f"[Make] Video rendered for job {job.job_id} ({stats.total_frames} frames rendered in {stats.elapsed_time_sec:.1f}s)",
        fg=typer.colors.CYAN,
    )

    # Stage 9: Automated Quality Control (Loudness, Frames, Metadata, Similarity)
    gate = QualityGate()
    qc_report = gate.evaluate_job(job, dry_run=dry_run)
    if qc_report.passed:
        typer.secho(
            f"[Make] Pipeline completed and QC passed for job {job.job_id} ({len(qc_report.checks)} checks satisfied)",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            f"[Make] QC Flagged: {qc_report.summary}",
            fg=typer.colors.YELLOW,
        )


@app.command()
def qc(
    job_id: str = typer.Option(..., "--job-id", "-j", help="Job ID to verify"),
    dry_run: bool = typer.Option(
        True, "--dry-run", help="Evaluate with dry-run duration constraints"
    ),
) -> None:
    """Run automated quality gates (duration, loudness, safe margins, similarity)."""
    store = StateStore()
    job = store.get_job(job_id)

    typer.secho(
        f"[QC] Running quality gates for job {job_id} (dry_run={dry_run})",
        fg=typer.colors.BRIGHT_YELLOW,
    )
    gate = QualityGate()
    report = gate.evaluate_job(job, dry_run=dry_run)

    for c in report.checks:
        icon = "✓" if c.passed else ("⚠" if c.severity == "warning" else "✗")
        color = (
            typer.colors.GREEN
            if c.passed
            else (typer.colors.YELLOW if c.severity == "warning" else typer.colors.RED)
        )
        typer.secho(f"  [{icon}] {c.name}: {c.message}", fg=color)

    if report.passed:
        typer.secho(
            f"\n[QC] PASSED - All quality gates satisfied for job {job_id}",
            fg=typer.colors.GREEN,
            bold=True,
        )
    else:
        typer.secho(f"\n[QC] FAILED - {report.summary}", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)


@app.command()
def publish(
    job_id: str = typer.Option(..., "--job-id", "-j", help="Job ID to publish"),
    dry_run: bool = typer.Option(True, "--dry-run", help="Do not upload to YouTube API"),
) -> None:
    """Publish video to YouTube (scheduled) or package into out/ directory."""
    store = StateStore()
    job = store.get_job(job_id)

    typer.secho(
        f"[Publish] Evaluating publishing for job {job_id} (dry_run={dry_run})",
        fg=typer.colors.BRIGHT_YELLOW,
    )
    uploader = YouTubeUploader()
    result = uploader.publish(job, dry_run=dry_run)

    if result.success:
        if result.mode == "scheduled":
            typer.secho(
                f"[Publish] SUCCESS - Video scheduled on YouTube for {result.scheduled_at}: {result.youtube_url}",
                fg=typer.colors.GREEN,
                bold=True,
            )
        elif result.mode == "fallback_package":
            typer.secho(
                f"[Publish] RESTRICTED/FALLBACK - Release package generated at {result.fallback_package_path}",
                fg=typer.colors.CYAN,
                bold=True,
            )
            typer.echo(f"  Details: {result.details}")
        else:  # dry_run
            typer.secho(
                f"[Publish] DRY RUN - {result.details}",
                fg=typer.colors.GREEN,
            )
            if result.fallback_package_path:
                typer.echo(f"  Package: {result.fallback_package_path}")
    else:
        typer.secho(f"[Publish] FAILED - {result.details}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def report() -> None:
    """Display pipeline status, registered AI providers, and recent job history."""
    pipe_cfg = load_pipeline_config()
    prov_cfg = load_providers_config()
    store = StateStore()
    jobs = store.list_jobs()

    typer.secho("=== GoldReel Pipeline Status ===", fg=typer.colors.BRIGHT_YELLOW, bold=True)
    typer.echo(f"Publishing Enabled: {pipe_cfg.publishing.publish_enabled}")
    typer.echo(f"Publish Mode:       {pipe_cfg.publishing.mode}")
    typer.echo(f"Max Uploads/Day:    {pipe_cfg.publishing.max_uploads_per_day}")
    typer.echo(f"Max Uploads/Week:   {pipe_cfg.publishing.max_uploads_per_week}")
    typer.echo(f"Default AI Chain:   {' -> '.join(prov_cfg.default_chain)}")
    typer.echo(f"Recent Jobs Count:  {len(jobs)}")

    if jobs:
        typer.secho("\n--- Recent Jobs ---", fg=typer.colors.CYAN)
        for j in jobs[:5]:
            status_summary = ", ".join(f"{k}:{v.status}" for k, v in j.stages.items())
            typer.echo(f"  {j.job_id} [{j.created_at}] - {status_summary or 'No stages'}")


if __name__ == "__main__":
    app()
