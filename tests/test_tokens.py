"""Tests for GoldReel black and gold design tokens."""

import pytest

from goldreel.design.tokens import (
    Colors,
    Layout,
    Tokens,
    hex_to_rgb,
    hex_to_rgba,
)


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    """Calculate relative luminance for WCAG contrast ratio."""
    normalized = []
    for c in rgb:
        v = c / 255.0
        normalized.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * normalized[0] + 0.7152 * normalized[1] + 0.0722 * normalized[2]


def contrast_ratio(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
    """Calculate WCAG contrast ratio between two RGB colors."""
    l1 = relative_luminance(rgb1)
    l2 = relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_token_hex_values():
    """Verify all tokens match docs/DESIGN.md Section 1 exactly."""
    assert Colors.bg == "#0A0A0A"
    assert Colors.surface == "#161616"
    assert Colors.surface_2 == "#1F1F1F"
    assert Colors.line == "#2A2A2A"
    assert Colors.gold == "#D4AF37"
    assert Colors.gold_light == "#F5E6A8"
    assert Colors.gold_dark == "#B8860B"
    assert Colors.ivory == "#F2EFE6"
    assert Colors.muted == "#A8A294"
    assert Colors.silver == "#C9C9C9"
    assert Colors.danger == "#E5484D"


def test_hex_to_rgb_and_rgba():
    """Verify conversion to RGB and RGBA."""
    rgb = hex_to_rgb("#D4AF37")
    assert rgb == (212, 175, 55)

    rgba = hex_to_rgba("#D4AF37", 0.35)
    assert rgba.r == 212
    assert rgba.g == 175
    assert rgba.b == 55
    assert rgba.a == round(0.35 * 255)

    with pytest.raises(ValueError):
        hex_to_rgb("INVALID")


def test_text_contrast_ratio():
    """Verify main ivory text on base background and card surfaces has contrast > 4.5:1."""
    bg_rgb = Colors.rgb_bg
    surface_rgb = Colors.rgb_surface
    ivory_rgb = Colors.rgb_ivory

    ratio_on_bg = contrast_ratio(ivory_rgb, bg_rgb)
    ratio_on_surface = contrast_ratio(ivory_rgb, surface_rgb)

    assert ratio_on_bg >= 4.5, f"Contrast on bg is {ratio_on_bg:.2f}"
    assert ratio_on_surface >= 4.5, f"Contrast on surface is {ratio_on_surface:.2f}"


def test_layout_constants():
    """Verify dimensions and safe margins."""
    assert Layout.LANDSCAPE_WIDTH == 1920
    assert Layout.LANDSCAPE_HEIGHT == 1080
    assert Layout.LANDSCAPE_SAFE_MARGIN == 60

    assert Layout.PORTRAIT_WIDTH == 1080
    assert Layout.PORTRAIT_HEIGHT == 1920
    assert Layout.PORTRAIT_SAFE_MARGIN_BOTTOM == 120

    assert Layout.MIN_TITLE_SIZE_LANDSCAPE == 72
    assert Layout.MIN_TITLE_SIZE_PORTRAIT == 84
    assert Layout.MIN_LABEL_SIZE == 36
    assert Layout.MIN_AXIS_SIZE == 28


def test_css_variables_output():
    """Verify CSS generator produces root block matching DESIGN.md."""
    css = Tokens.to_css_variables()
    assert ":root {" in css
    assert "--bg:#0a0a0a;" in css
    assert "--gold:#d4af37;" in css
    assert "--glow:0 0 18px rgba(212,175,55,.35);" in css
