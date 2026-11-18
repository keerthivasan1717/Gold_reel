"""Music library and license compliance tracker.

Strictly follows docs/GEMINI.md Section 4:
"Music only from assets/music/licenses.csv (title, artist, licence, URL, attribution required).
Never download clips or music at runtime."
"""

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MusicTrack:
    title: str
    artist: str
    licence: str
    url: str
    attribution_required: bool
    attribution_text: str
    filepath: Path


class MusicLibrary:
    """Manages licensed music assets."""

    def __init__(self, licenses_csv: Path | str = "assets/music/licenses.csv"):
        self.licenses_csv = Path(licenses_csv).resolve()
        self.tracks: list[MusicTrack] = []
        self._load()

    def _load(self) -> None:
        if not self.licenses_csv.exists():
            return
        with open(self.licenses_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                track_path = Path(row.get("filepath", "")).resolve()
                self.tracks.append(
                    MusicTrack(
                        title=row.get("title", "Unknown"),
                        artist=row.get("artist", "Unknown"),
                        licence=row.get("licence", "CC0"),
                        url=row.get("url", ""),
                        attribution_required=str(row.get("attribution_required", "false")).lower()
                        in ("true", "1"),
                        attribution_text=row.get("attribution_text", ""),
                        filepath=track_path,
                    )
                )

    def select_track(self, lane: str = "sports") -> MusicTrack:
        """Select appropriate background music track for the lane."""
        if not self.tracks:
            raise RuntimeError("No licensed music tracks found in assets/music/licenses.csv")
        # Return first track that exists on disk, or fallback to first entry
        for t in self.tracks:
            if t.filepath.exists():
                return t
        return self.tracks[0]
