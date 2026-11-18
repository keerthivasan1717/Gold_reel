"""Test visual audit frame generation."""

from pathlib import Path

from goldreel.design.audit_frames import run_all


def test_visual_audit_frames_generate(tmp_path):
    run_all()
    out_dir = Path("tests/fixtures/visual_check_frames")
    for i in range(1, 7):
        matches = list(out_dir.glob(f"frame_{i}_*.png"))
        assert len(matches) == 1, f"Frame {i} not generated"
        assert matches[0].stat().st_size > 1000, f"Frame {i} is empty"
