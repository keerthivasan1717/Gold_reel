"""Data models for video publishing, metadata packaging, and YouTube API results."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

PublishMode = Literal["scheduled", "private", "public", "fallback_package", "dry_run"]


class PublishMetadata(BaseModel):
    """Metadata package prepared for YouTube Data API v3 upload."""

    title: str = Field(..., max_length=100, description="Video title")
    description: str = Field(
        ..., max_length=5000, description="Video description with attributions"
    )
    tags: list[str] = Field(default_factory=list, description="Search tags")
    category_id: str = Field(
        default="28", description="YouTube category ID (28=Sci/Tech, 17=Sports)"
    )
    privacy_status: str = Field(default="private", description="YouTube privacy status")
    publish_at: str | None = Field(
        default=None, description="ISO 8601 UTC timestamp for scheduled release"
    )
    made_for_kids: bool = Field(default=False, description="COPPA compliance flag")
    synthetic_content_disclosure: bool = Field(
        default=True, description="YouTube synthetic content disclosure"
    )
    chapters: list[dict[str, str]] = Field(
        default_factory=list, description="Timestamped chapter markers"
    )


class PublishResult(BaseModel):
    """Execution outcome from publishing stage."""

    job_id: str
    success: bool
    mode: PublishMode
    video_id: str | None = None
    youtube_url: str | None = None
    scheduled_at: str | None = None
    fallback_package_path: str | None = None
    is_restricted_api: bool = False
    details: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
