"""Ranked countdown template.

Strictly follows docs/DESIGN.md Section 5:
- Big gold rank number.
- Card slides in from the right (0.5 s ease-out).
- Stat bar grows (0.8 s).
- One-line fact, left rail with revealed items.
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


class RankedCountdownTemplate(BaseTemplate):
    """Ranked countdown template displaying successive cards."""

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

        records = fact_table.records[:5]  # Top 5 countdown
        # Reverse to count down from 5 to 1
        countdown_records = list(reversed(records))
        self.items = []
        max_v = 1.0
        for idx, r in enumerate(countdown_records):
            val = float(r.value) if isinstance(r.value, (int, float)) else 10.0
            if val > max_v:
                max_v = val
            rank_num = r.rank or (len(countdown_records) - idx)
            self.items.append(
                {
                    "rank": rank_num,
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

        if not self.fact_table or not self.items:
            return frame

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

        # Determine which item is active based on time segment
        n_items = len(self.items)
        sec_per_item = dur / n_items
        active_idx = min(int(t // sec_per_item), n_items - 1)
        item_t = t - (active_idx * sec_per_item)
        current_item = self.items[active_idx]

        # 1. Left Rail: previously revealed items
        rail_x = self.layout.stage_x
        rail_y = self.layout.stage_y
        rail_w = 420
        font_rail = self.layout.get_font("regular", 24)
        font_rail_rank = self.layout.get_font("bold", 24)

        draw.rectangle(
            [rail_x, rail_y, rail_x + rail_w, rail_y + self.layout.stage_h],
            fill=Colors.rgb_surface,
            outline=Colors.rgb_line,
        )
        draw.text(
            (rail_x + 20, rail_y + 20), "COUNTDOWN PROGRESS", fill=Colors.rgb_muted, font=font_rail
        )

        for i in range(active_idx + 1):
            past = self.items[i]
            row_y = rail_y + 60 + i * 45
            is_cur = i == active_idx
            rank_color = Colors.rgb_gold if is_cur else Colors.rgb_muted
            text_color = Colors.rgb_ivory if is_cur else Colors.rgb_silver
            draw.text(
                (rail_x + 25, row_y), f"#{past['rank']}", fill=rank_color, font=font_rail_rank
            )
            draw.text(
                (rail_x + 85, row_y), f"{past['entity'][:18]}", fill=text_color, font=font_rail
            )

        # 2. Main Stage Card: Slides in from right (0.5s ease-out)
        slide_prog = ease_out_quad(min(1.0, item_t / 0.5))
        card_w = self.layout.stage_w - rail_w - 40
        card_h = self.layout.stage_h
        target_card_x = rail_x + rail_w + 40
        # Start offset 300px to the right
        card_x = target_card_x + int((1.0 - slide_prog) * 300)
        card_y = self.layout.stage_y

        is_top_rank = current_item["rank"] == 1
        card_outline = Colors.rgb_gold if is_top_rank else Colors.rgb_line

        # Main Card Panel
        draw.rectangle(
            [card_x, card_y, card_x + card_w, card_y + card_h],
            fill=Colors.rgb_surface_2,
            outline=card_outline,
            width=2 if is_top_rank else 1,
        )

        # Big Gold Rank Number
        font_big_rank = self.layout.get_font("display", 160)
        draw.text(
            (card_x + 50, card_y + 40),
            f"#{current_item['rank']}",
            fill=Colors.rgb_gold,
            font=font_big_rank,
        )

        # Entity Name
        font_entity = self.layout.get_font("bold", 54)
        draw.text(
            (card_x + 260, card_y + 70),
            current_item["entity"],
            fill=Colors.rgb_ivory,
            font=font_entity,
        )

        # Context line
        font_context = self.layout.get_font("regular", 28)
        ctx = current_item["context"].get("team") or current_item["context"].get("publisher") or ""
        if ctx:
            draw.text(
                (card_x + 260, card_y + 140), str(ctx), fill=Colors.rgb_muted, font=font_context
            )

        # Stat bar grows (0.8s ease-out)
        bar_prog = ease_out_quad(min(1.0, max(0.0, (item_t - 0.2) / 0.8)))
        bar_max_w = card_w - 100
        cur_bar_w = int((current_item["value"] / self.max_val) * bar_max_w * bar_prog)
        bar_y = card_y + 260

        draw.rectangle(
            [card_x + 50, bar_y, card_x + 50 + bar_max_w, bar_y + 60], fill=Colors.rgb_surface
        )
        draw.rectangle(
            [card_x + 50, bar_y, card_x + 50 + cur_bar_w, bar_y + 60],
            fill=Colors.rgb_gold,
            outline=Colors.rgb_gold_light,
        )

        # Value count
        font_val = self.layout.get_font("display", 48)
        val_str = f"{current_item['value']} {current_item['unit']}".strip()
        draw.text((card_x + 50, bar_y + 80), val_str, fill=Colors.rgb_gold_light, font=font_val)

        return frame
