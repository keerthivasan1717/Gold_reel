"""Fact repository to store and load structured fact tables."""

import json
from pathlib import Path

from goldreel.facts.models import FactTable


class FactStore:
    """Manages saving and loading of verified FactTable objects."""

    def __init__(self, base_dir: Path | str = "cache/facts"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, fact_table: FactTable) -> Path:
        """Save a FactTable to disk as JSON."""
        file_path = self.base_dir / f"{fact_table.topic_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fact_table.model_dump_json(indent=2))
        return file_path

    def load(self, topic_id: str) -> FactTable:
        """Load a FactTable from disk by topic_id."""
        file_path = self.base_dir / f"{topic_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Fact table not found for topic: {topic_id}")
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        return FactTable.model_validate(data)

    def list_topics(self) -> list[str]:
        """List all available topic IDs in store."""
        return [p.stem for p in self.base_dir.glob("*.json")]
