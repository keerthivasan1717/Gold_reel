"""Data models for YouTube analytics, template performance scoring, and learning loops."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

TemplateStatus = Literal["favored", "neutral", "retired"]


class VideoAnalyticsRecord(BaseModel):
    """Analytics metrics recorded for a single published video."""

    job_id: str
    video_id: str
    title: str
    format_type: str = "landscape"
    template_type: str = "stat_race"
    lane: str = "sports"
    views: int = 0
    watch_time_hours: float = 0.0
    avg_view_duration_sec: float = 0.0
    retention_percent: float = 0.0
    ctr_percent: float = 0.0
    estimated_revenue_usd: float = 0.0
    published_at: str
    last_updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class TemplatePerformance(BaseModel):
    """Aggregate performance metrics and scoring for a template type."""

    template_type: str
    video_count: int = 0
    total_views: int = 0
    avg_views: float = 0.0
    avg_watch_time_hours: float = 0.0
    avg_retention_percent: float = 0.0
    avg_ctr_percent: float = 0.0
    score: float = Field(default=50.0, description="Normalized score 0.0 - 100.0")
    status: TemplateStatus = "neutral"
    recommendation: str = ""


class LearningSummary(BaseModel):
    """Weekly learning loop synthesis report."""

    period_start: str
    period_end: str
    total_videos_analyzed: int
    total_channel_views: int
    total_watch_time_hours: float
    estimated_monthly_revenue_usd: float
    template_rankings: list[TemplatePerformance] = Field(default_factory=list)
    best_template: str | None = None
    retired_templates: list[str] = Field(default_factory=list)
    favored_templates: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

