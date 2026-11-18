"""Landscape 1920x1080 layout coordinates and typography configuration."""

from dataclasses import dataclass
from pathlib import Path

from PIL import ImageFont

from goldreel.design.tokens import Layout


@dataclass(frozen=True)
class LandscapeLayout:
    width: int = Layout.LANDSCAPE_WIDTH
    height: int = Layout.LANDSCAPE_HEIGHT
    margin: int = Layout.LANDSCAPE_SAFE_MARGIN

    # Header bounds
    header_x: int = Layout.LANDSCAPE_SAFE_MARGIN
    header_y: int = Layout.LANDSCAPE_SAFE_MARGIN
    header_w: int = Layout.LANDSCAPE_WIDTH - 2 * Layout.LANDSCAPE_SAFE_MARGIN

    # Footer bounds
    footer_y: int = Layout.LANDSCAPE_HEIGHT - Layout.LANDSCAPE_SAFE_MARGIN - 40
    footer_x_source: int = Layout.LANDSCAPE_SAFE_MARGIN
    footer_x_brand: int = Layout.LANDSCAPE_WIDTH - Layout.LANDSCAPE_SAFE_MARGIN - 220

    # Content stage bounds
    stage_x: int = Layout.LANDSCAPE_SAFE_MARGIN
    stage_y: int = 190
    stage_w: int = Layout.LANDSCAPE_WIDTH - 2 * Layout.LANDSCAPE_SAFE_MARGIN
    stage_h: int = Layout.LANDSCAPE_HEIGHT - 190 - 90

    # Font paths
    FONT_DISPLAY: str = "assets/fonts/BebasNeue-Regular.ttf"
    FONT_SANS_BOLD: str = "assets/fonts/LiberationSans-Bold.ttf"
    FONT_SANS_REG: str = "assets/fonts/LiberationSans-Regular.ttf"
    FONT_SANS_NARROW: str = "assets/fonts/LiberationSansNarrow-Bold.ttf"

    def get_font(self, font_type: str, size: int) -> ImageFont.FreeTypeFont:
        """Load requested font with system/default fallback."""
        paths = {
            "display": self.FONT_DISPLAY,
            "bold": self.FONT_SANS_BOLD,
            "regular": self.FONT_SANS_REG,
            "narrow": self.FONT_SANS_NARROW,
        }
        path = paths.get(font_type, self.FONT_SANS_REG)
        p = Path(path)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
        return ImageFont.load_default()
