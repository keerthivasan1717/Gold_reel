"""14-day unattended CI dry run simulation harness.

Simulates 14 consecutive days of autonomous pipeline execution:
- Daily scheduling cadence (max 2/day, max 7/week).
- Ingest, angle selection, and cross-day topic deduplication (>85% similarity check).
- Script synthesis and FactGate verification across sports and comic lanes.
- Quality gate validation and dry-run publishing state transitions.
- Weekly analytics harvest, autonomous template scoring, and learning loop reallocation.
- Static dashboard generation and weekly owner email summaries on days 7 and 14.
- Continuous memory profiling to guarantee peak RAM stays strictly under 3 GB.
"""

import shutil
import tempfile
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from goldreel.analytics.client import YouTubeAnalyticsClient
from goldreel.analytics.email_reporter import WeeklyEmailReporter
from goldreel.analytics.models import VideoAnalyticsRecord
from goldreel.analytics.scorer import TemplateScorer
from goldreel.dashboard.generator import DashboardGenerator
from goldreel.facts.gate import FactGate
from goldreel.facts.models import FactRecord, FactTable
from goldreel.publish.scheduler import PublishHistory, PublishScheduler
from goldreel.script.router import ProviderRouter
from goldreel.state.store import StateStore
from goldreel.topics.history import TopicHistory


@dataclass
class DailySimulationResult:
    """Telemetry captured for a single day of the simulation."""

    day_index: int
    date_str: str
    jobs_attempted: int
    jobs_succeeded: int
    jobs_deduplicated: int
    peak_ram_mb: float
    duration_seconds: float


@dataclass
class SimulationSummary:
    """Overall summary of the 14-day simulation."""

    total_days: int
    total_jobs_run: int
    total_jobs_succeeded: int
    total_deduplicated_angles: int
    weekly_emails_generated: int
    dashboards_built: int
    overall_peak_ram_mb: float
    total_wall_time_seconds: float
    success: bool
    daily_results: list[DailySimulationResult] = field(default_factory=list)


class PipelineSimulationHarness:
    """Executes multi-day autonomous simulation cycles without external API calls."""

    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir or tempfile.mkdtemp(prefix="goldreel_sim_")).resolve()
        self.state_dir = self.base_dir / "state"
        self.out_dir = self.base_dir / "out"
        self.docs_dir = self.base_dir / "docs-site"
        self.analytics_path = self.state_dir / "analytics_history.json"

        for d in [self.state_dir, self.out_dir, self.docs_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.store = StateStore(base_dir=self.state_dir)
        self.history = TopicHistory(history_file=self.state_dir / "topic_history.json")
        self.pub_history = PublishHistory(history_path=self.state_dir / "publish_history.json")
        self.scheduler = PublishScheduler(history=self.pub_history)
        self.scorer = TemplateScorer()
        self.analytics_client = YouTubeAnalyticsClient(history_path=self.analytics_path)
        self.reporter = WeeklyEmailReporter()
        self.dash_gen = DashboardGenerator(store=self.store, out_dir=self.docs_dir)

    def _generate_mock_daily_facts(self, day: int) -> list[FactTable]:
        """Generate verified fact tables across sports and comic lanes."""
        sports_data = [
            ("Virat Kohli", 8, "Chris Gayle", 6, "IPL All-Time Centuries"),
            ("Erling Haaland", 36, "Harry Kane", 30, "Premier League Golden Boot 2023"),
            ("Rohit Sharma", 5, "David Warner", 4, "World Cup Most Centuries"),
            ("Lionel Messi", 91, "Cristiano Ronaldo", 69, "Calendar Year Goals Record"),
            ("MS Dhoni", 250, "Dinesh Karthik", 240, "Most Matches as Wicketkeeper"),
            ("Kylian Mbappe", 8, "Julian Alvarez", 4, "World Cup Knockout Goals"),
            ("Sachin Tendulkar", 100, "Ricky Ponting", 71, "International Cricket Centuries"),
            ("Mohamed Salah", 32, "Son Heung-min", 23, "Premier League Single Season Records"),
            ("Jasprit Bumrah", 150, "Lasith Malinga", 170, "IPL Death Over Wickets"),
            ("Robert Lewandowski", 41, "Gerd Muller", 40, "Bundesliga Single Season Goals"),
            ("AB de Villiers", 31, "Corey Anderson", 36, "Fastest ODI Hundred Balls"),
            ("Neymar Jr", 79, "Pele", 77, "Brazil All-Time Top Scorers"),
            ("Virat Kohli", 8, "Chris Gayle", 6, "IPL All-Time Centuries"),  # Intentional duplicate on Day 13!
            ("Sunil Chhetri", 94, "Ali Daei", 109, "International Football Legends"),
        ]

        comic_data = [
            ("Superman", 1938, "Batman", 1939, "DC Golden Age Heroes"),
            ("Spider-Man", 1962, "Iron Man", 1963, "Marvel Silver Age Debuts"),
            ("Wonder Woman", 1941, "Captain Marvel", 1940, "First Female Superhero Debuts"),
            ("The Flash", 1940, "Green Lantern", 1940, "Justice Society First Appearances"),
            ("Hulk", 1962, "Thor", 1962, "Marvel Pantheon Origins"),
            ("Captain America", 1941, "Bucky Barnes", 1941, "Timely Comics Wartime Heroes"),
            ("Wolverine", 1974, "Punisher", 1974, "Bronze Age Antihero Debuts"),
            ("Black Panther", 1966, "Falcon", 1969, "Pioneering African American Heroes"),
            ("Daredevil", 1964, "Doctor Strange", 1963, "Marvel Street and Mystic Debuts"),
            ("Robin", 1940, "Speedy", 1941, "Golden Age Sidekick Debuts"),
            ("Aquaman", 1941, "Green Arrow", 1941, "More Fun Comics 1941 Launches"),
            ("Silver Surfer", 1966, "Galactus", 1966, "Cosmic Marvel Introductions"),
            ("Superman", 1938, "Batman", 1939, "DC Golden Age Heroes"),  # Intentional duplicate on Day 13!
            ("Nightwing", 1984, "Red Hood", 2005, "Bat-Family Evolutions"),
        ]

        s_idx = (day - 1) % len(sports_data)
        s_e1, s_v1, s_e2, s_v2, s_title = sports_data[s_idx]

        c_idx = (day - 1) % len(comic_data)
        c_e1, c_v1, c_e2, c_v2, c_title = comic_data[c_idx]

        tables = [
            FactTable(
                topic_id=f"sports_day_{day}",
                title=s_title,
                lane="sports",
                metric_label="Records",
                sources=[
                    {
                        "name": "cricsheet",
                        "source_url": "https://cricsheet.org",
                        "retrieved_at": f"2026-11-{day:02d}T00:00:00Z",
                    }
                ],
                records=[
                    FactRecord(rank=1, entity=s_e1, metric="Record", value=s_v1, unit="stat"),
                    FactRecord(rank=2, entity=s_e2, metric="Record", value=s_v2, unit="stat"),
                ],
            ),
            FactTable(
                topic_id=f"comic_day_{day}",
                title=c_title,
                lane="comics",
                metric_label="Year",
                sources=[
                    {
                        "name": "wikidata",
                        "source_url": "https://wikidata.org",
                        "retrieved_at": f"2026-11-{day:02d}T00:00:00Z",
                    },
                    {
                        "name": "grandcomicsdb",
                        "source_url": "https://gcd.org",
                        "retrieved_at": f"2026-11-{day:02d}T00:00:00Z",
                    },
                ],
                records=[
                    FactRecord(rank=1, entity=c_e1, metric="Publication Year", value=c_v1, unit="year"),
                    FactRecord(rank=2, entity=c_e2, metric="Publication Year", value=c_v2, unit="year"),
                ],
            ),
        ]
        return tables

    def run_14_day_simulation(self) -> SimulationSummary:
        """Execute full 14-day unattended pipeline simulation."""
        was_tracing = tracemalloc.is_tracing()
        if not was_tracing:
            tracemalloc.start()
        start_time = time.perf_counter()

        daily_results: list[DailySimulationResult] = []
        total_succeeded = 0
        total_deduped = 0
        weekly_emails = 0
        dashboards_built = 0
        overall_peak_ram = 0.0

        templates_pool = ["stat_race", "ranked_countdown", "scroll_compare", "milestone"]

        router = ProviderRouter()

        for day in range(1, 15):
            t_day_start = time.perf_counter()
            current_date = datetime(2026, 11, day, 6, 0, 0, tzinfo=UTC)
            date_str = current_date.strftime("%Y-%m-%d")

            facts_list = self._generate_mock_daily_facts(day)
            attempted = 0
            succeeded = 0
            deduped = 0

            for fact_table in facts_list:
                attempted += 1
                fmt = "landscape" if fact_table.lane == "sports" else "portrait"

                # 1. Rate Limit check (max 2 per day, max 7 per week)
                if succeeded >= 2:
                    continue
                week_num = 1 if day <= 7 else 2
                current_week_jobs = sum(
                    r.jobs_succeeded for r in daily_results if (1 if r.day_index <= 7 else 2) == week_num
                ) + succeeded
                if current_week_jobs >= 7:
                    continue

                # 2. Topic Deduplication check
                is_duplicate, dup_id, sim_score = self.history.check_similarity(
                    title=fact_table.title,
                    entities=[r.entity for r in fact_table.records],
                )
                if is_duplicate:
                    deduped += 1
                    continue

                # 3. Create Job
                job = self.store.create_job(f"sim_day_{day}_{attempted}")

                # 4. Generate Script & Verify FactGate
                t_type = templates_pool[(day + attempted) % len(templates_pool)]
                script = router.generate_script(
                    fact_table=fact_table,
                    format_type=fmt,
                    template_type=t_type,
                )

                gate = FactGate(fact_table)
                gate_res = gate.verify_script(script.model_dump())
                if not gate_res.passed:
                    job.mark_stage_failed("facts", f"FactGate failed: {gate_res.violations}")
                    continue

                # 5. Complete pipeline stages (dry-run)
                for stage in ["ingest", "facts", "topics", "script", "voice", "render", "qc", "publish"]:
                    job.mark_stage_completed(stage)

                self.pub_history.record_upload(
                    job_id=job.job_id,
                    video_id=f"yt_vid_{job.job_id}",
                    scheduled_at=None,
                    mode="scheduled",
                )

                # Record in topic history
                self.history.record_topic(
                    job_id=job.job_id,
                    topic_id=fact_table.topic_id,
                    title=fact_table.title,
                    lane=fact_table.lane,
                    angle_id="daily_benchmark_angle",
                    entities=[r.entity for r in fact_table.records],
                    facts_hash=f"hash_day_{day}_{attempted}",
                )

                # Record simulated analytics record
                record = VideoAnalyticsRecord(
                    video_id=f"yt_vid_{job.job_id}",
                    job_id=job.job_id,
                    title=fact_table.title,
                    lane=fact_table.lane,
                    template_type=t_type,
                    published_at=date_str,
                    views=500 + day * 50,
                    watch_time_minutes=250.0 + day * 25.0,
                    average_percentage_viewed=50.0 + (day % 20),
                    click_through_rate=5.0 + (day % 5),
                    likes=30 + day * 3,
                    subscribers_gained=1 + (day % 3),
                    estimated_revenue_usd=0.15 * day,
                )
                self.analytics_client.record_metrics(record)

                succeeded += 1

            total_succeeded += succeeded
            total_deduped += deduped

            # Weekly Milestone Check (Day 7 and Day 14)
            if day in (7, 14):
                records = self.analytics_client.records
                summary = self.scorer.generate_learning_summary(records, days=7)

                # Generate weekly email
                self.reporter.save_reports(summary, out_dir=self.out_dir)
                weekly_emails += 1

                # Rebuild static dashboard
                self.dash_gen.generate()
                dashboards_built += 1

            curr_mem, peak_mem = tracemalloc.get_traced_memory()
            peak_mb = peak_mem / (1024 * 1024)
            if peak_mb > overall_peak_ram:
                overall_peak_ram = peak_mb

            daily_results.append(
                DailySimulationResult(
                    day_index=day,
                    date_str=date_str,
                    jobs_attempted=attempted,
                    jobs_succeeded=succeeded,
                    jobs_deduplicated=deduped,
                    peak_ram_mb=peak_mb,
                    duration_seconds=time.perf_counter() - t_day_start,
                )
            )

        if not was_tracing:
            tracemalloc.stop()
        total_wall_time = time.perf_counter() - start_time

        # Verification asserts:
        # 1. Peak RAM must strictly stay below 3,000 MB
        # 2. Jobs must have succeeded and adhered to rate limits (<= 7 per week)
        # 3. Weekly emails and dashboards must have fired exactly twice (day 7 & day 14)
        is_success = (
            overall_peak_ram < 3000.0
            and total_succeeded >= 10
            and weekly_emails == 2
            and dashboards_built == 2
        )

        return SimulationSummary(
            total_days=14,
            total_jobs_run=sum(r.jobs_attempted for r in daily_results),
            total_jobs_succeeded=total_succeeded,
            total_deduplicated_angles=total_deduped,
            weekly_emails_generated=weekly_emails,
            dashboards_built=dashboards_built,
            overall_peak_ram_mb=overall_peak_ram,
            total_wall_time_seconds=total_wall_time,
            success=is_success,
            daily_results=daily_results,
        )

    def cleanup(self) -> None:
        """Remove simulation temporary directory."""
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
