"""Tests for Milestone 10: Hardening, Drills, Simulation, and Security."""


from goldreel.drills.runner import FailureDrillRunner
from goldreel.drills.simulation import PipelineSimulationHarness
from goldreel.security.scanner import RepositorySecurityScanner


def test_failure_drills_pass():
    """Verify that all individual pipeline resilience drills pass."""
    runner = FailureDrillRunner()
    try:
        results = runner.run_all_drills()
        assert len(results) >= 5
        for r in results:
            assert r.passed, f"Drill '{r.name}' failed: {r.details}"
    finally:
        runner.cleanup()


def test_14_day_simulation_invariants():
    """Verify that the 14-day dry run simulation satisfies all pipeline invariants."""
    harness = PipelineSimulationHarness()
    try:
        summary = harness.run_14_day_simulation()
        assert summary.success
        assert summary.total_days == 14
        assert summary.total_jobs_succeeded >= 10
        assert summary.weekly_emails_generated == 2
        assert summary.dashboards_built == 2
        assert summary.overall_peak_ram_mb < 3000.0
    finally:
        harness.cleanup()


def test_security_scanner_clean_repo():
    """Verify that repo audit finds zero exposed secrets or tracked credentials."""
    scanner = RepositorySecurityScanner()
    report = scanner.run_full_audit()
    assert report.passed, (
        f"Security audit detected violations:\n"
        f"Tracked: {report.tracked_violations}\n"
        f"History: {report.history_violations}\n"
        f"Artifacts: {report.artifact_violations}\n"
        f"Untracked risks: {report.untracked_risks}"
    )
