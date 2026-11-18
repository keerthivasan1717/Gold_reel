"""Static dashboard generator package for GoldReel."""

from goldreel.dashboard.generator import DashboardGenerator
from goldreel.dashboard.models import DashboardViewModel, PipelineStageCard, SystemHealthStatus

__all__ = ["DashboardGenerator", "DashboardViewModel", "PipelineStageCard", "SystemHealthStatus"]
