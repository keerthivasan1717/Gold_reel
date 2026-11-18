"""Topic similarity and deduplication Quality Control (QC) gate."""

from goldreel.qc.models import QCCheckItem
from goldreel.topics.history import TopicHistory


class SimilarityQC:
    """Automated similarity gate enforcing maximum 85% overlap with previous videos."""

    def __init__(
        self,
        history: TopicHistory | None = None,
        threshold_percent: float = 85.0,
    ):
        self.history = history or TopicHistory()
        self.threshold_percent = threshold_percent

    def check(
        self,
        title: str,
        entities: list[str],
        facts_hash: str | None = None,
        exclude_job_id: str | None = None,
    ) -> tuple[list[QCCheckItem], float]:
        """Verify candidate topic against historical records."""
        checks: list[QCCheckItem] = []
        is_dup, dup_id, max_sim = self.history.check_similarity(
            title=title,
            entities=entities,
            facts_hash=facts_hash,
            threshold=self.threshold_percent,
            exclude_job_id=exclude_job_id,
        )

        passed = not is_dup
        if passed:
            msg = (
                f"Topic is unique. Highest historical similarity is {max_sim:.1f}% "
                f"(threshold: < {self.threshold_percent:.1f}%)"
            )
        else:
            msg = (
                f"Topic similarity of {max_sim:.1f}% against past topic '{dup_id}' "
                f"exceeds the maximum allowed {self.threshold_percent:.1f}% threshold"
            )

        checks.append(
            QCCheckItem(
                name="topic_similarity_threshold",
                category="similarity",
                passed=passed,
                severity="critical",
                message=msg,
                measured_value=round(max_sim, 2),
                target_value=f"< {self.threshold_percent:.1f}%",
            )
        )

        return checks, max_sim
