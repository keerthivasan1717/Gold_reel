"""Benchmark script for Milestone 9 Dashboard & Learning Loop.

Measures:
- Dashboard compilation and static site generation (docs-site/index.html & style.css)
- Analytics record ingestion and metrics computation
- Template scoring and autonomous learning loop reallocation
- Weekly owner email generation (plain-text and HTML)
- Peak memory usage (strictly verified against system ceiling)
"""

import time
import tracemalloc
from pathlib import Path

from goldreel.analytics.client import YouTubeAnalyticsClient
from goldreel.analytics.email_reporter import WeeklyEmailReporter
from goldreel.analytics.models import VideoAnalyticsRecord
from goldreel.analytics.scorer import TemplateScorer
from goldreel.dashboard.generator import DashboardGenerator
from goldreel.dashboard.models import PipelineStageCard, SystemHealthStatus
from goldreel.state.store import StateStore


def run_benchmark():
    print("=== Milestone 9 Dashboard & Learning Loop Benchmark ===")

    tracemalloc.start()
    t0 = time.perf_counter()

    # 1. Benchmark Analytics Client & Record Aggregation
    t_start = time.perf_counter()
    bench_history = Path("data/bench_analytics.json")
    client = YouTubeAnalyticsClient(history_path=bench_history)

    # Ingest 50 mock records across templates
    templates = ["stat_race", "ranked_countdown", "scroll_compare", "milestone"]
    for i in range(50):
        t_type = templates[i % len(templates)]
        rec = VideoAnalyticsRecord(
            video_id=f"bench_vid_{i}",
            job_id=f"job_{i}",
            title=f"Benchmark Video {i}",
            lane="sports" if i % 2 == 0 else "comics",
            template_type=t_type,
            published_at="2026-11-18T00:00:00Z",
            views=1000 + i * 50,
            watch_time_minutes=500.0 + i * 20.0,
            average_percentage_viewed=45.0 + (i % 30),
            click_through_rate=4.0 + (i % 8) * 0.5,
            likes=50 + i * 2,
            subscribers_gained=2 + (i % 5),
            estimated_revenue_usd=0.20 + (i * 0.05),
        )
        client.record_metrics(rec)

    records = client.records
    t_client = (time.perf_counter() - t_start) * 1000

    # 2. Benchmark Template Scorer & Learning Loop
    t_start = time.perf_counter()
    scorer = TemplateScorer()
    rankings = scorer.score_templates(records)
    summary = scorer.generate_learning_summary(records)
    t_scorer = (time.perf_counter() - t_start) * 1000

    # 3. Benchmark Weekly Email Reporter
    t_start = time.perf_counter()
    reporter = WeeklyEmailReporter()
    txt_path, html_path = reporter.save_reports(summary, out_dir="out")
    email_text = txt_path.read_text(encoding="utf-8")
    email_html = html_path.read_text(encoding="utf-8")
    t_email = (time.perf_counter() - t_start) * 1000

    # 4. Benchmark Dashboard Generator
    t_start = time.perf_counter()
    dash_gen = DashboardGenerator(out_dir="docs-site")
    html_path, css_path = dash_gen.generate()
    t_dash = (time.perf_counter() - t_start) * 1000

    t_total = time.perf_counter() - t0
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Clean up benchmark temp files
    if bench_history.exists():
        bench_history.unlink()

    print(f"Ingested & computed {len(records)} records in: {t_client:.2f} ms")
    print(f"Scored {len(rankings)} templates & loop in:     {t_scorer:.2f} ms")
    print(f"Generated email (text {len(email_text)}b, html {len(email_html)}b) in: {t_email:.2f} ms")
    print(f"Generated static dashboard at {html_path.parent} in:  {t_dash:.2f} ms")
    print(f"Total benchmark wall time:                    {t_total:.4f} s")
    print(f"Current Memory:                               {current_mem / 1024 / 1024:.2f} MB")
    print(f"Peak Memory:                                  {peak_mem / 1024 / 1024:.2f} MB")
    print(f"Budget ceiling:                               3000.00 MB")
    assert peak_mem < 3000 * 1024 * 1024, "Peak memory breached 3 GB budget!"
    print("Benchmark completed successfully. Budget compliance verified.")


if __name__ == "__main__":
    run_benchmark()
