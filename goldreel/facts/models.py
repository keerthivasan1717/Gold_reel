"""Fact data models for GoldReel.

Enforces strict truth and provenance rules per docs/GEMINI.md Section 3:
- Numbers and dates come ONLY from structured sources, never an AI model.
- Every fact carries source, source_url, retrieved_at.
- Comic facts require two independent sources that agree.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class SourceAttribution(BaseModel):
    name: str = Field(..., description="Source name (e.g. 'cricsheet', 'wikidata')")
    source_url: str = Field(..., description="Direct URL or data dump URL")
    retrieved_at: str = Field(..., description="ISO 8601 timestamp of retrieval")
    attribution_text: str | None = Field(
        default=None, description="Attribution text if required by license"
    )


class FactRecord(BaseModel):
    rank: int | None = None
    entity: str = Field(..., description="Name of player, character, team, or title")
    metric: str = Field(..., description="Metric name (e.g. 'IPL Centuries', 'Debut Year')")
    value: int | float | str = Field(..., description="Verified value (number, date, or count)")
    unit: str = Field(
        default="", description="Unit of measurement (e.g. 'centuries', 'goals', 'year')"
    )
    context: dict[str, Any] = Field(
        default_factory=dict, description="Extra context like team, season, opponent"
    )


class FactTable(BaseModel):
    topic_id: str = Field(..., description="Topic identifier (e.g. 'ipl_most_centuries')")
    title: str = Field(..., description="Title of the fact table / ranking")
    lane: Literal["sports", "comics"] = Field(..., description="Production lane")
    metric_label: str = Field(
        ..., description="Exact ranking rule (e.g. 'By centuries scored in IPL, 2008 to 2024')"
    )
    sources: list[SourceAttribution] = Field(
        ..., min_length=1, description="Data sources for these facts"
    )
    records: list[FactRecord] = Field(..., min_length=1, description="List of verified facts")
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @model_validator(mode="after")
    def validate_facts_provenance(self) -> "FactTable":
        if not self.sources:
            raise ValueError(
                "Fact table must have at least one verified source with source_url and retrieved_at."
            )
        for s in self.sources:
            if not s.name or not s.source_url or not s.retrieved_at:
                raise ValueError("Every source must carry name, source_url, and retrieved_at.")
        return self


class ComicFact(BaseModel):
    topic_id: str
    entity: str = Field(..., description="Character or series name")
    publisher: str = Field(..., description="Publisher (e.g. 'Marvel Comics', 'DC Comics')")
    creators: list[str] = Field(default_factory=list)
    first_appearance_title: str
    publication_year: int
    cover_date: str
    sources: list[SourceAttribution] = Field(
        ..., min_length=2, description="Must have at least 2 independent sources"
    )
    agreement_verified: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_comic_sources_agreement(self) -> "ComicFact":
        if len(self.sources) < 2:
            raise ValueError("Comic facts require at least two independent sources.")
        # Ensure source names are independent
        names = {s.name.lower().strip() for s in self.sources}
        if len(names) < 2:
            raise ValueError(
                "Comic facts require two independent, distinct sources (got duplicates)."
            )
        if not self.agreement_verified:
            raise ValueError("Comic fact cannot be accepted without agreement_verified=True.")
        return self
