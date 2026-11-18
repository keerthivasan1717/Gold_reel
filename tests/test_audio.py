"""Tests for music library, ducking mixer, and credits generator."""

import json
from pathlib import Path

from goldreel.adapters.cricsheet import CricsheetAdapter
from goldreel.audio.credits import CreditsGenerator
from goldreel.audio.ducking import AudioMixer
from goldreel.audio.library import MusicLibrary

FIXTURES_DIR = Path("tests/fixtures")


def test_music_library_loads_tracks():
    lib = MusicLibrary()
    assert len(lib.tracks) >= 1
    track = lib.select_track(lane="sports")
    assert track.title is not None
    assert track.licence is not None
    assert track.url.startswith("http")


def test_credits_generator():
    with open(FIXTURES_DIR / "SAMPLE_cricket_facts.json", encoding="utf-8") as f:
        fact_table = CricsheetAdapter().extract_facts(json.load(f))

    lib = MusicLibrary()
    track = lib.select_track(lane="sports")

    desc_credits = CreditsGenerator.generate_description_credits(fact_table, track)
    assert "--- LICENSES & ATTRIBUTION ---" in desc_credits
    assert "Cricsheet" in desc_credits
    assert track.title in desc_credits
    assert "Piper TTS" in desc_credits

    outro_line = CreditsGenerator.generate_outro_credit(fact_table, track)
    assert "Data: Cricsheet" in outro_line
    assert track.title in outro_line


def test_audio_mixer_ducking_and_loudnorm(tmp_path):
    mixer = AudioMixer()
    # Generate 3-second test voice tone
    import subprocess

    v_wav = tmp_path / "voice_tone.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=180:duration=3", str(v_wav)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )

    music_path = Path("assets/music/midnight_gold.mp3")
    out_mixed = tmp_path / "mixed_output.mp3"

    mixed = mixer.mix_and_duck(
        voice_path=v_wav,
        music_path=music_path if music_path.exists() else None,
        output_path=out_mixed,
        target_loudness_lufs=-14.0,
        max_true_peak_dbfs=-1.0,
    )

    assert mixed.exists()
    assert mixed.stat().st_size > 1000
