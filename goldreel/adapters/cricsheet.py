"""Cricsheet open cricket data adapter.

Processes open ball-by-ball and match dataset from cricsheet.org.
License: CC-BY 4.0 (attribution required in video and description).
"""

import json
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from goldreel.adapters.base import BaseAdapter
from goldreel.facts.models import FactRecord, FactTable, SourceAttribution


class CricsheetAdapter(BaseAdapter):
    """Adapter for Cricsheet match datasets."""

    CRICSHEET_URL = "https://cricsheet.org/matches/"
    ATTRIBUTION_TEXT = "Data provided by Cricsheet (cricsheet.org), licensed under CC-BY 4.0."

    @property
    def name(self) -> str:
        return "cricsheet"

    @property
    def lane(self) -> str:
        return "sports"

    def ingest(self, source_path_or_url: str | Path | None = None) -> Path:
        """Cache match files or read existing cache."""
        target_dir = self.cache_dir / "cricsheet"
        target_dir.mkdir(parents=True, exist_ok=True)
        if source_path_or_url:
            p = Path(source_path_or_url)
            if p.suffix == ".zip":
                with zipfile.ZipFile(p, "r") as z:
                    z.extractall(target_dir)
            elif p.suffix == ".json":
                target_file = target_dir / p.name
                target_file.write_bytes(p.read_bytes())
                return target_file
        return target_dir

    def parse_match_deliveries(self, match_data: dict[str, Any]) -> dict[str, int]:
        """Calculate runs scored by each batter in a single match."""
        batter_runs: dict[str, int] = defaultdict(int)
        innings = match_data.get("innings", [])
        for inn in innings:
            for over in inn.get("overs", []):
                for delivery in over.get("deliveries", []):
                    batter = delivery.get("batter")
                    runs = delivery.get("runs", {}).get("batter", 0)
                    if batter:
                        batter_runs[batter] += runs
        return dict(batter_runs)

    def aggregate_centuries_from_matches(
        self, matches: list[dict[str, Any]]
    ) -> list[tuple[str, int]]:
        """Calculate total centuries (scores >= 100) per batter across matches."""
        centuries_count: dict[str, int] = defaultdict(int)
        for m in matches:
            match_scores = self.parse_match_deliveries(m)
            for batter, score in match_scores.items():
                if score >= 100:
                    centuries_count[batter] += 1

        sorted_players = sorted(centuries_count.items(), key=lambda x: x[1], reverse=True)
        return sorted_players

    def extract_facts(
        self, raw_data_or_path: Any, topic_id: str = "ipl_most_centuries"
    ) -> FactTable:
        """Extract verified FactTable from match data or pre-computed records."""
        if topic_id == "cricsheet_odi_centuries_progression":
            from goldreel.facts.series import create_sports_time_series
            return create_sports_time_series()

        now_iso = datetime.now(UTC).isoformat()
        records: list[FactRecord] = []
        time_steps: list[str] = []
        values_by_step: dict[str, dict[str, float]] = {}
        entity_groups: dict[str, str] = {}
        title = "Most Centuries in IPL History"
        subtitle = "Progression of Top Batsmen (2008 - 2024)"
        metric_label = "By centuries scored in IPL, 2008 to 2024"

        if isinstance(raw_data_or_path, list) and all(
            isinstance(m, dict) and "innings" in m for m in raw_data_or_path
        ):
            leaderboard = self.aggregate_centuries_from_matches(raw_data_or_path)
            for rank, (player, count) in enumerate(leaderboard[:10], start=1):
                records.append(
                    FactRecord(
                        rank=rank,
                        entity=player,
                        metric="IPL Centuries",
                        value=count,
                        unit="centuries",
                    )
                )
        elif isinstance(raw_data_or_path, (dict, list)):
            # Structured ranking feed
            feed = raw_data_or_path if isinstance(raw_data_or_path, dict) else raw_data_or_path[0]
            if feed.get("title"):
                title = feed["title"]
            if feed.get("subtitle"):
                subtitle = feed["subtitle"]
            if feed.get("metric"):
                metric_label = feed["metric"]

            time_steps = feed.get("time_steps", [])
            values_by_step = feed.get("values_by_step", {})
            entity_groups = feed.get("entity_groups", {})

            raw_records = feed.get("records", [])
            for r in raw_records:
                entity_name = r.get("entity") or r.get("name")
                records.append(
                    FactRecord(
                        rank=r.get("rank"),
                        entity=entity_name,
                        metric=feed.get("metric", "IPL Centuries"),
                        value=r["value"],
                        unit=r.get("unit", "centuries"),
                        context={"team": r.get("team", "") or r.get("context", {}).get("team", "")},
                    )
                )
        elif isinstance(raw_data_or_path, (str, Path)):
            path = Path(raw_data_or_path)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return self.extract_facts(data, topic_id=topic_id)
        else:
            raise ValueError(
                f"Unsupported data format for CricsheetAdapter: {type(raw_data_or_path)}"
            )

        source = SourceAttribution(
            name=self.name,
            source_url=self.CRICSHEET_URL,
            retrieved_at=now_iso,
            attribution_text=self.ATTRIBUTION_TEXT,
        )

        return FactTable(
            topic_id=topic_id,
            title=title,
            subtitle=subtitle,
            lane="sports",
            metric_label=metric_label,
            sources=[source],
            records=records,
            time_steps=time_steps,
            values_by_step=values_by_step,
            entity_groups=entity_groups,
        )
