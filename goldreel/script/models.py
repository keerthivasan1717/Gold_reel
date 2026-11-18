"""Script data models for GoldReel narration."""

from typing import Literal

from pydantic import BaseModel, Field


class ScriptScene(BaseModel):
    scene_index: int = Field(..., description="1-based scene index")
    scene_type: Literal["hook", "data", "insight", "outro"] = Field(
        ..., description="Scene classification"
    )
    text: str = Field(..., description="Narration voiceover line")
    target_duration_sec: float = Field(default=5.0, description="Estimated duration in seconds")
    bound_entities: list[str] = Field(
        default_factory=list, description="Entities mentioned in this scene"
    )
    bound_numbers: list[str | int | float] = Field(
        default_factory=list, description="Verified numbers used in text"
    )


class GeneratedScript(BaseModel):
    topic_id: str
    title: str
    lane: Literal["sports", "comics"]
    format_type: Literal["landscape", "portrait"]
    template_type: str = Field(
        ..., description="stat_race, ranked_countdown, scroll_compare, milestone"
    )
    hook: str = Field(..., description="High-retention opening hook question or statement")
    scenes: list[ScriptScene] = Field(..., min_length=2, description="Sequence of narration scenes")
    insight: str = Field(
        ..., description="Analytical takeaway / original insight required by GEMINI.md"
    )
    outro_text: str = Field(..., description="Closing line with credits and dataset attribution")
    estimated_duration_sec: float = Field(default=35.0)

    @property
    def full_text(self) -> str:
        """Concatenated narration text."""
        parts = [self.hook]
        for s in self.scenes:
            parts.append(s.text)
        parts.append(self.insight)
        parts.append(self.outro_text)
        return " ".join(parts)

    @property
    def total_words(self) -> int:
        return len(self.full_text.split())
