"""Unit tests for analytics, template scoring, and weekly owner reporting."""

from pathlib import Path

from goldreel.analytics.client import YouTubeAnalyticsClient
from goldreel.analytics.email_reporter import WeeklyEmailReporter
from goldreel.analytics.models import VideoAnalyticsRecord
from goldreel.analytics.scorer import TemplateScorer


def test_template_scorer_ranking_and_learning_loop():
    """Verify TemplateScorer computes weighted scores and identifies favored/retired templates."""
    records = [
        # Template A: High views, high retention (stat_race)
        VideoAnalyticsRecord(
            job_id="job_1",
            video_id="vid_1",
            title="IPL Most Centuries",
            format_type="landscape",
            template_type="stat_race",
            views=1200,
            watch_time_hours=25.0,
            retention_percent=75.0,
            ctr_percent=6.5,
            published_at="2026-11-10T14:00:00Z",
        ),
        VideoAnalyticsRecord(
            job_id="job_2",
            video_id="vid_2",
            title="Most International Sixes",
            format_type="landscape",
            template_type="stat_race",
            views=950,
            watch_time_hours=20.0,
            retention_percent=70.0,
            ctr_percent=6.0,
            published_at="2026-11-12T14:00:00Z",
        ),
        # Template B: Weak retention, low views (weak_template)
        VideoAnalyticsRecord(
            job_id="job_3",
            video_id="vid_3",
            title="Minor League Points",
            format_type="landscape",
            template_type="weak_template",
            views=150,
            watch_time_hours=2.0,
            retention_percent=25.0,
            ctr_percent=2.0,
            published_at="2026-11-13T14:00:00Z",
        ),
        VideoAnalyticsRecord(
            job_id="job_4",
            video_id="vid_4",
            title="Minor League Assists",
            format_type="landscape",
            template_type="weak_template",
            views=120,
            watch_time_hours=1.5,
            retention_percent=22.0,
            ctr_percent=1.8,
            published_at="2026-11-15T14:00:00Z",
        ),
    ]

    scorer = TemplateScorer()
    rankings = scorer.score_templates(records)

    assert len(rankings) == 2
    best = rankings[0]
    worst = rankings[1]

    # Best template is favored
    assert best.template_type == "stat_race"
    assert best.score >= 65.0
    assert best.status == "favored"

    # Worst template is retired
    assert worst.template_type == "weak_template"
    assert worst.score < 40.0
    assert worst.status == "retired"

    # Synthesis summary
    summary = scorer.generate_learning_summary(records, days=7)
    assert summary.best_template == "stat_race"
    assert "stat_race" in summary.favored_templates
    assert "weak_template" in summary.retired_templates
    assert len(summary.action_items) > 0


def test_analytics_client_save_and_load(tmp_path: Path):
    """Verify YouTubeAnalyticsClient persists metrics across invocations."""
    hist_file = tmp_path / "test_analytics.json"
    client = YouTubeAnalyticsClient(history_path=hist_file)

    rec = VideoAnalyticsRecord(
        job_id="job_test_01",
        video_id="vid_01",
        title="Debut Appearances",
        format_type="portrait",
        template_type="scroll_compare",
        views=450,
        published_at="2026-11-18T00:00:00Z",
    )
    client.record_metrics(rec)
    assert hist_file.exists()

    client_reloaded = YouTubeAnalyticsClient(history_path=hist_file)
    assert len(client_reloaded.records) == 1
    assert client_reloaded.records[0].video_id == "vid_01"
    assert client_reloaded.records[0].views == 450


def test_weekly_email_reporter_renders_text_and_html(tmp_path: Path):
    """Verify WeeklyEmailReporter renders compliant text and HTML reports."""
    records = [
        VideoAnalyticsRecord(
            job_id="job_x",
            video_id="vid_x",
            title="World Cup Hat-tricks",
            format_type="portrait",
            template_type="milestone",
            views=800,
            watch_time_hours=15.0,
            retention_percent=60.0,
            ctr_percent=5.0,
            published_at="2026-11-14T00:00:00Z",
        )
    ]
    scorer = TemplateScorer()
    summary = scorer.generate_learning_summary(records, days=7)

    reporter = WeeklyEmailReporter()
    txt_p, html_p = reporter.save_reports(summary, out_dir=tmp_path / "emails")

    assert txt_p.exists()
    assert html_p.exists()

    txt_content = txt_p.read_text(encoding="utf-8")
    assert "Subject: [GoldReel Weekly]" in txt_content
    assert "Target: $10.00/month" in txt_content
    assert "0 minutes required" in txt_content

    html_content = html_p.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_content
    assert "#D4AF37" in html_content
    assert "Template Performance Rankings" in html_content

