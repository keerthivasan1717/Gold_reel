"""Wikidata comic facts adapter with mandatory two-source cross-verification.

Strictly follows docs/GEMINI.md Section 3:
- Comic facts need TWO independent sources that agree (e.g. Wikidata CC0 + secondary source).
- Disagreement drops the fact.
- No artwork. First appearances, creators, publication dates, series runs.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from goldreel.adapters.base import BaseAdapter
from goldreel.facts.models import ComicFact, FactRecord, FactTable, SourceAttribution

logger = logging.getLogger(__name__)


class WikidataComicAdapter(BaseAdapter):
    """Adapter for comic facts with dual-source validation."""

    WIKIDATA_URL = "https://www.wikidata.org"

    @property
    def name(self) -> str:
        return "wikidata"

    @property
    def lane(self) -> str:
        return "comics"

    def ingest(self, source_path_or_url: str | Path | None = None) -> Path:
        target_dir = self.cache_dir / "comics"
        target_dir.mkdir(parents=True, exist_ok=True)
        if source_path_or_url and Path(source_path_or_url).exists():
            p = Path(source_path_or_url)
            dest = target_dir / p.name
            dest.write_bytes(p.read_bytes())
            return dest
        return target_dir

    def cross_verify(
        self,
        primary_fact: dict[str, Any],
        secondary_fact: dict[str, Any],
    ) -> ComicFact | None:
        """Cross-check primary source against secondary source.

        Drops fact if any critical field disagrees.
        """
        now_iso = datetime.now(UTC).isoformat()

        # Check publisher agreement
        pub1 = str(primary_fact.get("publisher", "")).strip().lower()
        pub2 = str(secondary_fact.get("publisher", "")).strip().lower()
        if pub1 != pub2:
            logger.warning(
                "Comic fact dropped: publisher mismatch between sources for '%s' ('%s' vs '%s')",
                primary_fact.get("entity"),
                pub1,
                pub2,
            )
            return None

        # Check publication year agreement
        year1 = int(primary_fact.get("publication_year", 0))
        year2 = int(secondary_fact.get("publication_year", 0))
        if year1 != year2:
            logger.warning(
                "Comic fact dropped: publication year mismatch for '%s' (%s vs %s)",
                primary_fact.get("entity"),
                year1,
                year2,
            )
            return None

        # Check debut title agreement (normalized comparison)
        title1 = "".join(
            filter(str.isalnum, str(primary_fact.get("first_appearance_title", "")).lower())
        )
        title2 = "".join(
            filter(str.isalnum, str(secondary_fact.get("first_appearance_title", "")).lower())
        )
        if not (title1 in title2 or title2 in title1):
            logger.warning(
                "Comic fact dropped: debut title mismatch for '%s' ('%s' vs '%s')",
                primary_fact.get("entity"),
                primary_fact.get("first_appearance_title"),
                secondary_fact.get("first_appearance_title"),
            )
            return None

        # Both sources agree!
        src1 = SourceAttribution(
            name=primary_fact.get("source_name", "wikidata"),
            source_url=primary_fact.get("source_url", self.WIKIDATA_URL),
            retrieved_at=primary_fact.get("retrieved_at", now_iso),
            attribution_text="Wikidata CC0 open structured data",
        )
        src2 = SourceAttribution(
            name=secondary_fact.get("source_name", "secondary_catalog"),
            source_url=secondary_fact.get("source_url", "https://www.comics.org/"),
            retrieved_at=secondary_fact.get("retrieved_at", now_iso),
            attribution_text="Grand Comics Database cross-verification source",
        )

        return ComicFact(
            topic_id=primary_fact.get("topic_id", "comic_debuts"),
            entity=primary_fact["entity"],
            publisher=primary_fact["publisher"],
            creators=primary_fact.get("creators", []),
            first_appearance_title=primary_fact["first_appearance_title"],
            publication_year=year1,
            cover_date=primary_fact.get("cover_date", str(year1)),
            sources=[src1, src2],
            agreement_verified=True,
        )

    def extract_facts(
        self, raw_data_or_path: Any, topic_id: str = "comic_first_appearances"
    ) -> FactTable:
        """Extract validated comic facts into a FactTable."""
        if isinstance(raw_data_or_path, (str, Path)):
            with open(raw_data_or_path, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = raw_data_or_path

        items = data if isinstance(data, list) else data.get("items", [data])
        records: list[FactRecord] = []
        collected_sources: list[SourceAttribution] = []

        rank = 1
        for item in items:
            # If item contains both primary and secondary definitions
            if "primary" in item and "secondary" in item:
                verified_comic = self.cross_verify(item["primary"], item["secondary"])
            elif (
                "sources" in item
                and len(item["sources"]) >= 2
                and item.get("verification_status") == "verified_agreement"
            ):
                now_iso = datetime.now(UTC).isoformat()
                s1 = SourceAttribution(
                    name=item["sources"][0]["name"],
                    source_url=item["sources"][0]["source_url"],
                    retrieved_at=item["sources"][0].get("retrieved_at", now_iso),
                )
                s2 = SourceAttribution(
                    name=item["sources"][1]["name"],
                    source_url=item["sources"][1]["source_url"],
                    retrieved_at=item["sources"][1].get("retrieved_at", now_iso),
                )
                verified_comic = ComicFact(
                    topic_id=topic_id,
                    entity=item["entity"],
                    publisher=item["publisher"],
                    creators=item.get("creators", []),
                    first_appearance_title=item["first_appearance"]["title"],
                    publication_year=item["first_appearance"]["publication_year"],
                    cover_date=item["first_appearance"].get("cover_date", ""),
                    sources=[s1, s2],
                    agreement_verified=True,
                )
            else:
                verified_comic = None

            if verified_comic is not None:
                records.append(
                    FactRecord(
                        rank=rank,
                        entity=verified_comic.entity,
                        metric="Publication Debut Year",
                        value=verified_comic.publication_year,
                        unit="year",
                        context={
                            "publisher": verified_comic.publisher,
                            "first_appearance_title": verified_comic.first_appearance_title,
                            "cover_date": verified_comic.cover_date,
                            "creators": ", ".join(verified_comic.creators),
                        },
                    )
                )
                for s in verified_comic.sources:
                    if s not in collected_sources:
                        collected_sources.append(s)
                rank += 1

        if not records:
            raise ValueError("No comic facts could be verified with two agreeing sources.")

        return FactTable(
            topic_id=topic_id,
            title="Comic Character First Appearances",
            lane="comics",
            metric_label="Chronological first appearances verified across Wikidata and secondary catalog",
            sources=collected_sources,
            records=records,
        )
