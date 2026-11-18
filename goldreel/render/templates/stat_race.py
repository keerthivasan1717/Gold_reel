"""Stat race template for continuous horizontal bar progression and racing statistics.

Strictly follows docs/DESIGN.md Section 5:
- Continuous racing motion every second: bars dynamically growing, values ticking up.
- Smooth vertical re-sorting / overtaking via ease_in_out_quad.
- Vibrant, distinct colors for every single bar and team on the graph (no dull monochrome).
- Dynamic smooth axis scaling with round tick intervals.
- Prominent dynamic year/step counter in bottom right.
- High visual polish with intro scene, outro scene, group legend, and source attribution.
- Discrete metrics strictly tick up as whole numbers (e.g. centuries never show decimals).
"""

import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from goldreel.design.tokens import Colors
from goldreel.facts.models import FactTable
from goldreel.render.easing import clamp01, ease_in_out_quad, ease_out_quad
from goldreel.render.layouts.landscape import LandscapeLayout
from goldreel.render.layouts.portrait import PortraitLayout
from goldreel.render.templates.base import BaseTemplate
from goldreel.render.timeline import Timeline
from goldreel.script.models import GeneratedScript

# Comprehensive vibrant team / group color mappings (no dull grey)
SPORTS_GROUP_COLORS: dict[str, str] = {
    # International cricket & sports
    "IND": "#00E676",  # Electric Emerald
    "AUS": "#FFB703",  # Amber Gold
    "WI": "#E63946",   # Crimson Carmine
    "ENG": "#FF006E",  # Hot Pink / English Rose
    "NZ": "#06D6A0",   # Mint Teal
    "SA": "#00F5D4",   # Proteas Turquoise / Aqua
    "SL": "#3A86FF",   # Lankan Royal Blue
    "PAK": "#10B981",  # Pakistan Emerald
    "BAN": "#059669",  # Bengal Green
    "AFG": "#4361EE",  # Afghan Indigo
    "ZW": "#FB5607",   # Zimbabwe Orange
    "IRE": "#38B000",  # Ireland Shamrock Green
    # IPL franchises
    "RCB": "#E63946",  # Challengers Red
    "CSK": "#FFBE0B",  # Super Kings Yellow
    "MI": "#0077B6",   # Mumbai Blue
    "KKR": "#7209B7",  # Knight Riders Purple
    "RR": "#FF006E",   # Royals Pink
    "DC": "#3A86FF",   # Capitals Royal Blue
    "SRH": "#FB5607",  # Sunrisers Orange
    "PBKS": "#EF233C", # Punjab Crimson
    "GT": "#00B4D8",   # Gujarat Titans Cyan
    "LSG": "#00F5D4",  # Lucknow Super Giants Aqua
}

# 16-color ultra-vibrant fallback palette for unlisted entities
VIBRANT_PALETTE: list[str] = [
    "#00E676",  # Electric Emerald
    "#FFB703",  # Amber Gold
    "#E63946",  # Crimson Red
    "#3A86FF",  # Royal Blue
    "#00F5D4",  # Cyan Aqua
    "#9D4EDD",  # Neon Purple
    "#FF006E",  # Hot Pink
    "#FB5607",  # Sunset Orange
    "#06D6A0",  # Mint Green
    "#FFBE0B",  # Sun Yellow
    "#4361EE",  # Indigo Blue
    "#F72585",  # Cerise
    "#38B000",  # Bright Lime
    "#4CC9F0",  # Sky Blue
    "#F77F00",  # Tangerine
    "#7209B7",  # Deep Violet
]


def get_nice_ticks(max_val: float) -> tuple[list[int], int]:
    """Calculate 4 to 6 round tick values for chart axis."""
    if max_val <= 0:
        return [0, 5, 10], 10

    raw_step = max_val / 5.0
    magnitude = 10 ** math.floor(math.log10(max(1.0, raw_step)))
    normalized = raw_step / magnitude

    if normalized <= 1.5:
        step = 1 * magnitude
    elif normalized <= 3.5:
        step = 2 * magnitude
    elif normalized <= 7.5:
        step = 5 * magnitude
    else:
        step = 10 * magnitude

    step = max(1, int(step))
    axis_max = int(math.ceil(max_val / step)) * step
    axis_max = max(axis_max, step * 3)

    ticks = list(range(0, axis_max + 1, step))
    return ticks, axis_max


class StatRaceTemplate(BaseTemplate):
    """Horizontal bar stat race template with continuous racing motion and vibrant colors."""

    def __init__(self, layout: LandscapeLayout | PortraitLayout | None = None, seed: int = 42):
        super().__init__(layout, seed)
        self.fact_table: FactTable | None = None
        self.script: GeneratedScript | None = None
        self.timeline: Timeline | None = None
        self.is_portrait: bool = self.layout.height > self.layout.width

        # Race progression fields
        self.time_steps: list[str] = []
        self.values_by_step: dict[str, dict[str, float]] = {}
        self.entity_groups: dict[str, str] = {}
        self.entity_colors: dict[str, str] = {}
        self.legend_items: list[tuple[str, str]] = []
        self.is_discrete: bool = True
        self.unit: str = ""

        self.intro_s: float = 4.0
        self.outro_s: float = 5.0
        self.step_duration_s: float = 1.0

    def plan(self, fact_table: FactTable, script: GeneratedScript) -> Timeline:
        self.fact_table = fact_table
        self.script = script
        dur = script.estimated_duration_sec or 30.0
        self.timeline = Timeline(
            duration_sec=dur, fps=30, width=self.layout.width, height=self.layout.height
        )

        # Check if metric is discrete count (e.g. centuries, wickets, goals)
        unit = fact_table.records[0].unit if fact_table.records else ""
        self.unit = unit or "value"
        sample_val = fact_table.records[0].value if fact_table.records else 1.0
        try:
            self.is_discrete = float(sample_val).is_integer()
        except Exception:
            self.is_discrete = True

        # Check if time series provided or synthesize progression
        if fact_table.time_steps and fact_table.values_by_step:
            self.time_steps = list(fact_table.time_steps)
            self.values_by_step = dict(fact_table.values_by_step)
            self.entity_groups = dict(fact_table.entity_groups)
        else:
            self._synthesize_progression()

        # Build group colors and ensure NO dull gray bars anywhere
        self._build_color_palette()

        num_transitions = max(1, len(self.time_steps) - 1)
        body_dur = max(1.0, dur - self.intro_s - self.outro_s)
        self.step_duration_s = body_dur / num_transitions

        return self.timeline

    def _synthesize_progression(self) -> None:
        """Synthesize multi-step racing progression from static records."""
        records = self.fact_table.records[:10] if self.fact_table else []
        if not records:
            return

        years = list(range(2008, 2025))
        self.time_steps = [str(y) for y in years]
        self.values_by_step = {}
        self.entity_groups = {}

        for r in records:
            grp = r.context.get("team") or r.context.get("group") or ""
            # If long team name, extract abbreviation
            words = grp.split()
            code = "".join(w[0] for w in words).upper() if len(words) > 1 else grp[:3].upper()
            self.entity_groups[r.entity] = code

        n_steps = len(self.time_steps)
        for s_idx, step_name in enumerate(self.time_steps):
            step_vals: dict[str, float] = {}
            for r_idx, r in enumerate(records):
                final_v = float(r.value) if isinstance(r.value, (int, float)) else 10.0
                start_step = int(r_idx * (n_steps * 0.12))
                if s_idx < start_step:
                    v = 0.0
                else:
                    progress = min(1.0, (s_idx - start_step) / max(1, n_steps - start_step - 1))
                    curve = progress ** 1.3
                    v = final_v * curve
                    if self.is_discrete:
                        v = float(int(round(v)))
                step_vals[r.entity] = v
            self.values_by_step[step_name] = step_vals

    def _build_color_palette(self) -> None:
        """Assign distinct vibrant colors for each group and entity."""
        self.entity_colors = {}
        self.legend_items = []
        seen_groups: set[str] = set()

        all_entities = list(self.entity_groups.keys())
        for idx, entity in enumerate(all_entities):
            grp = self.entity_groups.get(entity, "").upper()
            if grp and grp in SPORTS_GROUP_COLORS:
                color = SPORTS_GROUP_COLORS[grp]
                if grp not in seen_groups:
                    self.legend_items.append((grp, color))
                    seen_groups.add(grp)
            else:
                # Deterministic vibrant color from rainbow palette
                color = VIBRANT_PALETTE[idx % len(VIBRANT_PALETTE)]
                display_label = grp if grp else entity[:3].upper()
                if display_label not in seen_groups and len(self.legend_items) < 7:
                    self.legend_items.append((display_label, color))
                    seen_groups.add(display_label)

            self.entity_colors[entity] = color

    def _get_avatar(self, entity: str, size: int, border_color: Any) -> Image.Image:
        """Return a circular player photo avatar with border ring, or stylized monogram."""
        if not hasattr(self, "_avatar_cache"):
            self._avatar_cache: dict[tuple[str, int, str], Image.Image] = {}

        key = (entity, size, str(border_color))
        if key in self._avatar_cache:
            return self._avatar_cache[key]

        slug = entity.lower().replace(" ", "_").replace("-", "_")
        img_path = Path("assets/images/players") / f"{slug}.png"

        total_size = size + 6
        avatar = Image.new("RGBA", (total_size, total_size), (0, 0, 0, 0))
        adraw = ImageDraw.Draw(avatar)
        r = size // 2
        cx, cy = r + 3, r + 3

        # Outer glowing ring in bar color
        adraw.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], fill=border_color)

        if img_path.exists():
            try:
                with Image.open(img_path) as raw_img:
                    raw_crop = raw_img.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
                    mask = Image.new("L", (size, size), 0)
                    mdraw = ImageDraw.Draw(mask)
                    mdraw.ellipse([0, 0, size, size], fill=255)
                    avatar.paste(raw_crop, (cx - r, cy - r), mask)
                self._avatar_cache[key] = avatar
                return avatar
            except Exception:
                pass

        # Stylized monogram fallback
        adraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=Colors.rgb_surface_2)
        initial = entity[0].upper() if entity else "?"
        font_init = self.layout.get_font("bold", max(14, int(size * 0.5)))
        adraw.text((cx, cy), initial, fill=border_color, font=font_init, anchor="mm")

        self._avatar_cache[key] = avatar
        return avatar

    def draw(self, t: float) -> Image.Image:
        dur = self.timeline.duration_sec if self.timeline else 30.0
        frame = self.bg.render(t, total_duration=dur)

        if not self.fact_table or not self.time_steps:
            return frame

        draw = ImageDraw.Draw(frame)

        # Global top progress line
        prog_w = int((t / max(dur, 0.1)) * self.layout.width)
        draw.rectangle([0, 0, prog_w, 6], fill=Colors.rgb_gold)

        src_text = self.fact_table.sources[0].name.title() if self.fact_table.sources else "Cricsheet"

        if self.is_portrait:
            self._draw_portrait(frame, draw, t, dur, src_text)
        else:
            self._draw_landscape(frame, draw, t, dur, src_text)

        return frame

    # =========================================================================
    # LANDSCAPE RENDERER (1920x1080)
    # =========================================================================

    def _draw_landscape(self, frame: Image.Image, draw: ImageDraw.ImageDraw, t: float, dur: float, src_text: str) -> None:
        """Render 1920x1080 horizontal stat race with continuous motion and vibrant colors."""
        if t < self.intro_s:
            self._draw_landscape_intro(frame, draw, t)
            return

        if t >= (dur - self.outro_s):
            self._draw_landscape_outro(frame, draw, dur - t, dur, src_text)
            return

        self._draw_landscape_body(frame, draw, t, dur, src_text)

    def _draw_landscape_intro(self, frame: Image.Image, draw: ImageDraw.ImageDraw, t: float) -> None:
        """Render Intro scene (0 to 4s) with animated accent reveal."""
        p = clamp01(t / self.intro_s)
        alpha = ease_out_quad(p / 0.25) if p < 0.25 else (ease_out_quad((1.0 - p) / 0.25) if p > 0.75 else 1.0)

        center_x = self.layout.width // 2
        center_y = int(self.layout.height * 0.44)

        # Pill chip: "TOP 10 LEADERBOARD"
        chip_w, chip_h = 240, 42
        chip_x = center_x - chip_w // 2
        chip_y = center_y - 140
        draw.rounded_rectangle(
            [chip_x, chip_y, chip_x + chip_w, chip_y + chip_h],
            radius=6,
            fill=Colors.rgb_surface_2,
            outline=Colors.rgb_gold,
            width=2,
        )
        font_chip = self.layout.get_font("bold", 24)
        draw.text((center_x, chip_y + chip_h // 2), "TOP 10 LEADERBOARD", fill=Colors.rgb_gold, font=font_chip, anchor="mm")

        # Main Title Line 1
        font_title1 = self.layout.get_font("display", 80)
        draw.text((center_x, center_y - 45), self.fact_table.title.upper(), fill=Colors.rgb_ivory, font=font_title1, anchor="mm")

        # Subtitle Line 2
        font_title2 = self.layout.get_font("display", 52)
        sub_title = self.fact_table.subtitle.upper() if self.fact_table.subtitle else self.fact_table.metric_label.upper()
        draw.text((center_x, center_y + 35), sub_title, fill=Colors.rgb_gold, font=font_title2, anchor="mm")

        # Animated Gold Sweep Accent Bar
        sweep_w = int(self.layout.width * 0.40 * ease_in_out_quad(min(1.0, p * 1.5)))
        bar_y = center_y + 90
        draw.rounded_rectangle([center_x - sweep_w // 2, bar_y, center_x + sweep_w // 2, bar_y + 6], radius=3, fill=Colors.rgb_gold)

        # Metric & Year Range line
        font_sub = self.layout.get_font("regular", 28)
        year_span = f"{self.time_steps[0][:4]} – {self.time_steps[-1][:4]}"
        metric_line = f"{self.fact_table.metric_label}  •  {year_span}"
        draw.text((center_x, bar_y + 40), metric_line, fill=Colors.rgb_muted, font=font_sub, anchor="mm")

        # Watermark
        font_watermark = self.layout.get_font("bold", 22)
        draw.text((self.layout.margin, self.layout.height - 40), "GOLDREEL", fill=Colors.rgb_muted, font=font_watermark)

    def _draw_landscape_outro(self, frame: Image.Image, draw: ImageDraw.ImageDraw, t_from_end: float, dur: float, src_text: str) -> None:
        """Render Outro scene (last 5s)."""
        box_w = int(self.layout.width * 0.65)
        box_h = int(self.layout.height * 0.36)
        box_x = (self.layout.width - box_w) // 2
        box_y = (self.layout.height - box_h) // 2

        draw.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + box_h], radius=14, fill=Colors.rgb_surface_2, outline=Colors.rgb_gold, width=3)

        font_large = self.layout.get_font("display", 76)
        font_sub = self.layout.get_font("bold", 42)
        font_src = self.layout.get_font("regular", 26)

        center_x = self.layout.width // 2
        draw.text((center_x, box_y + int(box_h * 0.35)), "ALL-TIME RECORD RACE COMPLETED", fill=Colors.rgb_ivory, font=font_large, anchor="mm")
        draw.text((center_x, box_y + int(box_h * 0.68)), "SUBSCRIBE FOR DAILY STAT RACES", fill=Colors.rgb_gold, font=font_sub, anchor="mm")

        source_text = f"Source: {src_text} | Open Data"
        draw.text((center_x, box_y + box_h + 35), source_text, fill=Colors.rgb_muted, font=font_src, anchor="mm")

        font_watermark = self.layout.get_font("bold", 22)
        draw.text((self.layout.margin, self.layout.height - 40), "GOLDREEL", fill=Colors.rgb_muted, font=font_watermark)

    def _draw_landscape_body(self, frame: Image.Image, draw: ImageDraw.ImageDraw, t: float, dur: float, src_text: str) -> None:
        """Render main landscape racing body with smooth overtaking and vivid bar colors."""
        body_t = t - self.intro_s
        transitions = len(self.time_steps) - 1
        raw_step = body_t / max(0.01, self.step_duration_s)
        step_idx = min(transitions - 1, int(raw_step))
        alpha = clamp01(raw_step - step_idx)

        step_from = self.time_steps[step_idx]
        step_to = self.time_steps[step_idx + 1]

        vals_from = self.values_by_step.get(step_from, {})
        vals_to = self.values_by_step.get(step_to, {})

        # Continuous value interpolation
        interp_vals: dict[str, float] = {}
        for entity in set(vals_from.keys()).union(vals_to.keys()):
            v0 = vals_from.get(entity, 0.0)
            v1 = vals_to.get(entity, v0)
            interp_vals[entity] = v0 + alpha * (v1 - v0)

        # Smooth vertical re-sorting: compute ranks at step_from and step_to
        active_from = sorted([e for e in vals_from if vals_from[e] > 0.0], key=lambda e: vals_from[e], reverse=True)
        rank_from_map = {e: float(i) for i, e in enumerate(active_from)}

        active_to = sorted([e for e in vals_to if vals_to[e] > 0.0], key=lambda e: vals_to[e], reverse=True)
        rank_to_map = {e: float(i) for i, e in enumerate(active_to)}

        active_current = [e for e in interp_vals if interp_vals[e] > 0.0]

        # Smooth floating rank_y for overtaking transitions
        entity_rank_y: dict[str, float] = {}
        ease_t = ease_in_out_quad(alpha)

        for e in active_current:
            if e in rank_from_map and e in rank_to_map:
                r0 = rank_from_map[e]
                r1 = rank_to_map[e]
                entity_rank_y[e] = r0 + ease_t * (r1 - r0)
            elif e in rank_to_map:
                # Newly entering entity glides in smoothly from bottom
                r0 = min(10.0, float(len(active_from)))
                r1 = rank_to_map[e]
                entity_rank_y[e] = r0 + ease_out_quad(alpha) * (r1 - r0)
            elif e in rank_from_map:
                # Dropping entity glides out
                r0 = rank_from_map[e]
                entity_rank_y[e] = r0 + ease_t * (10.0 - r0)
            else:
                entity_rank_y[e] = 10.0

        # Visible entities in top 10
        visible_entities = sorted(
            [e for e in active_current if entity_rank_y[e] < 9.99],
            key=lambda e: entity_rank_y[e],
        )[:10]

        # Smooth dynamic axis scaling
        max_from = max(vals_from.values()) if vals_from else 10.0
        ticks_from, axis_max_from = get_nice_ticks(max_from)

        max_to = max(vals_to.values()) if vals_to else 10.0
        ticks_to, axis_max_to = get_nice_ticks(max_to)

        smooth_axis_max = float(axis_max_from) + ease_t * float(axis_max_to - axis_max_from)
        smooth_axis_max = max(10.0, smooth_axis_max)
        ticks = ticks_to if axis_max_to >= axis_max_from else ticks_from

        # 1. Header (y: 40 - 120)
        font_title = self.layout.get_font("display", 54)
        font_sub = self.layout.get_font("bold", 26)

        draw.text((self.layout.margin, 38), self.fact_table.title.upper(), fill=Colors.rgb_ivory, font=font_title)
        sub_text = f"{self.fact_table.subtitle or 'Historical Progression'}  •  {self.fact_table.metric_label}"
        draw.text((self.layout.margin, 96), sub_text, fill=Colors.rgb_gold, font=font_sub)

        # Layout boundaries
        name_col_width = int(self.layout.width * 0.22)
        bar_x_start = self.layout.margin + name_col_width + 15
        max_bar_width = int(self.layout.width * 0.60)
        bar_x_end = bar_x_start + max_bar_width

        chart_top_y = int(self.layout.height * 0.16)
        chart_bottom_y = int(self.layout.height * 0.88)

        # 2. Dynamic Axis & Gridlines
        font_tick = self.layout.get_font("regular", 22)
        unit_tag = f"▲ Axis ({self.unit})"
        draw.text((bar_x_end, chart_top_y - 32), unit_tag, font=font_tick, fill=Colors.rgb_gold, anchor="rb")

        for tick in ticks:
            tick_x = bar_x_start + int((tick / smooth_axis_max) * max_bar_width)
            if tick_x <= bar_x_end + 1:
                draw.line([(tick_x, chart_top_y - 6), (tick_x, chart_bottom_y)], fill="#1E232B", width=1)
                draw.text((tick_x, chart_top_y - 12), f"{tick:,}", font=font_tick, fill=Colors.rgb_muted, anchor="mb")

        draw.line([(bar_x_start, chart_top_y - 6), (bar_x_end, chart_top_y - 6)], fill=Colors.rgb_line, width=1)

        # 3. Dynamic Bars & Names
        bar_start_y = chart_top_y + 10
        bar_height = 54
        bar_gap = 16

        font_name = self.layout.get_font("bold", 32)
        font_group_tag = self.layout.get_font("bold", 20)
        font_val = self.layout.get_font("display", 36)

        for entity in visible_entities:
            rank_y = entity_rank_y[entity]
            y_pos = int(bar_start_y + rank_y * (bar_height + bar_gap))
            raw_val = interp_vals[entity]

            # Format value label (discrete counts strictly integers, NO 5.1 decimals)
            val_text = f"{int(round(raw_val)):,}" if self.is_discrete else f"{raw_val:,.1f}"

            group_code = self.entity_groups.get(entity, "")
            bar_color = self.entity_colors.get(entity, Colors.rgb_gold)

            # Left Name Rail
            tag_width = 46 if group_code else 0
            name_x = self.layout.margin + name_col_width - tag_width - 8
            name_y = y_pos + bar_height // 2

            draw.text((name_x, name_y), entity[:24], font=font_name, fill=Colors.rgb_ivory, anchor="rm")

            # Group tag chip (e.g. IND, AUS, WI, ENG, NZ, SA, SL)
            if group_code:
                tag_x = name_x + 6
                tag_h = int(bar_height * 0.48)
                tag_y = name_y - tag_h // 2
                draw.rounded_rectangle([tag_x, tag_y, tag_x + tag_width, tag_y + tag_h], radius=3, fill=Colors.rgb_surface_2, outline=bar_color, width=1)
                draw.text((tag_x + tag_width // 2, tag_y + tag_h // 2), group_code, font=font_group_tag, fill=bar_color, anchor="mm")

            # Bar Channel Background
            draw.rounded_rectangle([bar_x_start, y_pos, bar_x_start + max_bar_width, y_pos + bar_height], radius=6, fill=Colors.rgb_surface)

            # Active Vibrant Bar
            target_bar_w = int((raw_val / smooth_axis_max) * max_bar_width) if smooth_axis_max > 0 else 0
            bar_w = max(6, target_bar_w)
            draw.rounded_rectangle([bar_x_start, y_pos, bar_x_start + bar_w, y_pos + bar_height], radius=6, fill=bar_color)

            # Luminous glowing tip
            draw.rounded_rectangle([bar_x_start + bar_w - 8, y_pos, bar_x_start + bar_w, y_pos + bar_height], radius=4, fill="#FFFFFF")

            # Circular player photo avatar mounted at the leading edge of the bar
            avatar_img = self._get_avatar(entity, size=bar_height + 4, border_color=bar_color)
            av_w, av_h = avatar_img.size
            av_x = bar_x_start + bar_w - (av_w // 2)
            av_y = y_pos + bar_height // 2 - (av_h // 2)
            frame.paste(avatar_img, (av_x, av_y), avatar_img)

            # Value label directly right of avatar
            val_x = av_x + av_w + 10
            draw.text((val_x, name_y), val_text, font=font_val, fill=bar_color, anchor="lm")

        # 4. Large Dynamic Year Counter in Bottom Right
        font_year = self.layout.get_font("display", 112)
        display_step = step_from.replace(" Mid", "").replace(" End", "")
        draw.text((self.layout.width - 80, self.layout.height - 105), display_step, font=font_year, fill=Colors.rgb_gold, anchor="rs")

        # 5. Footer: Vibrant Legend & Source Credit
        footer_y = self.layout.height - 70
        self._draw_legend(draw, footer_y)

        font_source = self.layout.get_font("regular", 22)
        source_label = f"Source: {src_text} | GoldReel Visuals"
        draw.text((self.layout.width - self.layout.margin, footer_y + 8), source_label, font=font_source, fill=Colors.rgb_muted, anchor="rm")

        # Watermark
        font_watermark = self.layout.get_font("bold", 22)
        draw.text((self.layout.margin, self.layout.height - 35), "GOLDREEL", fill=Colors.rgb_muted, font=font_watermark)

    def _draw_legend(self, draw: ImageDraw.ImageDraw, y_pos: int) -> None:
        """Draw vibrant legend chips at bottom left."""
        chip_size = 18
        font_legend = self.layout.get_font("regular", 22)

        cur_x = self.layout.margin
        for group_name, color in self.legend_items[:7]:
            draw.rounded_rectangle([cur_x, y_pos, cur_x + chip_size, y_pos + chip_size], radius=3, fill=color)
            draw.text((cur_x + chip_size + 8, y_pos + chip_size // 2), group_name, font=font_legend, fill=Colors.rgb_ivory, anchor="lm")
            bbox = draw.textbbox((0, 0), group_name, font=font_legend)
            text_w = bbox[2] - bbox[0]
            cur_x += chip_size + text_w + 24

    # =========================================================================
    # PORTRAIT RENDERER (1080x1920)
    # =========================================================================

    def _draw_portrait(self, frame: Image.Image, draw: ImageDraw.ImageDraw, t: float, dur: float, src_text: str) -> None:
        """Render 1080x1920 portrait stat race filling the frame with continuous racing motion."""
        margin = 60
        stage_w = self.layout.width - (2 * margin)

        body_t = t
        transitions = len(self.time_steps) - 1
        raw_step = body_t / max(0.01, self.step_duration_s)
        step_idx = min(transitions - 1, int(raw_step))
        alpha = clamp01(raw_step - step_idx)

        step_from = self.time_steps[step_idx]
        step_to = self.time_steps[step_idx + 1]

        vals_from = self.values_by_step.get(step_from, {})
        vals_to = self.values_by_step.get(step_to, {})

        interp_vals: dict[str, float] = {}
        for entity in set(vals_from.keys()).union(vals_to.keys()):
            v0 = vals_from.get(entity, 0.0)
            v1 = vals_to.get(entity, v0)
            interp_vals[entity] = v0 + alpha * (v1 - v0)

        active_to = sorted([e for e in vals_to if vals_to[e] > 0.0], key=lambda e: vals_to[e], reverse=True)
        rank_to_map = {e: float(i) for i, e in enumerate(active_to)}
        active_from = sorted([e for e in vals_from if vals_from[e] > 0.0], key=lambda e: vals_from[e], reverse=True)
        rank_from_map = {e: float(i) for i, e in enumerate(active_from)}

        active_current = [e for e in interp_vals if interp_vals[e] > 0.0]
        ease_t = ease_in_out_quad(alpha)

        entity_rank_y: dict[str, float] = {}
        for e in active_current:
            if e in rank_from_map and e in rank_to_map:
                entity_rank_y[e] = rank_from_map[e] + ease_t * (rank_to_map[e] - rank_from_map[e])
            elif e in rank_to_map:
                entity_rank_y[e] = min(6.0, float(len(active_from))) + ease_out_quad(alpha) * (rank_to_map[e] - min(6.0, float(len(active_from))))
            else:
                entity_rank_y[e] = 6.0

        visible_entities = sorted([e for e in active_current if entity_rank_y[e] < 5.99], key=lambda e: entity_rank_y[e])[:6]

        max_val = max(interp_vals.values()) if interp_vals else 10.0
        _, axis_max = get_nice_ticks(max_val)

        # 1. Header (y: 60 - 240)
        font_pill = self.layout.get_font("bold", 28)
        font_title = self.layout.get_font("display", 76)
        font_metric = self.layout.get_font("bold", 34)

        draw.rounded_rectangle([margin, 60, margin + 280, 102], radius=6, fill=Colors.rgb_surface_2, outline=Colors.rgb_gold, width=2)
        draw.text((margin + 20, 70), "STAT RACE LEADERBOARD", fill=Colors.rgb_gold, font=font_pill)
        draw.text((margin, 120), self.fact_table.title.upper()[:28], fill=Colors.rgb_ivory, font=font_title)
        draw.text((margin, 205), self.fact_table.metric_label.upper(), fill=Colors.rgb_gold, font=font_metric)
        draw.line([margin, 250, margin + stage_w, 250], fill=Colors.rgb_line, width=1)

        # 2. Race Bars Stage (y: 270 - 1380)
        bar_slot_h = 175
        bar_h = 56
        font_label = self.layout.get_font("bold", 38)
        font_val = self.layout.get_font("display", 46)
        font_rank = self.layout.get_font("bold", 36)
        channel_w = stage_w - 200

        for entity in visible_entities:
            rank_y = entity_rank_y[entity]
            slot_y = int(270 + rank_y * bar_slot_h)
            raw_val = interp_vals[entity]

            val_text = f"{int(round(raw_val)):,}" if self.is_discrete else f"{raw_val:,.1f}"
            bar_color = self.entity_colors.get(entity, Colors.rgb_gold)
            group_code = self.entity_groups.get(entity, "")

            # Rank, Photo Avatar & Name
            int_rank = int(round(rank_y)) + 1
            draw.text((margin, slot_y + 8), f"#{int_rank}", fill=Colors.rgb_gold if int_rank == 1 else Colors.rgb_muted, font=font_rank)

            avatar_row = self._get_avatar(entity, size=46, border_color=bar_color)
            av_rw, av_rh = avatar_row.size
            frame.paste(avatar_row, (margin + 60, slot_y + 2), avatar_row)

            draw.text((margin + 120, slot_y + 8), entity[:18], fill=Colors.rgb_ivory, font=font_label)

            if group_code:
                draw.rounded_rectangle([margin + 420, slot_y + 12, margin + 490, slot_y + 44], radius=4, fill=Colors.rgb_surface_2, outline=bar_color, width=1)
                draw.text((margin + 455, slot_y + 28), group_code, fill=bar_color, font=self.layout.get_font("bold", 22), anchor="mm")

            # Bar Channel Background
            bar_y = slot_y + 60
            draw.rounded_rectangle([margin, bar_y, margin + channel_w, bar_y + bar_h], radius=6, fill=Colors.rgb_surface)

            # Active Vibrant Bar
            bar_w = int((raw_val / axis_max) * channel_w) if axis_max > 0 else 0
            bar_w = max(10, bar_w)
            draw.rounded_rectangle([margin, bar_y, margin + bar_w, bar_y + bar_h], radius=6, fill=bar_color)

            # Glowing tip
            draw.rounded_rectangle([margin + bar_w - 8, bar_y, margin + bar_w, bar_y + bar_h], radius=4, fill="#FFFFFF")

            # Circular photo avatar mounted at bar tip
            avatar_bar = self._get_avatar(entity, size=bar_h + 4, border_color=bar_color)
            av_bw, av_bh = avatar_bar.size
            av_bx = margin + bar_w - (av_bw // 2)
            av_by = bar_y + bar_h // 2 - (av_bh // 2)
            frame.paste(avatar_bar, (av_bx, av_by), avatar_bar)

            # Value text right of avatar
            draw.text((av_bx + av_bw + 10, bar_y + 6), val_text, fill=bar_color, font=font_val)

        # 3. Dynamic Year Display (y: 1320)
        font_year = self.layout.get_font("display", 96)
        display_step = step_from.replace(" Mid", "").replace(" End", "")
        draw.text((margin + stage_w, 1340), display_step, fill=Colors.rgb_gold, font=font_year, anchor="rs")

        # 4. Analytical Takeaway Box (y: 1420 - 1730)
        ins_y = 1420
        draw.rounded_rectangle([margin, ins_y, margin + stage_w, ins_y + 300], radius=10, fill=Colors.rgb_surface_2, outline=Colors.rgb_gold, width=2)
        font_ins_hdr = self.layout.get_font("bold", 32)
        font_ins_body = self.layout.get_font("regular", 36)

        draw.text((margin + 30, ins_y + 30), "RACE ANALYTICAL TAKEAWAY", fill=Colors.rgb_gold, font=font_ins_hdr)
        if self.script and self.script.insight:
            draw.text((margin + 30, ins_y + 85), self.script.insight[:46], fill=Colors.rgb_ivory, font=font_ins_body)
            if len(self.script.insight) > 46:
                draw.text((margin + 30, ins_y + 140), self.script.insight[46:95], fill=Colors.rgb_ivory, font=font_ins_body)
            if len(self.script.insight) > 95:
                draw.text((margin + 30, ins_y + 195), self.script.insight[95:145], fill=Colors.rgb_ivory, font=font_ins_body)

        # 5. Footer (y: 1750 - 1860)
        font_footer = self.layout.get_font("regular", 28)
        draw.text((margin, 1755), f"Source: {src_text} | GoldReel Visuals", fill=Colors.rgb_muted, font=font_footer)
        draw.text((margin + stage_w - 160, 1755), "GOLDREEL", fill=Colors.rgb_muted, font=font_footer)
