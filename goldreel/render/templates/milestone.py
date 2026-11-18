"""Milestone / 'On this day' template for high-impact YouTube Shorts.

Strictly follows docs/DESIGN.md Section 5:
- One large gold number.
- Short line of context.
- Gold progress line.
- Safe margins: 60 px top/sides, 120 px bottom platform UI exclusion zone.
"""

from typing import Any

from PIL import Image, ImageDraw

from goldreel.design.tokens import Colors
from goldreel.facts.models import FactTable
from goldreel.render.easing import ease_out_quad
from goldreel.render.layouts.portrait import PortraitLayout
from goldreel.render.templates.base import BaseTemplate
from goldreel.render.timeline import Timeline
from goldreel.script.models import GeneratedScript


class MilestoneTemplate(BaseTemplate):
    """Single milestone / record focus template for portrait Shorts."""

    def __init__(self, layout: PortraitLayout | None = None, seed: int = 42):
        self.p_layout = layout or PortraitLayout()
        super().__init__(layout=self.p_layout, seed=seed)
        self.fact_table: FactTable | None = None
        self.script: GeneratedScript | None = None
        self.timeline: Timeline | None = None
        self.leader_record: dict[str, Any] = {}

    def plan(self, fact_table: FactTable, script: GeneratedScript) -> Timeline:
        self.fact_table = fact_table
        self.script = script
        dur = script.estimated_duration_sec or 30.0
        self.timeline = Timeline(
            duration_sec=dur,
            fps=30,
            width=self.p_layout.width,
            height=self.p_layout.height,
        )

        if fact_table.records:
            r = fact_table.records[0]
            self.leader_record = {
                "entity": r.entity,
                "value": r.value,
                "unit": r.unit,
                "context": r.context,
            }
        else:
            self.leader_record = {
                "entity": "Milestone Record",
                "value": "100",
                "unit": "",
                "context": {},
            }

        return self.timeline

    def draw(self, t: float) -> Image.Image:
        dur = self.timeline.duration_sec if self.timeline else 30.0
        frame = self.bg.render(t, total_duration=dur)

        if not self.fact_table:
            return frame

        draw = ImageDraw.Draw(frame)

        # Header Title & Metric
        font_title = self.p_layout.get_font("display", 84)
        font_sub = self.p_layout.get_font("regular", 28)

        draw.text(
            (self.p_layout.header_x, self.p_layout.header_y),
            self.fact_table.title.upper(),
            fill=Colors.rgb_ivory,
            font=font_title,
        )
        draw.text(
            (self.p_layout.header_x, self.p_layout.header_y + 95),
            self.fact_table.metric_label,
            fill=Colors.rgb_gold,
            font=font_sub,
        )

        draw.line(
            [
                self.p_layout.header_x,
                self.p_layout.header_y + 140,
                self.p_layout.header_x + self.p_layout.header_w,
                self.p_layout.header_y + 140,
            ],
            fill=Colors.rgb_line,
            width=1,
        )

        # Hero Milestone Card
        card_x = self.p_layout.stage_x
        card_y = 380
        card_w = self.p_layout.stage_w
        card_h = 720

        draw.rectangle(
            [card_x, card_y, card_x + card_w, card_y + card_h],
            fill=Colors.rgb_surface_2,
            outline=Colors.rgb_gold_light,
            width=2,
        )

        # Badge pill
        pill_w = 260
        pill_h = 48
        draw.rectangle(
            [card_x + 50, card_y + 45, card_x + 50 + pill_w, card_y + 45 + pill_h],
            fill=Colors.rgb_gold,
        )
        font_pill = self.p_layout.get_font("bold", 24)
        draw.text(
            (card_x + 65, card_y + 55), "ALL-TIME MILESTONE", fill=Colors.rgb_bg, font=font_pill
        )

        # Giant Gold Record Number (Animated growth 0.8s)
        grow_prog = ease_out_quad(min(1.0, t / 0.8))
        font_giant = self.p_layout.get_font("display", 240)
        num_str = str(self.leader_record.get("value", ""))
        draw.text((card_x + 50, card_y + 120), num_str, fill=Colors.rgb_gold, font=font_giant)

        # Unit label
        unit_str = str(self.leader_record.get("unit", "")).upper()
        if unit_str:
            font_unit = self.p_layout.get_font("display", 48)
            draw.text(
                (card_x + 50, card_y + 360), unit_str, fill=Colors.rgb_gold_light, font=font_unit
            )

        # Gold Dynamic Progress Line
        line_max_w = card_w - 100
        cur_line_w = int(line_max_w * grow_prog)
        line_y = card_y + 440
        draw.rectangle(
            [card_x + 50, line_y, card_x + 50 + cur_line_w, line_y + 8], fill=Colors.rgb_gold
        )

        # Entity Name
        font_entity = self.p_layout.get_font("bold", 64)
        draw.text(
            (card_x + 50, card_y + 490),
            str(self.leader_record.get("entity", "")),
            fill=Colors.rgb_ivory,
            font=font_entity,
        )

        # Context line
        font_ctx = self.p_layout.get_font("regular", 32)
        ctx_val = (
            self.leader_record.get("context", {}).get("team")
            or self.leader_record.get("context", {}).get("publisher")
            or self.leader_record.get("context", {}).get("first_appearance_title")
            or ""
        )
        if ctx_val:
            draw.text(
                (card_x + 50, card_y + 590),
                f"Record: {ctx_val}",
                fill=Colors.rgb_muted,
                font=font_ctx,
            )

        # Analytical Insight Panel (Above 120px safe bottom line)
        if self.script and self.script.insight:
            insight_y = 1180
            draw.rectangle(
                [card_x, insight_y, card_x + card_w, insight_y + 240],
                fill=Colors.rgb_surface,
                outline=Colors.rgb_line,
                width=1,
            )
            font_ins_hdr = self.p_layout.get_font("bold", 28)
            font_ins_body = self.p_layout.get_font("regular", 28)
            draw.text(
                (card_x + 40, insight_y + 30),
                "DATA INSIGHT:",
                fill=Colors.rgb_gold,
                font=font_ins_hdr,
            )
            draw.text(
                (card_x + 40, insight_y + 80),
                self.script.insight[:85],
                fill=Colors.rgb_ivory,
                font=font_ins_body,
            )
            if len(self.script.insight) > 85:
                draw.text(
                    (card_x + 40, insight_y + 130),
                    self.script.insight[85:175],
                    fill=Colors.rgb_ivory,
                    font=font_ins_body,
                )

        # Safe Margin & Platform UI Clearance Footer
        src_name = (
            self.fact_table.sources[0].name.title() if self.fact_table.sources else "Open Data"
        )
        font_footer = self.p_layout.get_font("regular", 24)
        draw.text(
            (self.p_layout.margin_x, self.p_layout.footer_y),
            f"Source: {src_name} | Verified GoldReel Record",
            fill=Colors.rgb_muted,
            font=font_footer,
        )

        return frame
