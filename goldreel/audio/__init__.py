"""Audio package."""

from .credits import CreditsGenerator
from .ducking import AudioMixer
from .library import MusicLibrary, MusicTrack

__all__ = ["AudioMixer", "CreditsGenerator", "MusicLibrary", "MusicTrack"]
