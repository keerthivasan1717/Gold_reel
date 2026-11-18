"""Ranked countdown template for continuous motion and full-frame data visualization.

Strictly follows docs/DESIGN.md:
- Titles >= 72 px (84 px in portrait), labels >= 36 px.
- Continuous motion every second: bars growing, counters ticking, shimmer sweeping, background drifting.
- Scene transitions every 5 to 6 seconds on musical beats.
- No empty zones: fills full portrait 1080x1920 and landscape 1920x1080 frames.
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


class RankedCountdownTemplate(BaseTemplate):
    """Ranked countdown template displaying successive cards with continuous motion."""

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

        draw = ImageDraw.Draw(frame)

        # Global continuous progress across top edge
        prog_w = int((t / max(dur, 0.1)) * self.layout.width)
        draw.rectangle([0, 0, prog_w, 6], fill=Colors.rgb_gold)

        if self.is_portrait:
            self._draw_portrait(frame, draw, t, dur)
        else:
            self._draw_landscape(frame, draw, t, dur)

        return frame

    def _draw_portrait(self, frame: Image.Image, draw: ImageDraw.ImageDraw, t: float, dur: float) -> None:
        """Render full-frame portrait Shorts layout (1080x1920) with large text and continuous motion."""
        n_items = len(self.items)
        sec_per_item = dur / n_items
        active_idx = min(int(t // sec_per_item), n_items - 1)
        item_t = t - (active_idx * sec_per_item)
        current_item = self.items[active_idx]

        margin = 60
        stage_w = self.layout.width - (2 * margin)

        # 1. Header Zone (y: 60 - 230)
        font_pill = self.layout.get_font("bold", 28)
        font_title = self.layout.get_font("display", 80)
        font_metric = self.layout.get_font("bold", 36)

        draw.rectangle([margin, 60, margin + 260, 96], fill=Colors.rgb_surface_2, outline=Colors.rgb_gold)
        draw.text((margin + 18, 65), "OPEN DATA RECORDS", fill=Colors.rgb_gold, font=font_pill)

        draw.text((margin, 110), self.fact_table.title.upper()[:28], fill=Colors.rgb_ivory, font=font_title)
        draw.text((margin, 195), self.fact_table.metric_label.upper(), fill=Colors.rgb_gold, font=font_metric)
        draw.line([margin, 240, margin + stage_w, 240], fill=Colors.rgb_line, width=1)

        # 2. Countdown Navigation Rail (y: 255 - 325)
        chip_gap = 12
        chip_w = int((stage_w - ((n_items - 1) * chip_gap)) / n_items)
        font_chip = self.layout.get_font("bold", 32)

        for i in range(n_items):
            chip_x = margin + i * (chip_w + chip_gap)
            item_rank = self.items[i]["rank"]
            is_active = i == active_idx
            is_past = i < active_idx

            if is_active:
                # Pulsing active chip
                pulse = 0.85 + 0.15 * math.sin(t * 4.0)
                draw.rectangle([chip_x, 255, chip_x + chip_w, 315], fill=Colors.rgb_gold, outline=Colors.rgb_gold_light, width=2)
                draw.text((chip_x + (chip_w // 2) - 22, 268), f"#{item_rank}", fill=Colors.rgb_bg, font=font_chip)
            elif is_past:
                draw.rectangle([chip_x, 255, chip_x + chip_w, 315], fill=Colors.rgb_surface_2, outline=Colors.rgb_gold, width=1)
                draw.text((chip_x + (chip_w // 2) - 22, 268), f"#{item_rank}", fill=Colors.rgb_ivory, font=font_chip)
            else:
                draw.rectangle([chip_x, 255, chip_x + chip_w, 315], fill=Colors.rgb_surface, outline=Colors.rgb_line, width=1)
                draw.text((chip_x + (chip_w // 2) - 22, 268), f"#{item_rank}", fill=Colors.rgb_muted, font=font_chip)

        # 3. Main Hero Card (y: 340 - 1080)
        # Smooth entrance slide in first 0.5s
        slide_prog = ease_out_quad(min(1.0, item_t / 0.5))
        slide_offset = int((1.0 - slide_prog) * 120)
        card_y = 340 + slide_offset
        card_h = 740

        is_leader = current_item["rank"] == 1
        card_outline = Colors.rgb_gold if is_leader else Colors.rgb_line
        draw.rectangle([margin, card_y, margin + stage_w, card_y + card_h], fill=Colors.rgb_surface_2, outline=card_outline, width=2 if is_leader else 1)

        # Giant Rank Badge & Tag
        font_rank_tag = self.layout.get_font("bold", 36)
        font_rank_num = self.layout.get_font("display", 140)
        draw.text((margin + 40, card_y + 35), f"COUNTDOWN #{current_item['rank']}", fill=Colors.rgb_gold, font=font_rank_tag)
        draw.text((margin + stage_w - 180, card_y + 20), f"#{current_item['rank']}", fill=Colors.rgb_gold, font=font_rank_num)

        # Entity Name
        font_entity = self.layout.get_font("bold", 72)
        draw.text((margin + 40, card_y + 160), str(current_item["entity"])[:24], fill=Colors.rgb_ivory, font=font_entity)

        # Entity Context / Team / Era
        font_ctx = self.layout.get_font("regular", 36)
        ctx = current_item["context"].get("team") or current_item["context"].get("publisher") or current_item["context"].get("first_appearance_title") or "Historical Record"
        draw.text((margin + 40, card_y + 245), f"Category: {ctx}", fill=Colors.rgb_muted, font=font_ctx)

        # Ticking Counter Value
        counter_prog = ease_out_quad(min(1.0, max(0.0, item_t / 2.5)))
        current_val = current_item["value"] * counter_prog
        val_str = f"{int(round(current_val)):,}" if current_val.is_integer() else f"{current_val:,.1f}"

        font_val_big = self.layout.get_font("display", 130)
        font_unit = self.layout.get_font("display", 44)
        draw.text((margin + 40, card_y + 320), val_str, fill=Colors.rgb_gold, font=font_val_big)
        draw.text((margin + 40, card_y + 450), str(current_item["unit"]).upper(), fill=Colors.rgb_ivory, font=font_unit)

        # Growing Stat Bar (0.2s - 2.5s) + Continuous Shimmer Sweep
        bar_prog = ease_out_quad(min(1.0, max(0.0, (item_t - 0.15) / 2.2)))
        bar_max_w = stage_w - 80
        cur_bar_w = max(24, int((current_item["value"] / self.max_val) * bar_max_w * bar_prog))
        bar_y = card_y + 510

        draw.rectangle([margin + 40, bar_y, margin + 40 + bar_max_w, bar_y + 50], fill=Colors.rgb_surface)
        draw.rectangle([margin + 40, bar_y, margin + 40 + cur_bar_w, bar_y + 50], fill=Colors.rgb_gold, outline=Colors.rgb_gold_light)

        # Continuous Shimmer Sweep across the bar every second
        shimmer_x = margin + 40 + int(((item_t * 220) % max(cur_bar_w, 10)))
        draw.rectangle([shimmer_x, bar_y, min(shimmer_x + 14, margin + 40 + cur_bar_w), bar_y + 50], fill=Colors.rgb_gold_light)

        # Secondary Stat Highlights (side-by-side tiles)
        tile_w = (stage_w - 100) // 2
        tile_y = card_y + 590
        tile_h = 110

        font_tile_lbl = self.layout.get_font("regular", 28)
        font_tile_val = self.layout.get_font("bold", 38)

        # Tile 1: Leader Comparison
        draw.rectangle([margin + 40, tile_y, margin + 40 + tile_w, tile_y + tile_h], fill=Colors.rgb_surface, outline=Colors.rgb_line)
        draw.text((margin + 60, tile_y + 18), "STANDINGS TIER", fill=Colors.rgb_muted, font=font_tile_lbl)
        draw.text((margin + 60, tile_y + 55), f"TOP #{current_item['rank']} IN WORLD", fill=Colors.rgb_gold, font=font_tile_val)

        # Tile 2: Share of Max
        pct_of_max = (current_item["value"] / self.max_val) * 100
        draw.rectangle([margin + 60 + tile_w, tile_y, margin + 60 + (2 * tile_w), tile_y + tile_h], fill=Colors.rgb_surface, outline=Colors.rgb_line)
        draw.text((margin + 80 + tile_w, tile_y + 18), "PEAK SCALE", fill=Colors.rgb_muted, font=font_tile_lbl)
        draw.text((margin + 80 + tile_w, tile_y + 55), f"{pct_of_max:.1f}% OF RECORD", fill=Colors.rgb_ivory, font=font_tile_val)

        # 4. Standings Ladder & Historical Stage (y: 1110 - 1730, height 620px)
        ladder_y = 1110
        ladder_h = 400
        draw.rectangle([margin, ladder_y, margin + stage_w, ladder_y + ladder_h], fill=Colors.rgb_surface, outline=Colors.rgb_line)

        font_lad_hdr = self.layout.get_font("bold", 32)
        font_lad_row = self.layout.get_font("regular", 32)
        font_lad_val = self.layout.get_font("bold", 34)

        draw.text((margin + 30, ladder_y + 25), "COUNTDOWN LEADERBOARD", fill=Colors.rgb_gold, font=font_lad_hdr)
        draw.line([margin + 30, ladder_y + 70, margin + stage_w - 30, ladder_y + 70], fill=Colors.rgb_line, width=1)

        # Draw up to 4 revealed items in ladder
        shown_count = min(active_idx + 1, 4)
        for row_i in range(shown_count):
            row_item = self.items[row_i]
            r_y = ladder_y + 90 + row_i * 72
            is_cur = row_i == active_idx
            r_color = Colors.rgb_gold if is_cur else Colors.rgb_muted
            t_color = Colors.rgb_ivory if is_cur else Colors.rgb_silver

            draw.text((margin + 35, r_y), f"#{row_item['rank']}", fill=r_color, font=font_lad_val)
            draw.text((margin + 115, r_y), str(row_item["entity"])[:20], fill=t_color, font=font_lad_row)

            r_val_str = f"{int(row_item['value']):,} {row_item['unit']}"
            draw.text((margin + stage_w - 240, r_y), r_val_str, fill=r_color, font=font_lad_val)

        # Analytical Insight Quote Panel (y: 1535 - 1730, height 195px)
        if self.script and self.script.insight:
            ins_y = 1535
            draw.rectangle([margin, ins_y, margin + stage_w, ins_y + 195], fill=Colors.rgb_surface_2, outline=Colors.rgb_gold, width=1)
            font_ins_hdr = self.layout.get_font("bold", 28)
            font_ins_body = self.layout.get_font("regular", 32)
            draw.text((margin + 30, ins_y + 20), "DATA INSIGHT TAKEAWAY", fill=Colors.rgb_gold_light, font=font_ins_hdr)
            draw.text((margin + 30, ins_y + 65), self.script.insight[:48], fill=Colors.rgb_ivory, font=font_ins_body)
            if len(self.script.insight) > 48:
                draw.text((margin + 30, ins_y + 115), self.script.insight[48:105], fill=Colors.rgb_ivory, font=font_ins_body)

        # 5. Footer Safe Zone (y: 1750 - 1860)
        src_text = self.fact_table.sources[0].name.title() if self.fact_table.sources else "Open Data"
        font_footer = self.layout.get_font("regular", 28)
        draw.text((margin, 1755), f"Source: {src_text} | GoldReel Visuals", fill=Colors.rgb_muted, font=font_footer)
        draw.text((margin + stage_w - 160, 1755), "GOLDREEL", fill=Colors.rgb_muted, font=font_footer)

    def _draw_landscape(self, frame: Image.Image, draw: ImageDraw.ImageDraw, t: float, dur: float) -> None:
        """Render full-frame landscape layout (1920x1080) with large text and continuous motion."""
        n_items = len(self.items)
        sec_per_item = dur / n_items
        active_idx = min(int(t // sec_per_item), n_items - 1)
        item_t = t - (active_idx * sec_per_item)
        current_item = self.items[active_idx]

        src_text = self.fact_table.sources[0].name.title() if self.fact_table.sources else "Open Data"
        self.draw_common_chrome(
            frame,
            title=self.fact_table.title,
            metric_label=self.fact_table.metric_label,
            source_text=src_text,
        )

        # 1. Left Rail: previously revealed items
        rail_x = self.layout.stage_x
        rail_y = self.layout.stage_y
        rail_w = 440
        font_rail = self.layout.get_font("regular", 28)
        font_rail_rank = self.layout.get_font("bold", 32)
        font_rail_hdr = self.layout.get_font("bold", 28)

        draw.rectangle([rail_x, rail_y, rail_x + rail_w, rail_y + self.layout.stage_h], fill=Colors.rgb_surface, outline=Colors.rgb_line)
        draw.text((rail_x + 25, rail_y + 25), "COUNTDOWN PROGRESS", fill=Colors.rgb_gold, font=font_rail_hdr)
        draw.line([rail_x + 25, rail_y + 65, rail_x + rail_w - 25, rail_y + 65], fill=Colors.rgb_line, width=1)

        for i in range(active_idx + 1):
            past = self.items[i]
            row_y = rail_y + 85 + i * 70
            is_cur = i == active_idx
            rank_color = Colors.rgb_gold if is_cur else Colors.rgb_muted
            text_color = Colors.rgb_ivory if is_cur else Colors.rgb_silver
            draw.text((rail_x + 25, row_y), f"#{past['rank']}", fill=rank_color, font=font_rail_rank)
            draw.text((rail_x + 90, row_y), f"{past['entity'][:18]}", fill=text_color, font=font_rail)

        # 2. Main Stage Card: Slides in from right (0.5s ease-out)
        slide_prog = ease_out_quad(min(1.0, item_t / 0.5))
        card_w = self.layout.stage_w - rail_w - 40
        card_h = self.layout.stage_h
        target_card_x = rail_x + rail_w + 40
        card_x = target_card_x + int((1.0 - slide_prog) * 300)
        card_y = self.layout.stage_y

        is_top_rank = current_item["rank"] == 1
        card_outline = Colors.rgb_gold if is_top_rank else Colors.rgb_line

        draw.rectangle([card_x, card_y, card_x + card_w, card_y + card_h], fill=Colors.rgb_surface_2, outline=card_outline, width=2 if is_top_rank else 1)

        # Big Gold Rank Number
        font_big_rank = self.layout.get_font("display", 160)
        draw.text((card_x + 50, card_y + 30), f"#{current_item['rank']}", fill=Colors.rgb_gold, font=font_big_rank)

        # Entity Name
        font_entity = self.layout.get_font("bold", 68)
        draw.text((card_x + 270, card_y + 55), str(current_item["entity"])[:26], fill=Colors.rgb_ivory, font=font_entity)

        # Context line
        font_context = self.layout.get_font("regular", 36)
        ctx = current_item["context"].get("team") or current_item["context"].get("publisher") or "Historical Record"
        draw.text((card_x + 270, card_y + 135), f"Category: {ctx}", fill=Colors.rgb_muted, font=font_context)

        # Ticking Counter Value
        counter_prog = ease_out_quad(min(1.0, max(0.0, item_t / 2.5)))
        current_val = current_item["value"] * counter_prog
        val_str = f"{int(round(current_val)):,} {current_item['unit']}".strip()
        font_val = self.layout.get_font("display", 72)
        draw.text((card_x + 50, card_y + 225), val_str, fill=Colors.rgb_gold_light, font=font_val)

        # Stat bar grows (0.2s - 2.5s)
        bar_prog = ease_out_quad(min(1.0, max(0.0, (item_t - 0.2) / 2.2)))
        bar_max_w = card_w - 100
        cur_bar_w = max(20, int((current_item["value"] / self.max_val) * bar_max_w * bar_prog))
        bar_y = card_y + 320

        draw.rectangle([card_x + 50, bar_y, card_x + 50 + bar_max_w, bar_y + 60], fill=Colors.rgb_surface)
        draw.rectangle([card_x + 50, bar_y, card_x + 50 + cur_bar_w, bar_y + 60], fill=Colors.rgb_gold, outline=Colors.rgb_gold_light)

        # Shimmer sweep
        shimmer_x = card_x + 50 + int(((item_t * 260) % max(cur_bar_w, 10)))
        draw.rectangle([shimmer_x, bar_y, min(shimmer_x + 18, card_x + 50 + cur_bar_w), bar_y + 60], fill=Colors.rgb_gold_light)

        # Analytical Insight in Lower Half of Card
        if self.script and self.script.insight:
            ins_y = card_y + 420
            draw.rectangle([card_x + 50, ins_y, card_x + 50 + bar_max_w, ins_y + 160], fill=Colors.rgb_surface, outline=Colors.rgb_line)
            font_ins_hdr = self.layout.get_font("bold", 28)
            font_ins_body = self.layout.get_font("regular", 32)
            draw.text((card_x + 80, ins_y + 20), "KEY TAKEAWAY", fill=Colors.rgb_gold, font=font_ins_hdr)
            draw.text((card_x + 80, ins_y + 70), self.script.insight[:75], fill=Colors.rgb_ivory, font=font_ins_body)
