"""Analytics, template scoring, and learning loop package for GoldReel."""

from goldreel.analytics.client import YouTubeAnalyticsClient
from goldreel.analytics.email_reporter import WeeklyEmailReporter
from goldreel.analytics.models import LearningSummary, TemplatePerformance, VideoAnalyticsRecord
from goldreel.analytics.scorer import TemplateScorer

__all__ = [
    "YouTubeAnalyticsClient",
    "TemplateScorer",
    "WeeklyEmailReporter",
    "VideoAnalyticsRecord",
    "TemplatePerformance",
    "LearningSummary",
]
