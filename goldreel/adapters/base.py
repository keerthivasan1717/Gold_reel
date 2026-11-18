"""Base data adapter interface for GoldReel."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from goldreel.facts.models import FactTable


class BaseAdapter(ABC):
    """Abstract base class for all open data adapters."""

    def __init__(self, cache_dir: Path | str = "cache"):
        self.cache_dir = Path(cache_dir).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the adapter (e.g. 'cricsheet', 'wikidata')."""
        pass

    @property
    @abstractmethod
    def lane(self) -> str:
        """Lane: 'sports' or 'comics'."""
        pass

    @abstractmethod
    def ingest(self, source_path_or_url: str | Path | None = None) -> Path:
        """Fetch or locate raw data into cache/ with integrity verification."""
        pass

    @abstractmethod
    def extract_facts(self, raw_data_or_path: Any, topic_id: str) -> FactTable:
        """Parse raw dataset into a validated, typed FactTable."""
        pass
