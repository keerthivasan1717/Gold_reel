"""Automated black-and-gold thumbnail generator.

Strictly follows docs/DESIGN.md & docs/GEMINI.md:
- 1280x720 landscape thumbnail or 1080x1920 portrait Shorts cover.
- Procedural geometric background with gold glow.
- Big bold typography (Bebas Neue + Liberation Sans).
- No copyrighted character artwork or third-party logos.
"""

from pathlib import Path

from PIL import ImageDraw, ImageFont

from goldreel.design.tokens import Colors
from goldreel.facts.models import FactTable
from goldreel.render.background import ProceduralBackground
from goldreel.script.models import GeneratedScript


class ThumbnailGenerator:
    """Generates high-contrast black-and-gold YouTube video thumbnails."""

    FONT_DISPLAY = "assets/fonts/BebasNeue-Regular.ttf"
    FONT_SANS_BOLD = "assets/fonts/LiberationSans-Bold.ttf"
    FONT_SANS_REG = "assets/fonts/LiberationSans-Regular.ttf"

    def _get_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont:
        p = Path(font_name)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
        return ImageFont.load_default()

    def generate(
        self,
        fact_table: FactTable,
        script: GeneratedScript,
        output_path: Path,
        format_type: str = "landscape",
    ) -> Path:
        """Render and save a thumbnail for the given fact table and script."""
        is_portrait = format_type == "portrait"
        width = 1080 if is_portrait else 1280
        height = 1920 if is_portrait else 720

        # Base procedural background
        bg = ProceduralBackground(width=width, height=height, seed=42)
        base_frame = bg.render(t=1.5, total_duration=10.0)
        draw = ImageDraw.Draw(base_frame)

        if not is_portrait:
            # === LANDSCAPE THUMBNAIL (1280x720) ===
            # Outer subtle gold boundary
            draw.rectangle([20, 20, 1260, 700], outline=Colors.rgb_line, width=2)
            draw.rectangle([24, 24, 1256, 696], outline=Colors.rgb_surface_2, width=1)

            # Header pill
            badge_x, badge_y = 60, 60
            badge_w, badge_h = 240, 44
            draw.rectangle(
                [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
                fill=Colors.rgb_surface_2,
                outline=Colors.rgb_gold,
                width=2,
            )
            font_badge = self._get_font(self.FONT_SANS_BOLD, 22)
            draw.text(
                (badge_x + 22, badge_y + 10),
                "DATA VISUALIZATION",
                fill=Colors.rgb_gold,
                font=font_badge,
            )

            # Giant Main Title
            font_title = self._get_font(self.FONT_DISPLAY, 92)
            title_text = fact_table.title.upper()
            if len(title_text) > 30:
                words = title_text.split()
                mid = len(words) // 2
                line1 = " ".join(words[:mid])
                line2 = " ".join(words[mid:])
                draw.text((60, 130), line1, fill=Colors.rgb_ivory, font=font_title)
                draw.text((60, 225), line2, fill=Colors.rgb_ivory, font=font_title)
                stat_box_y = 350
            else:
                draw.text((60, 150), title_text, fill=Colors.rgb_ivory, font=font_title)
                stat_box_y = 280

            # Central Hero Stat Box
            top_rec = fact_table.records[0] if fact_table.records else None
            if top_rec:
                box_x, box_y = 60, stat_box_y
                box_w, box_h = 1160, 260
                draw.rectangle(
                    [box_x, box_y, box_x + box_w, box_y + box_h],
                    fill=Colors.rgb_surface,
                    outline=Colors.rgb_gold_light,
                    width=2,
                )

                # Hero Number Callout
                font_big_num = self._get_font(self.FONT_DISPLAY, 140)
                font_hero_entity = self._get_font(self.FONT_SANS_BOLD, 48)
                font_hero_sub = self._get_font(self.FONT_SANS_REG, 28)

                num_str = f"#{top_rec.rank}  {top_rec.value}"
                draw.text(
                    (box_x + 40, box_y + 35), num_str, fill=Colors.rgb_gold, font=font_big_num
                )
                draw.text(
                    (box_x + 480, box_y + 55),
                    top_rec.entity,
                    fill=Colors.rgb_ivory,
                    font=font_hero_entity,
                )
                draw.text(
                    (box_x + 480, box_y + 125),
                    f"{fact_table.metric_label} ({top_rec.unit})",
                    fill=Colors.rgb_muted,
                    font=font_hero_sub,
                )

            # Footer provenance
            font_footer = self._get_font(self.FONT_SANS_REG, 20)
            src_name = fact_table.sources[0].name.upper() if fact_table.sources else "OPEN DATA"
            draw.text(
                (60, 660),
                f"VERIFIED PROVENANCE: {src_name} | GOLDREEL",
                fill=Colors.rgb_muted,
                font=font_footer,
            )

        else:
            # === PORTRAIT SHORTS COVER (1080x1920) ===
            draw.rectangle([30, 30, 1050, 1890], outline=Colors.rgb_line, width=2)

            # Badge
            badge_x, badge_y = 80, 100
            draw.rectangle(
                [badge_x, badge_y, badge_x + 220, badge_y + 48],
                fill=Colors.rgb_surface_2,
                outline=Colors.rgb_gold,
                width=2,
            )
            font_badge = self._get_font(self.FONT_SANS_BOLD, 22)
            draw.text(
                (badge_x + 20, badge_y + 12),
                "GOLDREEL SHORTS",
                fill=Colors.rgb_gold,
                font=font_badge,
            )

            # Title
            font_title = self._get_font(self.FONT_DISPLAY, 108)
            draw.text((80, 200), fact_table.title.upper(), fill=Colors.rgb_ivory, font=font_title)

            # Center Card
            top_rec = fact_table.records[0] if fact_table.records else None
            if top_rec:
                box_x, box_y = 80, 600
                box_w, box_h = 920, 500
                draw.rectangle(
                    [box_x, box_y, box_x + box_w, box_y + box_h],
                    fill=Colors.rgb_surface_2,
                    outline=Colors.rgb_gold,
                    width=3,
                )
                font_big = self._get_font(self.FONT_DISPLAY, 220)
                font_ent = self._get_font(self.FONT_SANS_BOLD, 54)
                draw.text(
                    (box_x + 50, box_y + 40),
                    f"#{top_rec.rank}",
                    fill=Colors.rgb_gold,
                    font=font_big,
                )
                draw.text(
                    (box_x + 50, box_y + 290), top_rec.entity, fill=Colors.rgb_ivory, font=font_ent
                )
                draw.text(
                    (box_x + 50, box_y + 370),
                    f"{top_rec.value} {top_rec.unit}",
                    fill=Colors.rgb_gold_light,
                    font=font_ent,
                )

            # Footer (well above bottom 120px)
            font_footer = self._get_font(self.FONT_SANS_REG, 24)
            draw.text((80, 1720), "OFFICIAL DATA RECORDS", fill=Colors.rgb_muted, font=font_footer)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        base_frame.save(output_path, "PNG")
        return output_path
