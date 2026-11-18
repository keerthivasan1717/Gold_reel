"""Tests for GoldReel state store and job management."""

import pytest

from goldreel.state.store import StateStore, compute_content_hash


def test_state_job_lifecycle(tmp_path):
    store = StateStore(base_dir=tmp_path / "state")
    job = store.create_job()

    assert job.job_id is not None
    assert (tmp_path / "state" / job.job_id / "manifest.json").exists()

    # Stage start
    job.mark_stage_start("facts")
    assert job.manifest.stages["facts"].status == "running"

    # Artifact save
    sample_data = {"metric": "IPL Centuries", "leader": "Virat Kohli", "value": 8}
    content_hash = compute_content_hash(sample_data)
    art_path = job.save_artifact("facts.json", sample_data)
    assert art_path.exists()
    assert "facts.json" in job.manifest.artifacts

    # Stage complete with hash
    job.mark_stage_completed("facts", content_hash=content_hash)
    assert job.is_stage_completed("facts", expected_hash=content_hash)
    assert not job.is_stage_completed("facts", expected_hash="mismatch_hash")

    # Reload from store
    reloaded = store.get_job(job.job_id)
    assert reloaded.is_stage_completed("facts")
    loaded_art = reloaded.load_artifact("facts.json")
    assert loaded_art["leader"] == "Virat Kohli"


def test_stage_failure_tracking(tmp_path):
    store = StateStore(base_dir=tmp_path / "state")
    job = store.create_job("test_fail_job")
    job.mark_stage_start("script")
    job.mark_stage_failed("script", error="Fact gate mismatch: number 99 not in fact table")

    assert job.manifest.stages["script"].status == "failed"
    assert "Fact gate mismatch" in job.manifest.stages["script"].error

    jobs = store.list_jobs()
    assert len(jobs) == 1
    assert jobs[0].job_id == "test_fail_job"


def test_duplicate_job_id_raises(tmp_path):
    store = StateStore(base_dir=tmp_path / "state")
    store.create_job("duplicate_id")
    with pytest.raises(FileExistsError):
        store.create_job("duplicate_id")
