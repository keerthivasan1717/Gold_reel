"""Timeline and keyframe management for video frame generation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Keyframe:
    time_sec: float
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Timeline:
    duration_sec: float
    fps: int = 30
    width: int = 1920
    height: int = 1080
    keyframes: list[Keyframe] = field(default_factory=list)

    @property
    def total_frames(self) -> int:
        return max(1, int(round(self.duration_sec * self.fps)))

    def time_at_frame(self, frame_index: int) -> float:
        return frame_index / self.fps

    def frame_at_time(self, time_sec: float) -> int:
        return int(round(time_sec * self.fps))
