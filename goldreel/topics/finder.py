"""Rule-based angle finder and candidate scorer."""

from dataclasses import dataclass
from typing import Literal

from goldreel.config.loader import TopicAngle, TopicsConfig, load_topics_config
from goldreel.facts.models import FactTable
from goldreel.state.store import compute_content_hash
from goldreel.topics.history import TopicHistory


@dataclass
class AngleCandidate:
    angle_id: str
    name: str
    lane: str
    format_type: Literal["landscape", "portrait"]
    score: float
    reason: str
    fact_table: FactTable


class AngleFinder:
    """Discovers suitable narrative angles for a FactTable, scores them, and deduplicates against history."""

    def __init__(
        self,
        topics_config: TopicsConfig | None = None,
        history: TopicHistory | None = None,
    ):
        self.config = topics_config or load_topics_config()
        self.history = history or TopicHistory()

    def find_angles(
        self,
        fact_table: FactTable,
        target_format: str | None = None,
        dedupe_threshold: float = 85.0,
    ) -> list[AngleCandidate]:
        """Evaluate fact table against angle rules, score, and filter duplicates."""
        candidates: list[AngleCandidate] = []
        fact_hash = compute_content_hash(fact_table.model_dump())
        entities = [r.entity for r in fact_table.records]

        # 1. Deduplication check against history
        is_dup, dup_id, sim = self.history.check_similarity(
            title=fact_table.title,
            entities=entities,
            facts_hash=fact_hash,
            threshold=dedupe_threshold,
        )
        if is_dup:
            # Fact table too similar to previous video
            return []

        data_count = len(fact_table.records)

        # 2. Match against configured angles
        for angle in self.config.angles:
            if angle.lane != fact_table.lane:
                continue

            # Minimum data point constraint
            if data_count < angle.min_data_points:
                continue

            # Maximum data point constraint
            if angle.max_data_points and data_count > angle.max_data_points:
                # We can still slice, but penalty applies if too large
                pass

            # Calculate score
            score = self._score_angle(angle, fact_table, target_format)

            fmt = angle.preferred_format
            if target_format and target_format in ("landscape", "portrait"):
                fmt = target_format

            candidates.append(
                AngleCandidate(
                    angle_id=angle.id,
                    name=angle.name,
                    lane=angle.lane,
                    format_type="landscape" if fmt == "landscape" else "portrait",
                    score=score,
                    reason=f"Matched {angle.name} with {data_count} data points (similarity {sim:.1f}%)",
                    fact_table=fact_table,
                )
            )

        # Sort by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    def _score_angle(
        self,
        angle: TopicAngle,
        fact_table: FactTable,
        target_format: str | None,
    ) -> float:
        """Score angle suitability."""
        base = angle.scoring_weight * 10.0
        n_points = len(fact_table.records)

        # Reward healthy data point count
        if 5 <= n_points <= 12:
            base += 3.0
        elif n_points > 12:
            base += 1.5

        # Format match bonus
        if target_format and target_format == angle.preferred_format:
            base += 2.0

        return round(base, 2)
