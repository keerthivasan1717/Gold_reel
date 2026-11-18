"""Integration test for rendering video with muxed audio track."""

import json
import subprocess
from pathlib import Path

from goldreel.adapters.cricsheet import CricsheetAdapter
from goldreel.audio.ducking import AudioMixer
from goldreel.render.engine import RenderEngine
from goldreel.render.templates.stat_race import StatRaceTemplate
from goldreel.script.router import ProviderRouter
from goldreel.voice.piper import PiperWrapper

FIXTURES_DIR = Path("tests/fixtures")


def test_render_with_muxed_audio(tmp_path):
    with open(FIXTURES_DIR / "SAMPLE_cricket_facts.json", encoding="utf-8") as f:
        fact_table = CricsheetAdapter().extract_facts(json.load(f))

    router = ProviderRouter()
    script = router.generate_script(fact_table, format_type="landscape", target_duration_sec=3)
    script_3s = script.model_copy(update={"estimated_duration_sec": 3.0})

    # 1. Voice
    piper = PiperWrapper()
    voice_wav = tmp_path / "voice_test.wav"
    voice_track = piper.generate_narration(script_3s, voice_wav)

    # 2. Audio Mix
    mixer = AudioMixer()
    music_file = Path("assets/music/midnight_gold.mp3")
    mixed_mp3 = tmp_path / "mixed_test.mp3"
    mixer.mix_and_duck(
        voice_path=voice_track.audio_path,
        music_path=music_file if music_file.exists() else None,
        output_path=mixed_mp3,
    )

    # 3. Render video with muxed audio
    engine = RenderEngine()
    template = StatRaceTemplate(seed=42)
    out_video = tmp_path / "final_video_with_audio.mp4"

    stats = engine.render(
        template=template,
        fact_table=fact_table,
        script=script_3s,
        output_path=out_video,
        fps=24,
        audio_path=mixed_mp3,
    )

    assert out_video.exists()
    assert out_video.stat().st_size > 5000
    assert stats.total_frames > 0

    # Probe FFmpeg to verify audio stream is present
    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(out_video),
    ]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    assert "aac" in probe.stdout.lower()
