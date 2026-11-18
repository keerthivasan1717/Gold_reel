"""Tests for GoldReel CLI commands."""

from typer.testing import CliRunner

from goldreel.cli import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Headless black-and-gold open data video publisher" in result.stdout


def test_cli_ingest():
    result = runner.invoke(app, ["ingest", "--lane", "sports", "--dry-run"])
    assert result.exit_code == 0
    assert "[Ingest]" in result.stdout


def test_cli_plan():
    result = runner.invoke(app, ["plan", "--lane", "sports", "--format", "landscape"])
    assert result.exit_code == 0
    assert "[Plan] Topic planning complete" in result.stdout


def test_cli_make_dry_run():
    result = runner.invoke(app, ["make", "--dry-run", "--lane", "sports"])
    assert result.exit_code == 0
    assert "[Make] Starting production" in result.stdout
    assert "Pipeline completed" in result.stdout


def test_cli_qc_and_publish():
    import uuid

    test_jid = f"job_cli_{uuid.uuid4().hex[:8]}"
    # First create a full job via make in dry-run
    make_res = runner.invoke(app, ["make", "--job-id", test_jid, "--lane", "sports", "--dry-run"])
    assert make_res.exit_code == 0

    # Run QC
    qc_res = runner.invoke(app, ["qc", "--job-id", test_jid, "--dry-run"])
    assert qc_res.exit_code == 0
    assert "PASSED" in qc_res.stdout

    # Run Publish in dry-run
    pub_res = runner.invoke(app, ["publish", "--job-id", test_jid, "--dry-run"])
    assert pub_res.exit_code == 0
    assert "[Publish]" in pub_res.stdout


def test_cli_report():
    result = runner.invoke(app, ["report"])
    assert result.exit_code == 0
    assert "GoldReel Pipeline Status" in result.stdout
