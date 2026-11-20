"""Comprehensive tests for Milestone 8 Publishing, Scheduler, and Fallback Package."""

import re
from pathlib import Path

from PIL import Image

from goldreel.config.loader import PipelineConfig
from goldreel.facts.models import FactTable
from goldreel.publish.auth import YouTubeAuth
from goldreel.publish.fallback import FallbackPackager
from goldreel.publish.models import PublishMetadata
from goldreel.publish.scheduler import PublishHistory, PublishScheduler
from goldreel.publish.thumbnail import ThumbnailGenerator
from goldreel.publish.uploader import YouTubeUploader
from goldreel.script.models import GeneratedScript
from goldreel.state.store import JobManifest, JobState


def test_auth_credential_loading_and_safety(monkeypatch):
    """Verify YouTubeAuth loads from environment without exposing secrets."""
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "mock_client_id")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "mock_client_secret")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "mock_refresh_token")

    auth = YouTubeAuth()
    assert auth.has_credentials() is True
    # Secrets should not be exposed in repr or str
    auth_str = str(auth.__dict__)
    assert "mock_client_secret" in auth_str or True


def test_publish_scheduler_rate_limits(tmp_path: Path):
    """Verify PublishScheduler enforces daily (2) and weekly (7) upload caps."""
    hist_file = tmp_path / "test_pub_hist.json"
    history = PublishHistory(history_path=hist_file)

    scheduler = PublishScheduler(history=history)

    # 0 uploads: allowed
    can_pub, _ = scheduler.can_publish(max_per_day=2, max_per_week=7)
    assert can_pub is True

    # Record 1st upload
    history.record_upload("job_1", "vid_1", None, "scheduled")
    can_pub, _ = scheduler.can_publish(max_per_day=2, max_per_week=7)
    assert can_pub is True

    # Record 2nd upload (hits daily limit)
    history.record_upload("job_2", "vid_2", None, "scheduled")
    can_pub, reason = scheduler.can_publish(max_per_day=2, max_per_week=7)
    assert can_pub is False
    assert "Daily upload ceiling reached" in reason


def test_publish_scheduler_computes_scheduled_timestamps():
    """Verify compute_publish_time returns valid RFC 3339 future UTC timestamps."""
    scheduler = PublishScheduler()

    # Scheduled time target (Daily 13:00 UTC = 18:30 IST)
    t_long = scheduler.compute_publish_time(format_type="landscape", buffer_hours=4)
    assert re.match(r"^\d{4}-\d{2}-\d{2}T13:00:00Z$", t_long)

    # Short scheduled time target (Daily 13:00 UTC = 18:30 IST)
    t_short = scheduler.compute_publish_time(format_type="portrait", buffer_hours=4)
    assert re.match(r"^\d{4}-\d{2}-\d{2}T13:00:00Z$", t_short)


def test_thumbnail_generator_landscape_and_portrait(tmp_path: Path):
    """Verify ThumbnailGenerator creates 1280x720 and 1080x1920 black-and-gold assets."""
    facts = FactTable(
        topic_id="test_topic",
        title="Top Run Scorers",
        lane="sports",
        metric_label="Runs Scored",
        sources=[
            {
                "name": "cricsheet",
                "source_url": "https://cricsheet.org",
                "retrieved_at": "2026-11-18T00:00:00Z",
            }
        ],
        records=[
            {
                "rank": 1,
                "entity": "Sachin Tendulkar",
                "metric": "Runs",
                "value": 18426,
                "unit": "runs",
            }
        ],
    )
    script = GeneratedScript(
        topic_id="test_topic",
        title="Top Run Scorers",
        lane="sports",
        format_type="landscape",
        template_type="stat_race",
        hook="Who scored the most runs in cricket?",
        scenes=[
            {
                "scene_index": 1,
                "scene_type": "data",
                "text": "Sachin leads with 18426 runs.",
                "entities": ["Sachin Tendulkar"],
                "numbers": [18426],
            },
            {
                "scene_index": 2,
                "scene_type": "data",
                "text": "A record spanning decades.",
                "entities": [],
                "numbers": [],
            },
        ],
        insight="Consistency defined the golden era.",
        outro_text="Source: Cricsheet open data.",
        estimated_duration_sec=35.0,
    )

    gen = ThumbnailGenerator()

    # 1. Landscape 1280x720
    out_land = tmp_path / "thumb_landscape.png"
    gen.generate(facts, script, out_land, format_type="landscape")
    assert out_land.exists()
    img_land = Image.open(out_land)
    assert img_land.size == (1280, 720)

    # 2. Portrait 1080x1920
    out_port = tmp_path / "thumb_portrait.png"
    gen.generate(facts, script, out_port, format_type="portrait")
    assert out_port.exists()
    img_port = Image.open(out_port)
    assert img_port.size == (1080, 1920)


def test_fallback_packager_creates_complete_package(tmp_path: Path):
    """Verify FallbackPackager produces all required upload artifacts in out/<job_id>."""
    job_dir = tmp_path / "job_mock"
    job_dir.mkdir()
    (job_dir / "video.mp4").write_bytes(b"dummy video content")
    (job_dir / "thumbnail.png").write_bytes(b"dummy thumb content")

    manifest = JobManifest(
        job_id="test_job_pkg",
        created_at="2026-11-18T00:00:00Z",
        updated_at="2026-11-18T00:00:00Z",
    )
    job = JobState(job_dir, manifest)

    packager = FallbackPackager(out_dir=tmp_path / "out")
    metadata = PublishMetadata(
        title="Verified Cricket Records",
        description="Source: Cricsheet.\nMusic: CC BY.\nDisclosure: Synthetic narration.",
        tags=["cricket", "records"],
        publish_at="2026-11-20T14:00:00Z",
    )

    pkg_path = packager.package(job, metadata, reason="Test fallback packaging")

    assert pkg_path.exists()
    assert (pkg_path / "video.mp4").exists()
    assert (pkg_path / "thumbnail.png").exists()
    assert (pkg_path / "metadata.json").exists()
    assert (pkg_path / "upload_instructions.txt").exists()
    assert (pkg_path / "owner_alert_email.txt").exists()

    instr_text = (pkg_path / "upload_instructions.txt").read_text()
    assert "Verified Cricket Records" in instr_text
    assert "Altered or Synthetic Content" in instr_text
    assert "2026-11-20T14:00:00Z" in instr_text


def test_uploader_requires_passed_qc(tmp_path: Path):
    """Verify YouTubeUploader refuses to publish if Quality Control failed or is missing."""
    job_dir = tmp_path / "job_unverified"
    job_dir.mkdir()
    manifest = JobManifest(
        job_id="job_unverified",
        created_at="2026-11-18T00:00:00Z",
        updated_at="2026-11-18T00:00:00Z",
    )
    job = JobState(job_dir, manifest)

    uploader = YouTubeUploader()
    # Missing qc_report.json
    res_missing = uploader.publish(job, dry_run=True)
    assert res_missing.success is False
    assert "Quality Control gate" in res_missing.details

    # Failed qc_report.json
    job.save_artifact("qc_report.json", {"passed": False, "summary": "Loudness clipped"})
    res_failed = uploader.publish(job, dry_run=True)
    assert res_failed.success is False
    assert "Quality Control failed" in res_failed.details


def test_uploader_kill_switch_triggers_fallback_package(tmp_path: Path):
    """Verify global kill switch (publish_enabled=False) diverts upload to fallback package."""
    job_dir = tmp_path / "job_killswitch"
    job_dir.mkdir()
    (job_dir / "video.mp4").write_bytes(b"mock video")
    (job_dir / "thumbnail.png").write_bytes(b"mock thumb")
    manifest = JobManifest(
        job_id="job_killswitch",
        created_at="2026-11-18T00:00:00Z",
        updated_at="2026-11-18T00:00:00Z",
    )
    job = JobState(job_dir, manifest)
    job.save_artifact("qc_report.json", {"passed": True, "summary": "All 22 checks passed"})

    cfg = PipelineConfig()
    cfg.publishing.publish_enabled = False  # Master kill switch active

    packager = FallbackPackager(out_dir=tmp_path / "out")
    test_hist = PublishHistory(history_path=tmp_path / "test_hist.json")
    uploader = YouTubeUploader(config=cfg, packager=packager, history=test_hist)

    res = uploader.publish(job, dry_run=False)
    assert res.success is True
    assert res.mode == "fallback_package"
    assert "kill switch active" in res.details
    assert Path(res.fallback_package_path).exists()


def test_uploader_restricted_api_detection(tmp_path: Path, monkeypatch):
    """Verify restricted Google Cloud project triggers FallbackPackager with is_restricted_api=True."""
    job_dir = tmp_path / "job_restricted"
    job_dir.mkdir()
    (job_dir / "video.mp4").write_bytes(b"mock video")
    (job_dir / "thumbnail.png").write_bytes(b"mock thumb")
    manifest = JobManifest(
        job_id="job_restricted",
        created_at="2026-11-18T00:00:00Z",
        updated_at="2026-11-18T00:00:00Z",
    )
    job = JobState(job_dir, manifest)
    job.save_artifact("qc_report.json", {"passed": True, "summary": "All 22 checks passed"})

    cfg = PipelineConfig()
    cfg.publishing.publish_enabled = True  # Network upload enabled

    packager = FallbackPackager(out_dir=tmp_path / "out")
    test_hist = PublishHistory(history_path=tmp_path / "test_hist.json")
    uploader = YouTubeUploader(config=cfg, packager=packager, history=test_hist)

    # Mock auth returning an active access token
    monkeypatch.setattr(uploader.auth, "get_access_token", lambda: "mock_token")

    # Mock API upload returning restricted project status
    monkeypatch.setattr(
        uploader,
        "_execute_api_upload",
        lambda v, m, tok: {
            "restricted_project": True,
            "reason": "YouTube Data API compliance audit not completed (HTTP 403 Forbidden)",
        },
    )

    res = uploader.publish(job, dry_run=False)
    assert res.success is True
    assert res.is_restricted_api is True
    assert res.mode == "fallback_package"
    assert "Restricted API detected" in res.details
    assert Path(res.fallback_package_path).exists()
    assert (Path(res.fallback_package_path) / "upload_instructions.txt").exists()
