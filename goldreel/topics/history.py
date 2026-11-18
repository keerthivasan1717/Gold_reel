"""Topic history and similarity deduplication.

Enforces docs/GEMINI.md Section 4:
"Reject a video that is more than 85% similar to a previous one by title, fact set, or script."
"""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class TopicRecord:
    job_id: str
    topic_id: str
    title: str
    lane: str
    angle_id: str
    entities: list[str]
    facts_hash: str
    created_at: str


def tokenize_text(text: str) -> set[str]:
    """Tokenize string into normalized word set."""
    words = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())
    return set(words)


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity index between two sets (0.0 to 1.0)."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def calculate_topic_similarity(
    title_a: str,
    entities_a: list[str],
    title_b: str,
    entities_b: list[str],
) -> float:
    """Calculate combined similarity percentage between two topics (0.0 to 100.0)."""
    title_sim = jaccard_similarity(tokenize_text(title_a), tokenize_text(title_b))
    ent_set_a = {e.lower().strip() for e in entities_a}
    ent_set_b = {e.lower().strip() for e in entities_b}
    ent_sim = jaccard_similarity(ent_set_a, ent_set_b)

    # Weighted: 50% title overlap, 50% entity set overlap
    combined = (0.5 * title_sim + 0.5 * ent_sim) * 100.0
    return combined


class TopicHistory:
    """Stores history of produced topics and performs deduplication checks."""

    def __init__(self, history_file: Path | str = "state/topic_history.json"):
        self.history_file = Path(history_file).resolve()
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.records: list[TopicRecord] = []
        self._load()

    def _load(self) -> None:
        if not self.history_file.exists():
            return
        try:
            with open(self.history_file, encoding="utf-8") as f:
                data = json.load(f)
            self.records = [TopicRecord(**item) for item in data]
        except Exception:
            self.records = []

    def _save(self) -> None:
        data = [r.__dict__ for r in self.records]
        tmp = self.history_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(self.history_file)

    def check_similarity(
        self,
        title: str,
        entities: list[str],
        facts_hash: str | None = None,
        threshold: float = 85.0,
        exclude_job_id: str | None = None,
    ) -> tuple[bool, str | None, float]:
        """Check if candidate topic is too similar to any previous video.

        Returns (is_duplicate, duplicate_topic_id, max_similarity_percentage).
        """
        max_sim = 0.0
        most_similar_topic: str | None = None

        for rec in self.records:
            if exclude_job_id and rec.job_id == exclude_job_id:
                continue

            # Exact facts hash match is 100% duplicate
            if facts_hash and rec.facts_hash == facts_hash:
                return True, rec.topic_id, 100.0

            sim = calculate_topic_similarity(title, entities, rec.title, rec.entities)
            if sim > max_sim:
                max_sim = sim
                most_similar_topic = rec.topic_id

            if sim >= threshold:
                return True, rec.topic_id, sim

        return False, most_similar_topic, max_sim

    def record_topic(
        self,
        job_id: str,
        topic_id: str,
        title: str,
        lane: str,
        angle_id: str,
        entities: list[str],
        facts_hash: str,
    ) -> None:
        """Register a newly planned or produced topic into history."""
        rec = TopicRecord(
            job_id=job_id,
            topic_id=topic_id,
            title=title,
            lane=lane,
            angle_id=angle_id,
            entities=entities,
            facts_hash=facts_hash,
            created_at=datetime.now(UTC).isoformat(),
        )
        self.records.append(rec)
        self._save()
