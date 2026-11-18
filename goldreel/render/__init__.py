"""Render package."""

from .background import ProceduralBackground
from .easing import ease_in_out_quad, ease_out_quad, linear
from .engine import RenderEngine, RenderStats
from .layouts.landscape import LandscapeLayout
from .templates.base import BaseTemplate
from .templates.ranked_countdown import RankedCountdownTemplate
from .templates.stat_race import StatRaceTemplate
from .timeline import Timeline

__all__ = [
    "BaseTemplate",
    "LandscapeLayout",
    "ProceduralBackground",
    "RankedCountdownTemplate",
    "RenderEngine",
    "RenderStats",
    "StatRaceTemplate",
    "Timeline",
    "ease_in_out_quad",
    "ease_out_quad",
    "linear",
]
