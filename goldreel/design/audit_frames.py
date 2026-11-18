"""Render 6 visual verification frames using Pillow and design tokens to audit against docs/DESIGN.md."""

import random
import time
import tracemalloc
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from goldreel.design.tokens import Colors, Layout

OUT_DIR = Path("tests/fixtures/visual_check_frames")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BEBAS_FONT = "assets/fonts/BebasNeue-Regular.ttf"
SANS_BOLD = "assets/fonts/LiberationSans-Bold.ttf"
SANS_REG = "assets/fonts/LiberationSans-Regular.ttf"
SANS_NARROW = "assets/fonts/LiberationSansNarrow-Bold.ttf"


def get_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def render_frame_1_palette():
    """Frame 1: Palette Swatch Card (1920x1080)."""
    img = Image.new("RGB", (Layout.LANDSCAPE_WIDTH, Layout.LANDSCAPE_HEIGHT), Colors.rgb_bg)
    draw = ImageDraw.Draw(img)

    title_font = get_font(BEBAS_FONT, Layout.MIN_TITLE_SIZE_LANDSCAPE)
    label_font = get_font(SANS_REG, Layout.MIN_LABEL_SIZE)
    sub_font = get_font(SANS_REG, Layout.MIN_AXIS_SIZE)

    # Title
    draw.text(
        (Layout.LANDSCAPE_SAFE_MARGIN, Layout.LANDSCAPE_SAFE_MARGIN),
        "GOLDREEL COLOR PALETTE SPECIFICATION",
        fill=Colors.rgb_gold,
        font=title_font,
    )
    draw.text(
        (Layout.LANDSCAPE_SAFE_MARGIN, Layout.LANDSCAPE_SAFE_MARGIN + 85),
        "Design Tokens Audit per docs/DESIGN.md Section 1",
        fill=Colors.rgb_muted,
        font=sub_font,
    )

    swatches = [
        ("bg", Colors.bg, Colors.rgb_bg, "Base background"),
        ("surface", Colors.surface, Colors.rgb_surface, "Cards & panels"),
        ("surface_2", Colors.surface_2, Colors.rgb_surface_2, "Raised panels"),
        ("line", Colors.line, Colors.rgb_line, "Hairlines & grid"),
        ("gold", Colors.gold, Colors.rgb_gold, "Primary accent"),
        ("gold_light", Colors.gold_light, Colors.rgb_gold_light, "Highlight/top grad"),
        ("gold_dark", Colors.gold_dark, Colors.rgb_gold_dark, "Bar bottoms"),
        ("ivory", Colors.ivory, Colors.rgb_ivory, "Main body text"),
        ("muted", Colors.muted, Colors.rgb_muted, "Secondary / axis"),
        ("silver", Colors.silver, Colors.rgb_silver, "Second series"),
        ("danger", Colors.danger, Colors.rgb_danger, "Dashboard errors"),
    ]

    start_x = Layout.LANDSCAPE_SAFE_MARGIN
    start_y = 220
    card_w = 280
    card_h = 170

    for i, (name, hex_val, rgb_val, desc) in enumerate(swatches):
        row = i // 4
        col = i % 4
        x = start_x + col * (card_w + 30)
        y = start_y + row * (card_h + 30)

        # Card surface backing
        draw.rectangle(
            [x, y, x + card_w, y + card_h],
            fill=Colors.rgb_surface,
            outline=Colors.rgb_line,
            width=1,
        )
        # Swatch color block
        draw.rectangle(
            [x + 15, y + 15, x + 75, y + 75], fill=rgb_val, outline=Colors.rgb_line, width=1
        )
        # Texts
        draw.text((x + 85, y + 15), name, fill=Colors.rgb_ivory, font=label_font)
        draw.text((x + 85, y + 55), hex_val, fill=Colors.rgb_gold_light, font=sub_font)
        draw.text((x + 15, y + 95), desc, fill=Colors.rgb_muted, font=sub_font)

    img.save(OUT_DIR / "frame_1_palette_spec.png")


def render_frame_2_landscape_safe_margins():
    """Frame 2: Landscape Safe Margins & Safe Area Layout (1920x1080)."""
    img = Image.new("RGB", (Layout.LANDSCAPE_WIDTH, Layout.LANDSCAPE_HEIGHT), Colors.rgb_bg)
    draw = ImageDraw.Draw(img)

    margin = Layout.LANDSCAPE_SAFE_MARGIN
    w = Layout.LANDSCAPE_WIDTH
    h = Layout.LANDSCAPE_HEIGHT

    # Border for safe margins
    draw.rectangle([margin, margin, w - margin, h - margin], outline=Colors.rgb_gold, width=2)
    # Hairline guides
    draw.line([margin, 180, w - margin, 180], fill=Colors.rgb_line, width=1)
    draw.line([margin, h - 100, w - margin, h - 100], fill=Colors.rgb_line, width=1)

    title_font = get_font(BEBAS_FONT, Layout.MIN_TITLE_SIZE_LANDSCAPE)
    body_font = get_font(SANS_REG, Layout.MIN_LABEL_SIZE)
    sub_font = get_font(SANS_REG, Layout.MIN_AXIS_SIZE)

    draw.text(
        (margin + 20, margin + 20),
        "LANDSCAPE SAFE MARGIN AUDIT (60px ALL SIDES)",
        fill=Colors.rgb_ivory,
        font=title_font,
    )
    draw.text(
        (margin + 20, margin + 110),
        "Metric: 1920x1080 | Safe Area: 1800x960 | Status: COMPLIANT",
        fill=Colors.rgb_muted,
        font=sub_font,
    )

    # Content mockup
    draw.rectangle(
        [margin + 20, 220, margin + 600, 800], fill=Colors.rgb_surface, outline=Colors.rgb_line
    )
    draw.text((margin + 50, 260), "Leader Panel", fill=Colors.rgb_gold, font=body_font)
    draw.text((margin + 50, 320), "Rank 1: Virat Kohli", fill=Colors.rgb_ivory, font=body_font)
    draw.text((margin + 50, 380), "Centuries: 8", fill=Colors.rgb_gold_light, font=title_font)

    # Outro credits & watermark
    draw.text(
        (w - margin - 220, h - margin - 50), "GOLDREEL DATA", fill=Colors.rgb_muted, font=sub_font
    )
    draw.text(
        (margin + 20, h - margin - 50),
        "Source: Cricsheet Open Data",
        fill=Colors.rgb_muted,
        font=sub_font,
    )

    img.save(OUT_DIR / "frame_2_landscape_safe_margins.png")


def render_frame_3_portrait_safe_margins():
    """Frame 3: Portrait Safe Margins & Safe Area Layout (1080x1920)."""
    img = Image.new("RGB", (Layout.PORTRAIT_WIDTH, Layout.PORTRAIT_HEIGHT), Colors.rgb_bg)
    draw = ImageDraw.Draw(img)

    mx = Layout.PORTRAIT_SAFE_MARGIN_X
    m_top = Layout.PORTRAIT_SAFE_MARGIN_TOP
    m_bottom = Layout.PORTRAIT_SAFE_MARGIN_BOTTOM
    w = Layout.PORTRAIT_WIDTH
    h = Layout.PORTRAIT_HEIGHT

    # Boundary boxes
    draw.rectangle([mx, m_top, w - mx, h - m_bottom], outline=Colors.rgb_gold, width=2)
    # UI blackout zone at bottom
    draw.rectangle([0, h - m_bottom, w, h], fill=Colors.rgb_surface_2, outline=Colors.rgb_line)

    title_font = get_font(BEBAS_FONT, Layout.MIN_TITLE_SIZE_PORTRAIT)
    body_font = get_font(SANS_REG, Layout.MIN_LABEL_SIZE)
    sub_font = get_font(SANS_REG, Layout.MIN_AXIS_SIZE)

    draw.text(
        (mx + 20, m_top + 40), "SHORTS SAFE MARGIN AUDIT", fill=Colors.rgb_ivory, font=title_font
    )
    draw.text(
        (mx + 20, m_top + 140),
        "Bottom 120px Platform UI Exclusion Zone",
        fill=Colors.rgb_gold_light,
        font=sub_font,
    )
    draw.text(
        (mx + 20, h - m_bottom + 40),
        "[YouTube Shorts Platform UI Area - No Content]",
        fill=Colors.rgb_muted,
        font=sub_font,
    )

    # Mock portrait card
    draw.rectangle(
        [mx + 20, 300, w - mx - 20, 700], fill=Colors.rgb_surface, outline=Colors.rgb_line
    )
    draw.text((mx + 50, 340), "DC VS MARVEL TIMELINE", fill=Colors.rgb_gold, font=body_font)
    draw.text((mx + 50, 420), "1962: Spider-Man Debut", fill=Colors.rgb_ivory, font=title_font)
    draw.text(
        (mx + 50, 520), "Verified across Wikidata + GCD", fill=Colors.rgb_muted, font=sub_font
    )

    img.save(OUT_DIR / "frame_3_portrait_safe_margins.png")


def render_frame_4_background_geometry():
    """Frame 4: Signature Procedural Gold Geometric Lines Prototype."""
    w, h = Layout.LANDSCAPE_WIDTH, Layout.LANDSCAPE_HEIGHT
    img = Image.new("RGBA", (w, h), (10, 10, 10, 255))

    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    line_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    line_draw = ImageDraw.Draw(line_layer)

    # Deterministic seed
    rnd = random.Random(42)
    strokes = []
    for _ in range(6):
        x1 = rnd.randint(0, w)
        y1 = rnd.randint(0, h // 2)
        x2 = rnd.randint(0, w)
        y2 = rnd.randint(h // 2, h)
        width = rnd.randint(2, 6)
        alpha = rnd.randint(60, 115)  # 25% to 45%
        strokes.append((x1, y1, x2, y2, width, alpha))

    # Draw glow underneath
    gold_rgb = Colors.rgb_gold
    for x1, y1, x2, y2, width, alpha in strokes:
        glow_draw.line(
            [x1, y1, x2, y2],
            fill=(gold_rgb.r, gold_rgb.g, gold_rgb.b, int(alpha * 0.7)),
            width=width + 12,
        )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(16))

    # Draw sharp strokes
    for x1, y1, x2, y2, width, alpha in strokes:
        line_draw.line(
            [x1, y1, x2, y2], fill=(gold_rgb.r, gold_rgb.g, gold_rgb.b, alpha), width=width
        )

    # Vignette layer (55% black vignette)
    base = Image.alpha_composite(img, glow_layer)
    base = Image.alpha_composite(base, line_layer)
    vignette = Image.new("RGBA", (w, h), (10, 10, 10, 140))
    final = Image.alpha_composite(base, vignette).convert("RGB")

    # Add label
    d = ImageDraw.Draw(final)
    font = get_font(BEBAS_FONT, Layout.MIN_TITLE_SIZE_LANDSCAPE)
    sub_font = get_font(SANS_REG, Layout.MIN_LABEL_SIZE)
    d.text(
        (Layout.LANDSCAPE_SAFE_MARGIN, Layout.LANDSCAPE_SAFE_MARGIN),
        "PROCEDURAL GOLD GEOMETRIC SYSTEM",
        fill=Colors.rgb_gold,
        font=font,
    )
    d.text(
        (Layout.LANDSCAPE_SAFE_MARGIN, Layout.LANDSCAPE_SAFE_MARGIN + 80),
        "Seed=42, 6 diagonal strokes, Gaussian blur glow radius=16px, 55% vignette",
        fill=Colors.rgb_ivory,
        font=sub_font,
    )

    final.save(OUT_DIR / "frame_4_background_geometry.png")


def render_frame_5_typography_hierarchy():
    """Frame 5: Typographic Hierarchy Card."""
    img = Image.new("RGB", (Layout.LANDSCAPE_WIDTH, Layout.LANDSCAPE_HEIGHT), Colors.rgb_bg)
    draw = ImageDraw.Draw(img)
    m = Layout.LANDSCAPE_SAFE_MARGIN

    font_title = get_font(BEBAS_FONT, Layout.MIN_TITLE_SIZE_LANDSCAPE)
    font_lead = get_font(SANS_BOLD, 48)
    font_body = get_font(SANS_REG, Layout.MIN_LABEL_SIZE)
    font_axis = get_font(SANS_REG, Layout.MIN_AXIS_SIZE)

    draw.text((m, m), "TYPOGRAPHY HIERARCHY & SIZING AUDIT", fill=Colors.rgb_gold, font=font_title)
    draw.text(
        (m, m + 80),
        "Validation of Title (>=72px), Body (>=36px), Axis (>=28px)",
        fill=Colors.rgb_muted,
        font=font_axis,
    )

    # Specimen card
    card_x, card_y = m, 220
    draw.rectangle(
        [card_x, card_y, card_x + 1200, card_y + 480],
        fill=Colors.rgb_surface,
        outline=Colors.rgb_line,
    )

    draw.text(
        (card_x + 40, card_y + 40),
        "MOST IPL CENTURIES (2008 - 2024)",
        fill=Colors.rgb_ivory,
        font=font_lead,
    )
    draw.text(
        (card_x + 40, card_y + 110),
        "Rank 1: Virat Kohli (Royal Challengers Bengaluru)",
        fill=Colors.rgb_gold_light,
        font=font_body,
    )
    draw.text(
        (card_x + 40, card_y + 170),
        "Record: 8 Centuries | Strike Rate: 130.02",
        fill=Colors.rgb_ivory,
        font=font_body,
    )

    # Bar chart element mockup
    bar_y = card_y + 260
    draw.rectangle([card_x + 40, bar_y, card_x + 900, bar_y + 50], fill=Colors.rgb_gold)
    draw.rectangle([card_x + 900, bar_y, card_x + 910, bar_y + 50], fill=Colors.rgb_gold_light)
    draw.text((card_x + 930, bar_y + 8), "8", fill=Colors.rgb_ivory, font=font_lead)
    draw.text(
        (card_x + 40, bar_y + 70),
        "Axis: 0    2    4    6    8 (Centuries)",
        fill=Colors.rgb_muted,
        font=font_axis,
    )

    img.save(OUT_DIR / "frame_5_typography_hierarchy.png")


def render_frame_6_component_cards():
    """Frame 6: Component Cards, Badges, and Leader Highlight."""
    img = Image.new("RGB", (Layout.LANDSCAPE_WIDTH, Layout.LANDSCAPE_HEIGHT), Colors.rgb_bg)
    draw = ImageDraw.Draw(img)
    m = Layout.LANDSCAPE_SAFE_MARGIN

    font_title = get_font(BEBAS_FONT, Layout.MIN_TITLE_SIZE_LANDSCAPE)
    font_label = get_font(SANS_BOLD, Layout.MIN_LABEL_SIZE)
    font_sub = get_font(SANS_REG, Layout.MIN_AXIS_SIZE)

    draw.text((m, m), "DATA CARDS & BADGE SYSTEM", fill=Colors.rgb_gold, font=font_title)
    draw.text(
        (m, m + 80),
        "Series A (Gold), Series B (Silver), Status Badges",
        fill=Colors.rgb_muted,
        font=font_sub,
    )

    # Card 1: Leader Highlight
    draw.rectangle(
        [m, 220, m + 500, 600], fill=Colors.rgb_surface_2, outline=Colors.rgb_gold_light, width=2
    )
    # Badge
    draw.rectangle([m + 30, 250, m + 180, 290], fill=Colors.rgb_gold)
    draw.text((m + 45, 255), "LEADER", fill=Colors.rgb_bg, font=font_sub)
    draw.text((m + 30, 320), "Series A: Cricket", fill=Colors.rgb_gold, font=font_label)
    draw.text((m + 30, 380), "Virat Kohli", fill=Colors.rgb_ivory, font=font_label)
    draw.text((m + 30, 440), "Stat: 8 Centuries", fill=Colors.rgb_gold_light, font=font_sub)

    # Card 2: Runner Up (Silver)
    draw.rectangle(
        [m + 540, 220, m + 1040, 600], fill=Colors.rgb_surface, outline=Colors.rgb_line, width=1
    )
    draw.rectangle([m + 570, 250, m + 730, 290], fill=Colors.rgb_surface_2, outline=Colors.rgb_line)
    draw.text((m + 585, 255), "RUNNER UP", fill=Colors.rgb_silver, font=font_sub)
    draw.text((m + 570, 320), "Series B: Contender", fill=Colors.rgb_silver, font=font_label)
    draw.text((m + 570, 380), "Jos Buttler", fill=Colors.rgb_ivory, font=font_label)
    draw.text((m + 570, 440), "Stat: 7 Centuries", fill=Colors.rgb_muted, font=font_sub)

    img.save(OUT_DIR / "frame_6_component_cards.png")


def run_all():
    tracemalloc.start()
    t0 = time.perf_counter()

    render_frame_1_palette()
    render_frame_2_landscape_safe_margins()
    render_frame_3_portrait_safe_margins()
    render_frame_4_background_geometry()
    render_frame_5_typography_hierarchy()
    render_frame_6_component_cards()

    t1 = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Rendered 6 frames in {t1 - t0:.3f} s")
    print(f"Peak RAM: {peak / (1024 * 1024):.2f} MB")


if __name__ == "__main__":
    run_all()
