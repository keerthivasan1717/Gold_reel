"""Automated credits and attribution text generator.

Strictly follows docs/DESIGN.md & docs/GEMINI.md:
- Generates required attribution for data sources (Cricsheet/Wikidata), music licenses, and Piper voice.
- Output formats: multiline description block and single-line video outro screen.
"""

from goldreel.audio.library import MusicTrack
from goldreel.facts.models import FactTable


class CreditsGenerator:
    """Builds required legal credits and attributions."""

    @staticmethod
    def generate_description_credits(
        fact_table: FactTable,
        music_track: MusicTrack | None = None,
        voice_name: str = "en_US-lessac-medium (Piper TTS)",
    ) -> str:
        """Generate description attribution block for YouTube metadata."""
        lines = [
            "--- LICENSES & ATTRIBUTION ---",
            "Data Sources:",
        ]
        for src in fact_table.sources:
            attr = f" - {src.attribution_text}" if src.attribution_text else ""
            lines.append(f"• {src.name.title()}: {src.source_url}{attr}")

        lines.append("\nMusic:")
        if music_track:
            if music_track.attribution_required and music_track.attribution_text:
                lines.append(f"• {music_track.attribution_text}")
            else:
                lines.append(
                    f'• "{music_track.title}" by {music_track.artist} ({music_track.licence}) - {music_track.url}'
                )
        else:
            lines.append("• Original sound design by GoldReel.")

        lines.append("\nVoice Narration:")
        lines.append(
            f"• Narration powered by local {voice_name} (licensed under Open Data / PDDL)."
        )
        lines.append(
            "• Visuals: GoldReel geometric design tokens and typography (OFL / Liberation)."
        )

        return "\n".join(lines)

    @staticmethod
    def generate_outro_credit(fact_table: FactTable, music_track: MusicTrack | None = None) -> str:
        """Generate single-line summary credit for video outro slide."""
        data_name = fact_table.sources[0].name.title() if fact_table.sources else "Open Data"
        music_name = music_track.title if music_track else "GoldReel Audio"
        return f"Data: {data_name} | Music: {music_name} | Voice: Piper TTS"
