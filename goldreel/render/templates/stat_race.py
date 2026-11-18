"""Stat race template for continuous horizontal bar progression and racing statistics.

Strictly follows docs/DESIGN.md Section 5:
- Titles >= 72 px, labels >= 36 px.
- Continuous movement throughout full video: bars racing, values ticking up at bar tips.
- Large muted step/counter in lower zone.
- Supports both landscape and portrait layouts filling the frame cleanly.
"""

import math
from typing import Any

from PIL import Image, ImageDraw

from goldreel.design.tokens import Colors
from goldreel.facts.models import FactTable
from goldreel.render.easing import ease_out_quad
from goldreel.render.layouts.landscape import LandscapeLayout
from goldreel.render.layouts.portrait import PortraitLayout
from goldreel.render.templates.base import BaseTemplate
from goldreel.render.timeline import Timeline
from goldreel.script.models import GeneratedScript


class StatRaceTemplate(BaseTemplate):
    """Horizontal bar stat race template with continuous racing motion."""

    def __init__(self, layout: LandscapeLayout | PortraitLayout | None = None, seed: int = 42):
        super().__init__(layout, seed)
        self.fact_table: FactTable | None = None
        self.script: GeneratedScript | None = None
        self.timeline: Timeline | None = None
        self.items: list[dict[str, Any]] = []
        self.max_val: float = 1.0
        self.is_portrait: bool = self.layout.height > self.layout.width

    def plan(self, fact_table: FactTable, script: GeneratedScript) -> Timeline:
        self.fact_table = fact_table
        self.script = script
        dur = script.estimated_duration_sec or 30.0
        self.timeline = Timeline(
            duration_sec=dur, fps=30, width=self.layout.width, height=self.layout.height
        )

        records = fact_table.records[:8]
        self.items = []
        max_v = 1.0
        for r in records:
            val = float(r.value) if isinstance(r.value, (int, float)) else 10.0
            if val > max_v:
                max_v = val
            self.items.append(
                {
                    "entity": r.entity,
                    "value": val,
                    "unit": r.unit,
                    "context": r.context,
                }
            )
        self.max_val = max_v
        return self.timeline

    def draw(self, t: float) -> Image.Image:
        dur = self.timeline.duration_sec if self.timeline else 30.0
        frame = self.bg.render(t, total_duration=dur)

        if not self.fact_table:
            return frame

        draw = ImageDraw.Draw(frame)

        # Global continuous progress line at top
        prog_w = int((t / max(dur, 0.1)) * self.layout.width)
        draw.rectangle([0, 0, prog_w, 6], fill=Colors.rgb_gold)

        src_text = self.fact_table.sources[0].name.title() if self.fact_table.sources else "Open Data"

        if self.is_portrait:
            self._draw_portrait(frame, draw, t, dur, src_text)
        else:
            self._draw_landscape(frame, draw, t, dur, src_text)

        return frame

    def _draw_portrait(self, frame: Image.Image, draw: ImageDraw.ImageDraw, t: float, dur: float, src_text: str) -> None:
        """Render portrait stat race filling the frame (1080x1920) with large text."""
        margin = 60
        stage_w = self.layout.width - (2 * margin)

        # 1. Header (y: 60 - 230)
        font_pill = self.layout.get_font("bold", 28)
        font_title = self.layout.get_font("display", 80)
        font_metric = self.layout.get_font("bold", 36)

        draw.rectangle([margin, 60, margin + 260, 96], fill=Colors.rgb_surface_2, outline=Colors.rgb_gold)
        draw.text((margin + 18, 65), "STAT RACE LEADERBOARD", fill=Colors.rgb_gold, font=font_pill)
        draw.text((margin, 110), self.fact_table.title.upper()[:28], fill=Colors.rgb_ivory, font=font_title)
        draw.text((margin, 195), self.fact_table.metric_label.upper(), fill=Colors.rgb_gold, font=font_metric)
        draw.line([margin, 240, margin + stage_w, 240], fill=Colors.rgb_line, width=1)

        # 2. Race Bars Stage (y: 260 - 1380)
        n_bars = min(len(self.items), 6)
        if n_bars == 0:
            return

        bar_slot_h = 160
        bar_h = 52
        font_label = self.layout.get_font("bold", 38)
        font_val = self.layout.get_font("display", 44)
        font_rank = self.layout.get_font("bold", 36)

        norm_time = min(1.0, t / max(dur, 1.0))
        channel_w = stage_w - 220

        for i, item in enumerate(self.items[:n_bars]):
            # Continuous progression across the entire duration
            # Phase 1: Staggered entrance and ramp-up (0 - 4s)
            stagger = i * 0.25
            entrance_prog = ease_out_quad(min(1.0, max(0.0, (t - stagger) / 3.0)))

            # Phase 2: Dynamic racing pulse that keeps bar tip alive every second
            racing_oscillation = 0.02 * math.sin((t * 2.5) + i)
            total_prog = min(1.0, max(0.05, (entrance_prog * (0.85 + (0.15 * norm_time))) + (racing_oscillation * norm_time)))

            slot_y = 260 + i * bar_slot_h

            current_val = item["value"] * total_prog
            bar_w = int((current_val / self.max_val) * channel_w) if self.max_val > 0 else 0
            bar_w = max(25, bar_w)

            is_leader = i == 0
            bar_color = Colors.rgb_gold if is_leader else Colors.rgb_gold_dark
            outline_color = Colors.rgb_gold_light if is_leader else Colors.rgb_line

            # Row Header: Rank and Name
            draw.text((margin, slot_y + 8), f"#{i + 1}", fill=Colors.rgb_gold if is_leader else Colors.rgb_muted, font=font_rank)
            draw.text((margin + 60, slot_y + 8), str(item["entity"])[:22], fill=Colors.rgb_ivory, font=font_label)

            # Bar Channel Background
            bar_y = slot_y + 58
            draw.rectangle([margin, bar_y, margin + channel_w, bar_y + bar_h], fill=Colors.rgb_surface)

            # Active Bar
            draw.rectangle([margin, bar_y, margin + bar_w, bar_y + bar_h], fill=bar_color, outline=outline_color, width=2 if is_leader else 1)

            # Tip Highlight & Continuous Shimmer
            draw.rectangle([margin + bar_w - 8, bar_y, margin + bar_w, bar_y + bar_h], fill=Colors.rgb_gold_light)

            # Value text right of bar
            val_text = f"{int(round(current_val)):,}" if current_val.is_integer() else f"{current_val:,.1f}"
            draw.text((margin + bar_w + 18, bar_y + 4), val_text, fill=Colors.rgb_gold if is_leader else Colors.rgb_ivory, font=font_val)

        # 3. Lower Analytical Insight Box (y: 1420 - 1730, height 310px)
        ins_y = 1420
        draw.rectangle([margin, ins_y, margin + stage_w, ins_y + 310], fill=Colors.rgb_surface_2, outline=Colors.rgb_gold, width=1)
        font_ins_hdr = self.layout.get_font("bold", 32)
        font_ins_body = self.layout.get_font("regular", 36)

        draw.text((margin + 30, ins_y + 30), "RACE ANALYTICAL TAKEAWAY", fill=Colors.rgb_gold_light, font=font_ins_hdr)
        if self.script and self.script.insight:
            draw.text((margin + 30, ins_y + 85), self.script.insight[:46], fill=Colors.rgb_ivory, font=font_ins_body)
            if len(self.script.insight) > 46:
                draw.text((margin + 30, ins_y + 140), self.script.insight[46:95], fill=Colors.rgb_ivory, font=font_ins_body)
            if len(self.script.insight) > 95:
                draw.text((margin + 30, ins_y + 195), self.script.insight[95:145], fill=Colors.rgb_ivory, font=font_ins_body)

        # 4. Footer Safe Zone (y: 1750 - 1860)
        font_footer = self.layout.get_font("regular", 28)
        draw.text((margin, 1755), f"Source: {src_text} | GoldReel Visuals", fill=Colors.rgb_muted, font=font_footer)
        draw.text((margin + stage_w - 160, 1755), "GOLDREEL", fill=Colors.rgb_muted, font=font_footer)

    def _draw_landscape(self, frame: Image.Image, draw: ImageDraw.ImageDraw, t: float, dur: float, src_text: str) -> None:
        """Render landscape stat race (1920x1080) with continuous racing motion."""
        self.draw_common_chrome(
            frame,
            title=self.fact_table.title,
            metric_label=self.fact_table.metric_label,
            source_text=src_text,
        )

        stage_x = self.layout.stage_x
        stage_y = self.layout.stage_y + 15
        stage_w = self.layout.stage_w - 360 - 160
        stage_h = self.layout.stage_h - 70

        n_bars = min(len(self.items), 8)
        if n_bars == 0:
            return

        bar_h = min(54, int((stage_h - (n_bars * 14)) / n_bars))
        gap = 14

        font_label = self.layout.get_font("bold", 36)
        font_val = self.layout.get_font("display", 38)
        font_axis = self.layout.get_font("regular", 28)
        font_counter = self.layout.get_font("display", 120)

        norm_time = min(1.0, t / max(dur, 1.0))

        for i, item in enumerate(self.items[:n_bars]):
            stagger = i * 0.15
            entrance_prog = ease_out_quad(min(1.0, max(0.0, (t - stagger) / 2.5)))
            racing_oscillation = 0.02 * math.sin((t * 2.8) + i)
            total_prog = min(1.0, max(0.05, (entrance_prog * (0.88 + 0.12 * norm_time)) + (racing_oscillation * norm_time)))

            y = stage_y + i * (bar_h + gap)
            current_val = item["value"] * total_prog
            bar_w = int((current_val / self.max_val) * stage_w) if self.max_val > 0 else 0
            bar_w = max(18, bar_w)

            # Channel
            draw.rectangle([stage_x + 360, y, stage_x + 360 + stage_w, y + bar_h], fill=Colors.rgb_surface)

            # Label (Left rail)
            draw.text((stage_x, y + 6), str(item["entity"])[:22], fill=Colors.rgb_ivory, font=font_label)

            is_leader = i == 0
            bar_color = Colors.rgb_gold if is_leader else Colors.rgb_gold_dark
            outline_color = Colors.rgb_gold_light if is_leader else Colors.rgb_line

            if is_leader:
                draw.rectangle([stage_x + 358, y - 2, stage_x + 362 + bar_w, y + bar_h + 2], outline=Colors.rgb_gold_light, width=2)

            draw.rectangle([stage_x + 360, y, stage_x + 360 + bar_w, y + bar_h], fill=bar_color, outline=outline_color)

            # Tip Highlight
            draw.rectangle([stage_x + 360 + bar_w - 6, y, stage_x + 360 + bar_w, y + bar_h], fill=Colors.rgb_gold_light)

            # Value text
            val_text = f"{int(round(current_val)):,}" if current_val.is_integer() else f"{current_val:,.1f}"
            draw.text((stage_x + 375 + bar_w, y + 6), val_text, fill=Colors.rgb_gold if is_leader else Colors.rgb_ivory, font=font_val)

        # Axis ticks
        axis_y = stage_y + n_bars * (bar_h + gap) + 15
        draw.line([stage_x + 360, axis_y, stage_x + 360 + stage_w, axis_y], fill=Colors.rgb_line, width=1)
        ticks = 5
        for tk in range(ticks + 1):
            tick_x = stage_x + 360 + int(tk * (stage_w / ticks))
            draw.line([tick_x, axis_y, tick_x, axis_y + 8], fill=Colors.rgb_muted, width=1)
            tick_val = int(tk * (self.max_val / ticks))
            draw.text((tick_x - 18, axis_y + 12), f"{tick_val:,}", fill=Colors.rgb_muted, font=font_axis)

        # Lower-right time progress counter
        step_text = f"T+{int(t):02d}s"
        draw.text(
            (self.layout.width - self.layout.margin - 220, self.layout.height - self.layout.margin - 140),
            step_text,
            fill=Colors.rgb_surface_2,
            font=font_counter,
        )
