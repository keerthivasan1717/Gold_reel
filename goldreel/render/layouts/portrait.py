"""Portrait 1080x1920 layout configuration for YouTube Shorts.

Strictly follows docs/DESIGN.md Section 3:
- Resolution: 1080x1920 (9:16 vertical).
- Safe margins: 60 px on left/right/top, 120 px on bottom for platform UI.
- Minimum font sizes: titles 84 px, labels 36 px, axis 28 px.
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import ImageFont

from goldreel.design.tokens import Layout


@dataclass(frozen=True)
class PortraitLayout:
    width: int = Layout.PORTRAIT_WIDTH
    height: int = Layout.PORTRAIT_HEIGHT
    margin_x: int = Layout.PORTRAIT_SAFE_MARGIN_X
    margin_top: int = Layout.PORTRAIT_SAFE_MARGIN_TOP
    margin_bottom: int = Layout.PORTRAIT_SAFE_MARGIN_BOTTOM

    # Usable horizontal width inside safe margin
    usable_w: int = Layout.PORTRAIT_WIDTH - (2 * Layout.PORTRAIT_SAFE_MARGIN_X)

    # Header region
    header_x: int = Layout.PORTRAIT_SAFE_MARGIN_X
    header_y: int = Layout.PORTRAIT_SAFE_MARGIN_TOP + 20
    header_w: int = Layout.PORTRAIT_WIDTH - (2 * Layout.PORTRAIT_SAFE_MARGIN_X)

    # Content stage bounds
    stage_x: int = Layout.PORTRAIT_SAFE_MARGIN_X
    stage_y: int = 240
    stage_w: int = Layout.PORTRAIT_WIDTH - (2 * Layout.PORTRAIT_SAFE_MARGIN_X)
    stage_h: int = Layout.PORTRAIT_HEIGHT - 240 - Layout.PORTRAIT_SAFE_MARGIN_BOTTOM - 40

    # Footer bounds (just above the 120px platform UI exclusion zone)
    footer_y: int = Layout.PORTRAIT_HEIGHT - Layout.PORTRAIT_SAFE_MARGIN_BOTTOM - 45
    footer_x_source: int = Layout.PORTRAIT_SAFE_MARGIN_X
    footer_x_brand: int = Layout.PORTRAIT_WIDTH - Layout.PORTRAIT_SAFE_MARGIN_X - 180
    margin: int = Layout.PORTRAIT_SAFE_MARGIN_X

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
