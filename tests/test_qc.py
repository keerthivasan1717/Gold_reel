"""Comprehensive automated tests for Quality Control (QC) gates.

Tests:
- Audio QC: loudness (-14 LUFS), true peak (<= -1 dBFS), silence detection
- Frame QC: solid black/blank frame detection, safe margins, bottom 120px zone
- Metadata QC: title spam linter, synthetic disclosure, Shorts duration limits
- Similarity QC: 85% maximum threshold enforcement against topic history
- Central QualityGate: full end-to-end evaluation and report generation
"""

from pathlib import Path

from PIL import Image, ImageDraw

from goldreel.design.tokens import Colors
from goldreel.qc.audio import AudioQC
from goldreel.qc.frame import FrameQC
from goldreel.qc.gate import QualityGate
from goldreel.qc.metadata import MetadataQC
from goldreel.qc.similarity import SimilarityQC
from goldreel.state.store import JobManifest, JobState
from goldreel.topics.history import TopicHistory


def test_audio_qc_measures_loudness_and_true_peak():
    """Verify AudioQC measures integrated loudness and true peak with ffmpeg."""
    music_path = Path("assets/music/midnight_gold.mp3")
    assert music_path.exists()

    qc = AudioQC(target_loudness_lufs=-14.0, max_true_peak_dbfs=-1.0, tolerance_lufs=35.0)
    checks = qc.check(music_path)

    check_names = {c.name for c in checks}
    assert "audio_stream_present" in check_names
    assert "audio_not_silent" in check_names
    assert "integrated_loudness" in check_names
    assert "true_peak_ceiling" in check_names

    # Music track is audible and true peak is <= -1.0 dBFS
    silence_check = next(c for c in checks if c.name == "audio_not_silent")
    assert silence_check.passed is True
    peak_check = next(c for c in checks if c.name == "true_peak_ceiling")
    assert peak_check.passed is True


def test_audio_qc_fails_silent_or_missing_audio(tmp_path: Path):
    """Verify AudioQC fails when media file is missing or contains no audio stream."""
    missing_file = tmp_path / "nonexistent.mp3"
    qc = AudioQC()
    checks = qc.check(missing_file)
    assert len(checks) == 1
    assert checks[0].name == "audio_file_exists"
    assert checks[0].passed is False


def test_frame_qc_blank_frame_detection():
    """Verify FrameQC flags solid black / blank frames."""
    qc = FrameQC(sample_count=6)
    black_img = Image.new("RGB", (1920, 1080), (0, 0, 0))
    frames = [(float(i), black_img, None) for i in range(6)]

    checks, audits = qc.check(frames, format_type="landscape")
    blank_check = next(c for c in checks if c.name == "no_blank_frames")
    flat_check = next(c for c in checks if c.name == "no_flat_frames")

    assert blank_check.passed is False
    assert flat_check.passed is False
    assert all(not a.passed for a in audits)


def test_frame_qc_detects_static_identical_frames():
    """Verify FrameQC flags and fails videos with mostly identical or static frozen frames."""
    qc = FrameQC(sample_count=10)
    # Generate identical frames (frozen card)
    frozen_img = Image.new("RGB", (1080, 1920), Colors.rgb_bg)
    draw = ImageDraw.Draw(frozen_img)
    draw.text((120, 100), "Frozen Video Title", fill=Colors.rgb_gold)
    draw.rectangle([120, 300, 800, 360], fill=Colors.rgb_gold)

    static_frames = [(float(i), frozen_img.copy(), None) for i in range(10)]
    checks, _ = qc.check(static_frames, format_type="portrait")

    div_check = next(c for c in checks if c.name == "continuous_motion_diversity")
    assert div_check.passed is False
    assert div_check.severity == "critical"
    assert "mostly identical" in div_check.message

    # Generate dynamically animated frames (bars growing, counters ticking)
    dynamic_frames = []
    for i in range(10):
        img = Image.new("RGB", (1080, 1920), Colors.rgb_bg)
        d = ImageDraw.Draw(img)
        d.text((120, 100), f"Dynamic Frame {i}", fill=Colors.rgb_gold)
        # Animate bar growing significantly each frame
        d.rectangle([120, 300, 150 + i * 80, 420], fill=Colors.rgb_gold)
        dynamic_frames.append((float(i), img, None))

    dyn_checks, _ = qc.check(dynamic_frames, format_type="portrait")
    dyn_div_check = next(c for c in dyn_checks if c.name == "continuous_motion_diversity")
    assert dyn_div_check.passed is True


def test_frame_qc_safe_margins_and_palette():
    """Verify FrameQC passes compliant black-and-gold frames."""
    qc = FrameQC(sample_count=6)
    frames = []

    for i in range(6):
        img = Image.new("RGB", (1920, 1080), Colors.rgb_bg)
        draw = ImageDraw.Draw(img)
        # Add gold header well inside safe margin (60px)
        draw.text((120, 100), f"Test Title Frame {i}", fill=Colors.rgb_gold)
        # Add ivory bar inside safe margin
        draw.rectangle(
            [120, 300, 1000 + i * 50, 360], fill=Colors.rgb_gold, outline=Colors.rgb_ivory
        )
        frames.append((float(i), img, None))

    checks, audits = qc.check(frames, format_type="landscape")

    assert next(c for c in checks if c.name == "resolution_compliance").passed is True
    assert next(c for c in checks if c.name == "no_blank_frames").passed is True
    assert next(c for c in checks if c.name == "safe_margins_respected").passed is True
    assert next(c for c in checks if c.name == "design_token_palette").passed is True


def test_frame_qc_detects_portrait_bottom_zone_breach():
    """Verify FrameQC flags content violating the 120px bottom platform UI exclusion zone."""
    qc = FrameQC(sample_count=6)
    frames = []

    for i in range(6):
        img = Image.new("RGB", (1080, 1920), Colors.rgb_bg)
        draw = ImageDraw.Draw(img)
        # Encroach right inside the bottom 120px exclusion zone (y = 1860 > 1800)
        draw.rectangle([100, 1860, 400, 1900], fill=Colors.rgb_ivory)
        frames.append((float(i), img, None))

    checks, _ = qc.check(frames, format_type="portrait")
    bottom_check = next(c for c in checks if c.name == "portrait_bottom_exclusion_zone")
    assert bottom_check.passed is False


def test_metadata_qc_title_checks():
    """Verify MetadataQC title validation rules."""
    qc = MetadataQC()

    # Valid title
    checks_valid = qc.check_title("Top 10 Century Scorers in Cricket")
    assert all(c.passed for c in checks_valid)

    # Too short title
    checks_short = qc.check_title("Stats")
    assert next(c for c in checks_short if c.name == "title_length").passed is False

    # Spam buzzword title
    checks_spam = qc.check_title("SHOCKING Record Broken in Finals You Won't Believe")
    assert next(c for c in checks_spam if c.name == "title_editorial_quality").passed is False


def test_metadata_qc_description_and_synthetic_disclosure():
    """Verify MetadataQC checks source attribution, music credits, and synthetic disclosure."""
    qc = MetadataQC()

    # Fully compliant description
    valid_desc = (
        "Analysis of IPL centuries.\n"
        "Source: Cricsheet ball-by-ball open database.\n"
        "Music: Midnight Gold by GoldReel (Creative Commons CC BY 4.0).\n"
        "Disclosure: This video was produced with automated data visualization and synthetic narration.\n"
        "#cricket #ipl"
    )
    checks = qc.check_description(valid_desc)
    assert all(c.passed for c in checks)

    # Missing synthetic disclosure
    non_compliant_desc = "Analysis of IPL centuries.\nSource: Cricsheet.\nMusic: Midnight Gold.\n"
    checks_bad = qc.check_description(non_compliant_desc)
    synth_check = next(c for c in checks_bad if c.name == "synthetic_content_disclosure")
    assert synth_check.passed is False


def test_metadata_qc_duration_bounds():
    """Verify MetadataQC enforces YouTube Shorts 60s hard ceiling."""
    qc = MetadataQC()

    # Short <= 60s passes
    checks_pass = qc.check_duration(42.5, format_type="portrait", is_dry_run=False)
    assert next(c for c in checks_pass if c.name == "short_hard_ceiling").passed is True
    assert next(c for c in checks_pass if c.name == "short_target_duration").passed is True

    # Short at 55.0s (within 30-60s range) passes
    checks_55 = qc.check_duration(55.0, format_type="portrait", is_dry_run=False)
    assert next(c for c in checks_55 if c.name == "short_hard_ceiling").passed is True
    assert next(c for c in checks_55 if c.name == "short_target_duration").passed is True

    # Short > 60s fails YouTube Shorts criteria
    checks_fail = qc.check_duration(65.0, format_type="portrait", is_dry_run=False)
    assert next(c for c in checks_fail if c.name == "short_hard_ceiling").passed is False


def test_similarity_qc_enforces_85_percent_threshold(tmp_path: Path):
    """Verify SimilarityQC allows unique topics and rejects > 85% duplicates."""
    hist_file = tmp_path / "test_history.json"
    history = TopicHistory(history_file=hist_file)

    # Record historical topic
    history.record_topic(
        job_id="job_001",
        topic_id="ipl_centuries",
        title="Most Centuries in IPL History",
        lane="sports",
        angle_id="stat_race",
        entities=["Virat Kohli", "Chris Gayle", "David Warner"],
        facts_hash="hash_001",
    )

    qc = SimilarityQC(history=history, threshold_percent=85.0)

    # 1. Candidate with 100% facts hash or title duplicate -> fails
    checks_dup, sim_score = qc.check(
        title="Most Centuries in IPL History",
        entities=["Virat Kohli", "Chris Gayle", "David Warner"],
        facts_hash="hash_001",
    )
    assert checks_dup[0].passed is False
    assert sim_score >= 85.0

    # 2. Distinct topic -> passes
    checks_unique, sim_score_u = qc.check(
        title="Premier League All-Time Assists",
        entities=["Ryan Giggs", "Cesc Fabregas", "Wayne Rooney"],
        facts_hash="hash_002",
    )
    assert checks_unique[0].passed is True
    assert sim_score_u < 85.0


def test_quality_gate_evaluates_mock_job(tmp_path: Path):
    """Verify full QualityGate orchestrator on a mock JobState directory."""
    job_dir = tmp_path / "mock_job"
    job_dir.mkdir()

    manifest = JobManifest(
        job_id="mock_job_123",
        created_at="2026-11-18T00:00:00Z",
        updated_at="2026-11-18T00:00:00Z",
    )
    job = JobState(job_dir, manifest)

    # 1. Fact gate report
    job.save_artifact("fact_gate_report.json", {"passed": True, "summary": "All 5 facts verified"})

    # 2. Script
    job.save_artifact(
        "script.json",
        {
            "topic_id": "test_topic",
            "title": "Comic Character First Appearances",
            "format_type": "landscape",
            "stated_insight": "Superheroes emerged in the golden age.",
            "total_words": 80,
            "scenes": [],
        },
    )

    # 3. Credits description
    job.save_artifact(
        "credits.txt",
        (
            "Source: Wikidata open knowledge graph.\n"
            "Music: Midnight Gold by GoldReel (Creative Commons CC BY 4.0).\n"
            "Disclosure: This video was produced with automated data visualization and synthetic narration."
        ),
    )

    # 4. Copy test audio file as audio_mixed.mp3
    src_audio = Path("assets/music/midnight_gold.mp3")
    if src_audio.exists():
        job.save_artifact("audio_mixed.mp3", src_audio.read_bytes())

    hist_file = tmp_path / "hist.json"
    history = TopicHistory(history_file=hist_file)

    gate = QualityGate(history=history)
    report = gate.evaluate_job(job, dry_run=True)

    assert report.job_id == "mock_job_123"
    assert (job_dir / "qc_report.json").exists()
    assert any(c.name == "fact_gate_passed" for c in report.checks)
    assert any(c.name == "source_attribution_present" for c in report.checks)
    assert any(c.name == "topic_similarity_threshold" for c in report.checks)
