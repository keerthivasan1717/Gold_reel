"""Scroll compare template for two-row timeline comparisons in YouTube Shorts.

Strictly follows docs/DESIGN.md Section 5:
- Two horizontal rows scrolling at independent speeds.
- Row labels as fixed gold pills with solid backing.
- Cards are purely typographic (name, year, big number), NO character art.
- Centre indicator displays the fact for the card nearest the middle.
- Safe margins: 60 px top/sides, 120 px bottom platform UI exclusion zone.
"""

from typing import Any

from PIL import Image, ImageDraw

from goldreel.design.tokens import Colors
from goldreel.facts.models import FactTable
from goldreel.render.layouts.portrait import PortraitLayout
from goldreel.render.templates.base import BaseTemplate
from goldreel.render.timeline import Timeline
from goldreel.script.models import GeneratedScript


class ScrollCompareTemplate(BaseTemplate):
    """Two-row horizontal scroll compare template for portrait Shorts."""

    def __init__(self, layout: PortraitLayout | None = None, seed: int = 42):
        self.p_layout = layout or PortraitLayout()
        # Initialize base template with portrait layout
        super().__init__(layout=self.p_layout, seed=seed)
        self.fact_table: FactTable | None = None
        self.script: GeneratedScript | None = None
        self.timeline: Timeline | None = None
        self.row_a_items: list[dict[str, Any]] = []
        self.row_b_items: list[dict[str, Any]] = []

    def plan(self, fact_table: FactTable, script: GeneratedScript) -> Timeline:
        self.fact_table = fact_table
        self.script = script
        dur = script.estimated_duration_sec or 35.0
        self.timeline = Timeline(
            duration_sec=dur,
            fps=30,
            width=self.p_layout.width,
            height=self.p_layout.height,
        )

        # Split items into Row A and Row B
        self.row_a_items = []
        self.row_b_items = []

        for r in fact_table.records:
            ctx = r.context.get("publisher") or r.context.get("team") or ""
            item = {
                "entity": r.entity,
                "value": r.value,
                "unit": r.unit,
                "group": ctx,
                "context": r.context,
            }
            # If comics: split Marvel vs DC; else split alternate
            if "dc" in str(ctx).lower():
                self.row_b_items.append(item)
            elif "marvel" in str(ctx).lower():
                self.row_a_items.append(item)
            else:
                if len(self.row_a_items) <= len(self.row_b_items):
                    self.row_a_items.append(item)
                else:
                    self.row_b_items.append(item)

        if not self.row_a_items and self.row_b_items:
            self.row_a_items = self.row_b_items[: len(self.row_b_items) // 2]
            self.row_b_items = self.row_b_items[len(self.row_b_items) // 2 :]

        return self.timeline

    def draw(self, t: float) -> Image.Image:
        dur = self.timeline.duration_sec if self.timeline else 35.0
        frame = self.bg.render(t, total_duration=dur)

        if not self.fact_table:
            return frame

        draw = ImageDraw.Draw(frame)

        # Header (84px display title per DESIGN.md portrait rules)
        font_title = self.p_layout.get_font("display", 84)
        font_sub = self.p_layout.get_font("bold", 36)

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

        # Hairline
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

        # Setup Two Scroll Rows
        row1_y = 360
        row2_y = 740

        card_w = 260
        card_h = 220
        gap = 25

        # Speed 1 and Speed 2
        scroll_x1 = int(t * 80)
        scroll_x2 = int(t * 55)

        # Draw Row 1 (Series A)
        active_item_a = self._draw_scroll_row(
            frame=frame,
            draw=draw,
            items=self.row_a_items,
            row_y=row1_y,
            row_label="SERIES A",
            scroll_x=scroll_x1,
            card_w=card_w,
            card_h=card_h,
            gap=gap,
            is_gold_accent=True,
        )

        # Draw Row 2 (Series B)
        active_item_b = self._draw_scroll_row(
            frame=frame,
            draw=draw,
            items=self.row_b_items,
            row_y=row2_y,
            row_label="SERIES B",
            scroll_x=scroll_x2,
            card_w=card_w,
            card_h=card_h,
            gap=gap,
            is_gold_accent=False,
        )

        # Center Active Fact Focus Panel
        focus_y = 1120
        focus_h = 260
        draw.rectangle(
            [
                self.p_layout.stage_x,
                focus_y,
                self.p_layout.stage_x + self.p_layout.stage_w,
                focus_y + focus_h,
            ],
            fill=Colors.rgb_surface_2,
            outline=Colors.rgb_gold,
            width=2,
        )

        font_focus_title = self.p_layout.get_font("display", 36)
        font_focus_body = self.p_layout.get_font("bold", 42)
        font_focus_sub = self.p_layout.get_font("regular", 28)

        draw.text(
            (self.p_layout.stage_x + 30, focus_y + 25),
            "ACTIVE FOCUS TIMELINE",
            fill=Colors.rgb_gold,
            font=font_focus_title,
        )

        focus_item = active_item_a or active_item_b
        if focus_item:
            draw.text(
                (self.p_layout.stage_x + 30, focus_y + 80),
                f"{focus_item['entity']} ({focus_item['value']})",
                fill=Colors.rgb_ivory,
                font=font_focus_body,
            )
            ctx_text = str(
                focus_item.get("group") or focus_item["context"].get("first_appearance_title", "")
            )
            draw.text(
                (self.p_layout.stage_x + 30, focus_y + 145),
                f"Verified: {ctx_text}",
                fill=Colors.rgb_muted,
                font=font_focus_sub,
            )

        # Stated analytical insight panel (above safe 120px bottom UI)
        if self.script and self.script.insight:
            insight_y = 1440
            draw.rectangle(
                [
                    self.p_layout.stage_x,
                    insight_y,
                    self.p_layout.stage_x + self.p_layout.stage_w,
                    insight_y + 160,
                ],
                fill=Colors.rgb_surface,
                outline=Colors.rgb_line,
                width=1,
            )
            font_insight_hdr = self.p_layout.get_font("bold", 26)
            font_insight_body = self.p_layout.get_font("regular", 26)
            draw.text(
                (self.p_layout.stage_x + 25, insight_y + 18),
                "ANALYTICAL TAKEAWAY:",
                fill=Colors.rgb_gold_light,
                font=font_insight_hdr,
            )
            # Wrap insight text
            draw.text(
                (self.p_layout.stage_x + 25, insight_y + 58),
                self.script.insight[:95],
                fill=Colors.rgb_ivory,
                font=font_insight_body,
            )
            if len(self.script.insight) > 95:
                draw.text(
                    (self.p_layout.stage_x + 25, insight_y + 92),
                    self.script.insight[95:180],
                    fill=Colors.rgb_ivory,
                    font=font_insight_body,
                )

        # Footer Source Credit (Above 120px safe bottom line)
        src_name = (
            self.fact_table.sources[0].name.title() if self.fact_table.sources else "Open Data"
        )
        font_footer = self.p_layout.get_font("regular", 24)
        draw.text(
            (self.p_layout.margin_x, self.p_layout.footer_y),
            f"Source: {src_name} | GoldReel Shorts",
            fill=Colors.rgb_muted,
            font=font_footer,
        )

        return frame

    def _draw_scroll_row(
        self,
        frame: Image.Image,
        draw: ImageDraw.ImageDraw,
        items: list[dict[str, Any]],
        row_y: int,
        row_label: str,
        scroll_x: int,
        card_w: int,
        card_h: int,
        gap: int,
        is_gold_accent: bool,
    ) -> dict[str, Any] | None:
        """Render a single horizontally scrolling row and return the card nearest the screen center."""
        if not items:
            return None

        # Fixed label pill with solid backing
        pill_w = 160
        pill_h = 42
        pill_x = self.p_layout.margin_x
        pill_y = row_y - 20

        draw.rectangle(
            [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
            fill=Colors.rgb_surface_2,
            outline=Colors.rgb_gold if is_gold_accent else Colors.rgb_silver,
        )
        font_pill = self.p_layout.get_font("bold", 22)
        draw.text(
            (pill_x + 18, pill_y + 8),
            row_label,
            fill=Colors.rgb_gold if is_gold_accent else Colors.rgb_silver,
            font=font_pill,
        )

        stage_x = self.p_layout.stage_x
        stage_w = self.p_layout.stage_w
        card_top = row_y + 35

        # Create row canvas with RGBA transparency for clean clipping at safe margins
        row_canvas = Image.new("RGBA", (stage_w, card_h + 10), (0, 0, 0, 0))
        row_draw = ImageDraw.Draw(row_canvas)

        center_x = stage_w // 2
        nearest_item = None
        min_dist = float("inf")

        font_entity = self.p_layout.get_font("bold", 30)
        font_val = self.p_layout.get_font("display", 54)
        font_unit = self.p_layout.get_font("regular", 22)

        # Repeat items to create continuous scroll
        loop_w = len(items) * (card_w + gap)
        if loop_w == 0:
            return None

        effective_offset = scroll_x % loop_w

        # Draw enough cards to cover screen width inside safe margins
        for idx in range(-2, len(items) + 6):
            item = items[idx % len(items)]
            base_x = idx * (card_w + gap) - effective_offset

            if -card_w <= base_x <= stage_w:
                # Distance to center
                card_mid = base_x + card_w // 2
                dist = abs(card_mid - center_x)
                if dist < min_dist:
                    min_dist = dist
                    nearest_item = item

                is_centered = dist < card_w // 2
                card_fill = Colors.rgb_surface_2 if is_centered else Colors.rgb_surface
                card_outline = (
                    Colors.rgb_gold if (is_centered and is_gold_accent) else Colors.rgb_line
                )

                # Card panel
                row_draw.rectangle(
                    [base_x, 0, base_x + card_w, card_h],
                    fill=card_fill,
                    outline=card_outline,
                    width=2 if is_centered else 1,
                )

                # Big typographic number
                val_str = str(item["value"])
                val_color = Colors.rgb_gold if is_gold_accent else Colors.rgb_silver
                row_draw.text((base_x + 20, 20), val_str, fill=val_color, font=font_val)

                # Entity name
                row_draw.text(
                    (base_x + 20, 100),
                    item["entity"][:18],
                    fill=Colors.rgb_ivory,
                    font=font_entity,
                )

                # Context label
                unit_label = item.get("unit") or item.get("group") or ""
                row_draw.text(
                    (base_x + 20, 155),
                    str(unit_label)[:20],
                    fill=Colors.rgb_muted,
                    font=font_unit,
                )

        # Paste row canvas onto main frame clipped to safe margins
        frame.paste(row_canvas, (stage_x, card_top), row_canvas)

        # Center indicator hairline
        main_center_x = self.p_layout.width // 2
        draw.line(
            [main_center_x, row_y + 25, main_center_x, row_y + 35 + card_h + 10],
            fill=Colors.rgb_gold,
            width=2,
        )

        return nearest_item
