"""Benchmark script for Milestone 7 Quality Control (QC) Gates.

Measures:
- Extraction of 6 sample frames and visual analysis time
- Audio loudness and true peak analysis time via FFmpeg loudnorm
- Metadata linting and similarity deduplication check time
- Peak RAM usage (strictly bounded to system constraints)
"""

import time
import tracemalloc

from goldreel.qc.gate import QualityGate
from goldreel.state.store import StateStore


def run_benchmark():
    store = StateStore()
    jobs = store.list_jobs()
    if not jobs:
        print("No existing jobs found to benchmark.")
        return

    # Find candidate jobs with video.mp4
    test_job_id = None
    for j in jobs:
        v_path = store.base_dir / j.job_id / "video.mp4"
        if v_path.exists():
            test_job_id = j.job_id
            break

    if not test_job_id:
        print("No job with video.mp4 found.")
        return

    job = store.get_job(test_job_id)
    print(f"=== Quality Control (QC) Benchmark for Job {job.job_id} ===")

    tracemalloc.start()
    t0 = time.perf_counter()

    gate = QualityGate()
    report = gate.evaluate_job(job, dry_run=True)

    t1 = time.perf_counter()
    current_ram, peak_ram = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    elapsed = t1 - t0
    peak_ram_mb = peak_ram / (1024 * 1024)

    print(f"Total QC Duration:       {elapsed:.2f} s")
    print(f"Peak RAM Usage:          {peak_ram_mb:.2f} MB")
    print(f"Gates Evaluated:         {len(report.checks)}")
    print(f"Overall Result:          {'PASSED' if report.passed else 'FAILED'}")
    print(f"Frames Audited:          {len(report.frames_audited)}")
    if report.loudness_lufs is not None:
        print(f"Measured Loudness:       {report.loudness_lufs:.1f} LUFS")
    if report.true_peak_dbfs is not None:
        print(f"Measured True Peak:      {report.true_peak_dbfs:.1f} dBFS")
    if report.similarity_score is not None:
        print(f"Similarity Score:        {report.similarity_score:.1f}%")

    # Assert budget limits
    assert peak_ram_mb < 3000, "Peak RAM exceeded 3 GB limit"
    print("✓ All benchmark constraints satisfied.")


if __name__ == "__main__":
    run_benchmark()
