"""Black and gold design tokens for GoldReel.

Single source of truth for colors, dimensions, safe areas, typography rules,
and dashboard CSS styling as defined in docs/DESIGN.md.
"""

from dataclasses import dataclass
from typing import NamedTuple


class RGB(NamedTuple):
    r: int
    g: int
    b: int


class RGBA(NamedTuple):
    r: int
    g: int
    b: int
    a: int


def hex_to_rgb(hex_code: str) -> RGB:
    """Convert hex color (#RRGGBB or RRGGBB) to RGB namedtuple."""
    hex_clean = hex_code.lstrip("#")
    if len(hex_clean) != 6:
        raise ValueError(f"Invalid hex code: {hex_code}")
    r = int(hex_clean[0:2], 16)
    g = int(hex_clean[2:4], 16)
    b = int(hex_clean[4:6], 16)
    return RGB(r, g, b)


def hex_to_rgba(hex_code: str, alpha: float) -> RGBA:
    """Convert hex color and float alpha (0.0 - 1.0) to RGBA namedtuple with alpha (0-255)."""
    rgb = hex_to_rgb(hex_code)
    a = int(round(max(0.0, min(1.0, alpha)) * 255))
    return RGBA(rgb.r, rgb.g, rgb.b, a)


@dataclass(frozen=True)
class ColorPalette:
    """Exact hex tokens from docs/DESIGN.md Section 1."""

    bg: str = "#0A0A0A"
    surface: str = "#161616"
    surface_2: str = "#1F1F1F"
    line: str = "#2A2A2A"
    gold: str = "#D4AF37"
    gold_light: str = "#F5E6A8"
    gold_dark: str = "#B8860B"
    ivory: str = "#F2EFE6"
    muted: str = "#A8A294"
    silver: str = "#C9C9C9"
    danger: str = "#E5484D"

    # RGB convenience properties
    @property
    def rgb_bg(self) -> RGB:
        return hex_to_rgb(self.bg)

    @property
    def rgb_surface(self) -> RGB:
        return hex_to_rgb(self.surface)

    @property
    def rgb_surface_2(self) -> RGB:
        return hex_to_rgb(self.surface_2)

    @property
    def rgb_line(self) -> RGB:
        return hex_to_rgb(self.line)

    @property
    def rgb_gold(self) -> RGB:
        return hex_to_rgb(self.gold)

    @property
    def rgb_gold_light(self) -> RGB:
        return hex_to_rgb(self.gold_light)

    @property
    def rgb_gold_dark(self) -> RGB:
        return hex_to_rgb(self.gold_dark)

    @property
    def rgb_ivory(self) -> RGB:
        return hex_to_rgb(self.ivory)

    @property
    def rgb_muted(self) -> RGB:
        return hex_to_rgb(self.muted)

    @property
    def rgb_silver(self) -> RGB:
        return hex_to_rgb(self.silver)

    @property
    def rgb_danger(self) -> RGB:
        return hex_to_rgb(self.danger)


Colors = ColorPalette()


@dataclass(frozen=True)
class LayoutConstants:
    """Resolution and safe margin constraints from docs/DESIGN.md."""

    # Landscape (16:9 Long videos)
    LANDSCAPE_WIDTH: int = 1920
    LANDSCAPE_HEIGHT: int = 1080
    LANDSCAPE_SAFE_MARGIN: int = 60

    # Portrait (9:16 Shorts)
    PORTRAIT_WIDTH: int = 1080
    PORTRAIT_HEIGHT: int = 1920
    PORTRAIT_SAFE_MARGIN_X: int = 60
    PORTRAIT_SAFE_MARGIN_TOP: int = 60
    PORTRAIT_SAFE_MARGIN_BOTTOM: int = 120  # Accommodate platform UI

    # Minimum font sizes at 1080p
    MIN_TITLE_SIZE_LANDSCAPE: int = 72
    MIN_TITLE_SIZE_PORTRAIT: int = 84
    MIN_LABEL_SIZE: int = 36
    MIN_AXIS_SIZE: int = 28

    # Motion constraints
    MAX_SIMULTANEOUS_MOVEMENTS: int = 3
    STAGGER_MIN_MS: int = 80
    STAGGER_MAX_MS: int = 120

    # Glow parameters
    GLOW_OPACITY_MIN: float = 0.20
    GLOW_OPACITY_MAX: float = 0.35
    GLOW_BLUR_RADIUS_MIN: int = 12
    GLOW_BLUR_RADIUS_MAX: int = 24


Layout = LayoutConstants()


@dataclass(frozen=True)
class DesignTokens:
    colors: ColorPalette = Colors
    layout: LayoutConstants = Layout

    @staticmethod
    def to_css_variables() -> str:
        """Generate CSS :root block matching docs/DESIGN.md."""
        return (
            ":root {\n"
            f"  --bg:{Colors.bg.lower()}; --surface:{Colors.surface.lower()}; "
            f"--surface-2:{Colors.surface_2.lower()}; --line:{Colors.line.lower()};\n"
            f"  --gold:{Colors.gold.lower()}; --gold-light:{Colors.gold_light.lower()}; "
            f"--gold-dark:{Colors.gold_dark.lower()};\n"
            f"  --ivory:{Colors.ivory.lower()}; --muted:{Colors.muted.lower()}; "
            f"--silver:{Colors.silver.lower()};\n"
            "  --glow:0 0 18px rgba(212,175,55,.35);\n"
            "}"
        )


Tokens = DesignTokens()
