"""Tests for Piper voice synthesis, models, and sentence timings."""

import json
from pathlib import Path

from goldreel.adapters.cricsheet import CricsheetAdapter
from goldreel.script.router import ProviderRouter
from goldreel.voice.models import SentenceTiming, VoiceTrack, WordTiming
from goldreel.voice.piper import PiperWrapper

FIXTURES_DIR = Path("tests/fixtures")


def test_voice_models_lookup():
    words = [
        WordTiming(word="Virat", start_sec=0.0, end_sec=0.5),
        WordTiming(word="Kohli", start_sec=0.5, end_sec=1.0),
    ]
    sentence = SentenceTiming(
        sentence_index=1,
        text="Virat Kohli leads.",
        start_sec=0.0,
        end_sec=2.0,
        words=words,
    )
    track = VoiceTrack(
        audio_path=Path("fake/path.wav"),
        total_duration_sec=2.0,
        sentences=[sentence],
    )

    assert track.get_sentence_at(0.5) is not None
    assert track.get_sentence_at(0.5).sentence_index == 1
    assert track.get_sentence_at(5.0) is None
    assert sentence.duration_sec == 2.0


def test_piper_wrapper_narration_generation(tmp_path):
    with open(FIXTURES_DIR / "SAMPLE_cricket_facts.json", encoding="utf-8") as f:
        fact_table = CricsheetAdapter().extract_facts(json.load(f))

    router = ProviderRouter()
    script = router.generate_script(fact_table, format_type="landscape", target_duration_sec=15)

    piper = PiperWrapper()
    out_wav = tmp_path / "test_narration.wav"
    voice_track = piper.generate_narration(script, out_wav)

    assert out_wav.exists()
    assert out_wav.stat().st_size > 1000
    assert voice_track.total_duration_sec > 1.0
    assert len(voice_track.sentences) >= len(script.scenes)
    # Check sentence boundary continuity
    for i in range(len(voice_track.sentences) - 1):
        s_cur = voice_track.sentences[i]
        s_next = voice_track.sentences[i + 1]
        assert s_cur.end_sec <= s_next.start_sec + 0.1
