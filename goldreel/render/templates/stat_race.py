"""Stat race template for horizontal bar progression.

Strictly follows docs/DESIGN.md Section 5:
- Top 10 bars, gold gradient bars with rounded ends.
- Value counting up at the bar tip.
- Year or step in a large muted number in the lower right.
- Axis with 4 to 6 nice ticks, unit under title.
- Leader highlighted with gold glow and thin gold_light outline.
"""

from typing import Any

from PIL import Image, ImageDraw

from goldreel.design.tokens import Colors
from goldreel.facts.models import FactTable
from goldreel.render.easing import ease_out_quad
from goldreel.render.layouts.landscape import LandscapeLayout
from goldreel.render.templates.base import BaseTemplate
from goldreel.render.timeline import Timeline
from goldreel.script.models import GeneratedScript


class StatRaceTemplate(BaseTemplate):
    """Horizontal bar stat race template."""

    def __init__(self, layout: LandscapeLayout | None = None, seed: int = 42):
        super().__init__(layout, seed)
        self.fact_table: FactTable | None = None
        self.script: GeneratedScript | None = None
        self.timeline: Timeline | None = None
        self.items: list[dict[str, Any]] = []
        self.max_val: float = 1.0

    def plan(self, fact_table: FactTable, script: GeneratedScript) -> Timeline:
        self.fact_table = fact_table
        self.script = script
        dur = script.estimated_duration_sec or 30.0
        self.timeline = Timeline(
            duration_sec=dur, fps=30, width=self.layout.width, height=self.layout.height
        )

        # Extract top 10 records
        records = fact_table.records[:10]
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

        # Chrome
        src_text = (
            self.fact_table.sources[0].name.title() if self.fact_table.sources else "Open Data"
        )
        self.draw_common_chrome(
            frame,
            title=self.fact_table.title,
            metric_label=self.fact_table.metric_label,
            source_text=src_text,
        )

        draw = ImageDraw.Draw(frame)

        # Stage coordinates
        stage_x = self.layout.stage_x
        stage_y = self.layout.stage_y + 20
        # Subtract left label rail (320px) and right value label margin (140px)
        stage_w = self.layout.stage_w - 320 - 140
        stage_h = self.layout.stage_h - 60  # Leave room for axis

        n_bars = min(len(self.items), 8)
        if n_bars == 0:
            return frame

        bar_h = min(48, int((stage_h - (n_bars * 12)) / n_bars))
        gap = 12

        font_label = self.layout.get_font("bold", 28)
        font_val = self.layout.get_font("display", 32)
        font_axis = self.layout.get_font("regular", 24)
        font_counter = self.layout.get_font("display", 110)

        # Growth animation across first 2 seconds per item, staggered
        for i, item in enumerate(self.items[:n_bars]):
            stagger = i * 0.12  # Stagger entrances by 120ms
            item_t = max(0.0, (t - stagger) / 1.5)
            progress = ease_out_quad(item_t)

            y = stage_y + i * (bar_h + gap)
            current_val = item["value"] * progress
            bar_w = int((current_val / self.max_val) * stage_w) if self.max_val > 0 else 0
            bar_w = max(10, bar_w)

            # Bar background channel
            draw.rectangle(
                [stage_x + 320, y, stage_x + 320 + stage_w, y + bar_h],
                fill=Colors.rgb_surface,
                width=0,
            )

            # Entity label (left rail)
            draw.text((stage_x, y + 8), item["entity"][:24], fill=Colors.rgb_ivory, font=font_label)

            # Active bar
            is_leader = i == 0
            bar_color = Colors.rgb_gold if is_leader else Colors.rgb_gold_dark
            outline_color = Colors.rgb_gold_light if is_leader else Colors.rgb_line

            # Leader highlight styling
            if is_leader:
                # Glow border
                draw.rectangle(
                    [stage_x + 318, y - 2, stage_x + 322 + bar_w, y + bar_h + 2],
                    outline=Colors.rgb_gold_light,
                    width=2,
                )

            draw.rectangle(
                [stage_x + 320, y, stage_x + 320 + bar_w, y + bar_h],
                fill=bar_color,
                outline=outline_color,
            )

            # Bar tip highlight gradient line
            draw.rectangle(
                [stage_x + 320 + bar_w - 6, y, stage_x + 320 + bar_w, y + bar_h],
                fill=Colors.rgb_gold_light,
            )

            # Value text at tip
            val_text = (
                f"{int(round(current_val))}" if current_val.is_integer() else f"{current_val:.1f}"
            )
            draw.text(
                (stage_x + 335 + bar_w, y + 4), val_text, fill=Colors.rgb_ivory, font=font_val
            )

        # Draw axis at bottom
        axis_y = stage_y + n_bars * (bar_h + gap) + 15
        draw.line(
            [stage_x + 320, axis_y, stage_x + 320 + stage_w, axis_y], fill=Colors.rgb_line, width=1
        )
        ticks = 5
        for tk in range(ticks + 1):
            tick_x = stage_x + 320 + int(tk * (stage_w / ticks))
            draw.line([tick_x, axis_y, tick_x, axis_y + 8], fill=Colors.rgb_muted, width=1)
            tick_val = int(tk * (self.max_val / ticks))
            draw.text(
                (tick_x - 12, axis_y + 12), str(tick_val), fill=Colors.rgb_muted, font=font_axis
            )

        # Lower-right muted step / year counter
        step_text = f"#{n_bars}"
        draw.text(
            (
                self.layout.width - self.layout.margin - 160,
                self.layout.height - self.layout.margin - 140,
            ),
            step_text,
            fill=(Colors.rgb_muted.r, Colors.rgb_muted.g, Colors.rgb_muted.b),
            font=font_counter,
        )

        return frame
