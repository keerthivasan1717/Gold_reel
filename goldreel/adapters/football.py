"""Open football data adapter.

Processes public football tables and top scorer data.
Attribution and provenance verified per docs/PLAN.md Section 3.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from goldreel.adapters.base import BaseAdapter
from goldreel.facts.models import FactRecord, FactTable, SourceAttribution


class FootballAdapter(BaseAdapter):
    """Adapter for open football standings and goalscoring statistics."""

    SOURCE_URL = "https://github.com/openfootball"
    ATTRIBUTION_TEXT = "Football data provided by openfootball, public domain / open dataset."

    @property
    def name(self) -> str:
        return "openfootball"

    @property
    def lane(self) -> str:
        return "sports"

    def ingest(self, source_path_or_url: str | Path | None = None) -> Path:
        target_dir = self.cache_dir / "football"
        target_dir.mkdir(parents=True, exist_ok=True)
        if source_path_or_url and Path(source_path_or_url).exists():
            p = Path(source_path_or_url)
            dest = target_dir / p.name
            dest.write_bytes(p.read_bytes())
            return dest
        return target_dir

    def extract_facts(
        self, raw_data_or_path: Any, topic_id: str = "premier_league_top_scorers"
    ) -> FactTable:
        now_iso = datetime.now(UTC).isoformat()
        records: list[FactRecord] = []

        if isinstance(raw_data_or_path, (str, Path)):
            with open(raw_data_or_path, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = raw_data_or_path

        scorers = data.get("scorers", data.get("records", []))
        season = data.get("season", "2023-2024")
        league = data.get("league", "Premier League")

        for rank, item in enumerate(scorers, start=1):
            name = item.get("name") or item.get("player")
            goals = item.get("goals") or item.get("value")
            team = item.get("team", "")
            records.append(
                FactRecord(
                    rank=rank,
                    entity=name,
                    metric=f"{league} Goals",
                    value=goals,
                    unit="goals",
                    context={"team": team, "season": season},
                )
            )

        source = SourceAttribution(
            name=self.name,
            source_url=data.get("source_url", self.SOURCE_URL),
            retrieved_at=now_iso,
            attribution_text=self.ATTRIBUTION_TEXT,
        )

        return FactTable(
            topic_id=topic_id,
            title=f"{league} Top Scorers ({season})",
            lane="sports",
            metric_label=f"Ranked by total goals scored in {league} ({season})",
            sources=[source],
            records=records,
        )
