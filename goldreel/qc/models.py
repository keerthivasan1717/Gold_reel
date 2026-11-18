"""Data models for automated Quality Control (QC) checks and reports."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

QCCheckCategory = Literal["audio", "frame", "metadata", "similarity", "facts", "duration"]
QCSeverity = Literal["critical", "warning", "info"]


class QCCheckItem(BaseModel):
    """Result of an individual automated quality gate check."""

    name: str = Field(..., description="Unique check identifier")
    category: QCCheckCategory = Field(..., description="Check domain")
    passed: bool = Field(..., description="Whether the check met the threshold")
    severity: QCSeverity = Field(default="critical", description="Failure severity")
    message: str = Field(..., description="Human-readable assessment or error description")
    measured_value: Any | None = Field(default=None, description="Actual measured value")
    target_value: Any | None = Field(default=None, description="Expected value or range")


class FrameAudit(BaseModel):
    """Inspection record for a single sampled video frame."""

    timestamp_sec: float
    mean_luminance: float
    stddev_luminance: float
    passed: bool
    notes: str
    saved_path: str | None = None


class QCReport(BaseModel):
    """Comprehensive Quality Control evaluation report for a job."""

    job_id: str
    passed: bool
    checks: list[QCCheckItem] = Field(default_factory=list)
    summary: str = ""
    duration_sec: float | None = None
    loudness_lufs: float | None = None
    true_peak_dbfs: float | None = None
    similarity_score: float | None = None
    frames_audited: list[FrameAudit] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def failed_critical_checks(self) -> list[QCCheckItem]:
        """Return all failed checks marked as critical."""
        return [c for c in self.checks if not c.passed and c.severity == "critical"]

    @property
    def warnings(self) -> list[QCCheckItem]:
        """Return all non-passing checks marked as warning."""
        return [c for c in self.checks if not c.passed and c.severity == "warning"]
