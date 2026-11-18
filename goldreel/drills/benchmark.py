"""Benchmark script for Milestone 10: Hardening, Drills, and Simulation.

Measures:
- 14-day unattended simulation wall time and memory allocation
- Subsystem resilience drills execution time
- Full repository security audit scan time
- Peak memory usage across all hardening suites (verified against 3 GB ceiling)
"""

import time
import tracemalloc

from goldreel.drills.runner import FailureDrillRunner
from goldreel.drills.simulation import PipelineSimulationHarness
from goldreel.security.scanner import RepositorySecurityScanner


def run_benchmark():
    print("=== Milestone 10 Hardening & Resilience Benchmark ===")

    tracemalloc.start()
    t0 = time.perf_counter()

    # 1. Benchmark Repository Security Scan
    t_start = time.perf_counter()
    scanner = RepositorySecurityScanner()
    report = scanner.run_full_audit()
    t_audit = (time.perf_counter() - t_start) * 1000
    assert report.passed, "Security audit failed during benchmark!"

    # 2. Benchmark Resilience Failure Drills
    t_start = time.perf_counter()
    runner = FailureDrillRunner()
    try:
        drill_results = runner.run_all_drills()
        for r in drill_results:
            assert r.passed, f"Drill {r.name} failed!"
    finally:
        runner.cleanup()
    t_drills = (time.perf_counter() - t_start) * 1000

    # 3. Benchmark 14-Day Simulation
    t_start = time.perf_counter()
    harness = PipelineSimulationHarness()
    try:
        sim_summary = harness.run_14_day_simulation()
        assert sim_summary.success, "14-day simulation failed!"
    finally:
        harness.cleanup()
    t_sim = (time.perf_counter() - t_start) * 1000

    t_total = time.perf_counter() - t0
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Repository Security Audit completed in:     {t_audit:.2f} ms")
    print(f"5 Resilience Failure Drills completed in:   {t_drills:.2f} ms")
    print(f"14-Day Dry Run Simulation completed in:     {t_sim:.2f} ms")
    print(f"Total Hardening Benchmark Wall Time:        {t_total:.4f} s")
    print(f"Current Memory:                             {current_mem / 1024 / 1024:.2f} MB")
    print(f"Peak Memory:                                {peak_mem / 1024 / 1024:.2f} MB")
    print(f"Budget Ceiling:                             3000.00 MB")
    assert peak_mem < 3000 * 1024 * 1024, "Peak memory breached 3 GB budget ceiling!"
    print("Benchmark completed successfully. Budget compliance verified.")


if __name__ == "__main__":
    run_benchmark()
