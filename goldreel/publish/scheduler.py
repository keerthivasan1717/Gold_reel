"""Upload scheduler and rate-limit enforcer.

Enforces docs/GEMINI.md Section 5:
- YouTube quota safety: 1 upload = 1,600 units out of 10,000 units/day.
- Caps daily uploads to max_uploads_per_day (default: 2).
- Caps weekly uploads to max_uploads_per_week (default: 7).
- Computes optimal future UTC release timestamps for 'scheduled' uploads (publishAt).
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field


class PublishRecord(BaseModel):
    """Log of a completed or scheduled upload."""

    job_id: str
    video_id: str | None = None
    scheduled_at: str | None = None
    published_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    mode: str = "scheduled"


class PublishHistory:
    """Persistent ledger of published videos in state/publish_history.json."""

    def __init__(self, history_path: Path | str = "state/publish_history.json"):
        self.history_path = Path(history_path).resolve()
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.records: list[PublishRecord] = []
        self._load()

    def _load(self) -> None:
        if not self.history_path.exists():
            return
        try:
            with open(self.history_path, encoding="utf-8") as f:
                data = json.load(f)
            self.records = [PublishRecord(**item) for item in data]
        except Exception:
            self.records = []

    def _save(self) -> None:
        data = [r.model_dump() for r in self.records]
        tmp = self.history_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(self.history_path)

    def record_upload(
        self,
        job_id: str,
        video_id: str | None,
        scheduled_at: str | None,
        mode: str,
    ) -> None:
        """Register a published/scheduled video upload."""
        rec = PublishRecord(
            job_id=job_id,
            video_id=video_id,
            scheduled_at=scheduled_at,
            mode=mode,
        )
        self.records.append(rec)
        self._save()

    def count_recent(self, hours: float) -> int:
        """Count uploads occurring within the last N hours."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=hours)
        count = 0
        for r in self.records:
            try:
                rec_dt = datetime.fromisoformat(r.published_at)
                if rec_dt >= cutoff:
                    count += 1
            except Exception:
                continue
        return count


class PublishScheduler:
    """Calculates scheduled release timestamps and validates quota safety limits."""

    def __init__(self, history: PublishHistory | None = None):
        self.history = history or PublishHistory()

    def can_publish(self, max_per_day: int = 2, max_per_week: int = 7) -> tuple[bool, str]:
        """Check if publishing quota limits allow an upload at this time."""
        recent_24h = self.history.count_recent(hours=24)
        if recent_24h >= max_per_day:
            return (
                False,
                f"Daily upload ceiling reached: {recent_24h}/{max_per_day} in last 24h",
            )

        recent_7d = self.history.count_recent(hours=24 * 7)
        if recent_7d >= max_per_week:
            return (
                False,
                f"Weekly upload ceiling reached: {recent_7d}/{max_per_week} in last 7 days",
            )

        return True, "Quota checks satisfied"

    def has_video_scheduled_for_date(self, target_publish_time: str) -> bool:
        """Check if any video in history is scheduled for or published on target date (YYYY-MM-DD)."""
        target_date = target_publish_time.split("T")[0]
        for r in self.history.records:
            if r.scheduled_at and r.scheduled_at.startswith(target_date):
                return True
        return False

    def compute_publish_time(
        self,
        format_type: str = "landscape",
        buffer_hours: float = 0.5,
    ) -> str:
        """Compute the next optimal scheduled release timestamp in UTC.

        Target release time: 13:00 UTC (18:30 IST / 6:30 PM IST) daily.
        YouTube requires publishAt to be in RFC 3339 format (e.g. 'YYYY-MM-DDTHH:MM:SSZ').
        """
        now = datetime.now(UTC)
        min_release = now + timedelta(hours=buffer_hours)

        # Target 13:00 UTC (18:30 IST / 6:30 PM IST) daily
        candidate = min_release.replace(hour=13, minute=0, second=0, microsecond=0)
        if candidate < min_release:
            candidate += timedelta(days=1)

        # Output format required by YouTube Data API v3 (RFC 3339 / ISO 8601 UTC)
        return candidate.strftime("%Y-%m-%dT%H:%M:%SZ")
