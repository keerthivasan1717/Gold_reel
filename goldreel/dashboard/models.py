"""View models for rendering the static HTML dashboard."""

from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, Field

from goldreel.analytics.models import TemplatePerformance, VideoAnalyticsRecord


class PipelineStageCard(BaseModel):
    """Status card for a single pipeline stage in the latest job."""

    name: str
    status: str = "completed"  # completed, failed, running, pending, skipped
    duration_sec: float | None = None
    summary: str = ""
    error: str | None = None


class SystemHealthStatus(BaseModel):
    """Health indicator metrics for data freshness, tokens, and compute."""

    cricsheet_freshness: str = "Live (synced)"
    football_freshness: str = "Live (synced)"
    wikidata_freshness: str = "Live (synced)"
    oauth_token_status: str = "Verified / Active"
    disk_usage_percent: float = 18.5
    runner_minutes_used: int = 142
    runner_monthly_limit: int = 2000
    publish_mode: str = "scheduled"
    kill_switch_active: bool = False


class DashboardViewModel(BaseModel):
    """Complete data structure supplied to Jinja2 template."""

    # Status strip
    channel_name: str = "GoldReel"
    last_successful_run: str
    next_scheduled_upload: str
    publish_mode_display: str
    publish_mode_tag: str  # scheduled, restricted, off

    # Pipeline board
    latest_job_id: str
    pipeline_stages: list[PipelineStageCard] = Field(default_factory=list)

    # Queue and history
    videos_history: list[dict[str, Any]] = Field(default_factory=list)

    # Template performance scores
    template_scores: list[TemplatePerformance] = Field(default_factory=list)

    # Health
    health: SystemHealthStatus = Field(default_factory=SystemHealthStatus)

    # Overview counters
    total_videos: int = 0
    total_views: int = 0
    total_watch_time: float = 0.0
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"))
