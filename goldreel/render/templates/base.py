"""Base class for all render templates."""

from abc import ABC, abstractmethod

from PIL import Image, ImageDraw

from goldreel.design.tokens import Colors
from goldreel.facts.models import FactTable
from goldreel.render.background import ProceduralBackground
from goldreel.render.layouts.landscape import LandscapeLayout
from goldreel.render.timeline import Timeline
from goldreel.script.models import GeneratedScript


class BaseTemplate(ABC):
    """Abstract template renderer."""

    def __init__(self, layout: LandscapeLayout | None = None, seed: int = 42):
        self.layout = layout or LandscapeLayout()
        self.bg = ProceduralBackground(
            width=self.layout.width,
            height=self.layout.height,
            seed=seed,
        )

    @abstractmethod
    def plan(self, fact_table: FactTable, script: GeneratedScript) -> Timeline:
        """Plan timeline, keyframes, and durations from facts and script."""
        pass

    @abstractmethod
    def draw(self, t: float) -> Image.Image:
        """Draw video frame at timestamp t."""
        pass

    def draw_common_chrome(
        self,
        img: Image.Image,
        title: str,
        metric_label: str,
        source_text: str,
        watermark: str = "GOLDREEL",
    ) -> None:
        """Draw persistent header, footer source, and brand watermark within safe margins."""
        draw = ImageDraw.Draw(img)

        # Header fonts
        font_title = self.layout.get_font("display", 72)
        font_sub = self.layout.get_font("regular", 28)

        # Title
        draw.text(
            (self.layout.header_x, self.layout.header_y),
            title.upper(),
            fill=Colors.rgb_ivory,
            font=font_title,
        )
        # Metric / Rule label
        draw.text(
            (self.layout.header_x, self.layout.header_y + 80),
            metric_label,
            fill=Colors.rgb_muted,
            font=font_sub,
        )

        # Hairline separator under header
        draw.line(
            [
                self.layout.header_x,
                self.layout.header_y + 120,
                self.layout.header_x + self.layout.header_w,
                self.layout.header_y + 120,
            ],
            fill=Colors.rgb_line,
            width=1,
        )

        # Footer Source
        font_footer = self.layout.get_font("regular", 24)
        draw.text(
            (self.layout.footer_x_source, self.layout.footer_y),
            f"Source: {source_text}",
            fill=Colors.rgb_muted,
            font=font_footer,
        )

        # Brand Watermark
        draw.text(
            (self.layout.footer_x_brand, self.layout.footer_y),
            watermark,
            fill=Colors.rgb_gold,
            font=font_footer,
        )
