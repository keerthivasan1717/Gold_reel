"""Voice timing models for speech alignment and timing-driven scenes."""

from pathlib import Path

from pydantic import BaseModel, Field


class WordTiming(BaseModel):
    word: str
    start_sec: float
    end_sec: float


class SentenceTiming(BaseModel):
    sentence_index: int
    text: str
    start_sec: float
    end_sec: float
    words: list[WordTiming] = Field(default_factory=list)

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)


class VoiceTrack(BaseModel):
    audio_path: Path
    total_duration_sec: float
    sentences: list[SentenceTiming] = Field(default_factory=list)

    def get_sentence_at(self, time_sec: float) -> SentenceTiming | None:
        """Find the active sentence at timestamp t."""
        for s in self.sentences:
            if s.start_sec <= time_sec <= s.end_sec:
                return s
        return None
