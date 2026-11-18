"""Tests for render engine, templates, procedural background, and FFmpeg frame piping."""

import json
from pathlib import Path

from goldreel.adapters.cricsheet import CricsheetAdapter
from goldreel.render.background import ProceduralBackground
from goldreel.render.easing import ease_in_out_quad, ease_out_quad, linear
from goldreel.render.engine import RenderEngine
from goldreel.render.templates.ranked_countdown import RankedCountdownTemplate
from goldreel.render.templates.stat_race import StatRaceTemplate
from goldreel.script.router import ProviderRouter

FIXTURES_DIR = Path("tests/fixtures")


def get_sample_fact_table():
    with open(FIXTURES_DIR / "SAMPLE_cricket_facts.json", encoding="utf-8") as f:
        return CricsheetAdapter().extract_facts(json.load(f))


def test_easing_functions():
    # Linear
    assert linear(0.0) == 0.0
    assert linear(0.5) == 0.5
    assert linear(1.0) == 1.0

    # Ease out quad
    assert ease_out_quad(0.0) == 0.0
    assert ease_out_quad(0.5) == 0.75
    assert ease_out_quad(1.0) == 1.0

    # Ease in out quad
    assert ease_in_out_quad(0.0) == 0.0
    assert ease_in_out_quad(0.5) == 0.5
    assert ease_in_out_quad(1.0) == 1.0

    # Out of bounds clamping
    assert ease_out_quad(-1.0) == 0.0
    assert ease_out_quad(2.0) == 1.0


def test_procedural_background_render():
    bg = ProceduralBackground(width=1920, height=1080, seed=123)
    frame_0 = bg.render(t=0.0, total_duration=10.0)
    assert frame_0.size == (1920, 1080)
    assert frame_0.mode == "RGB"

    # Drift over time
    frame_5 = bg.render(t=5.0, total_duration=10.0)
    assert frame_5.size == (1920, 1080)


def test_stat_race_template_draw():
    fact_table = get_sample_fact_table()
    router = ProviderRouter()
    script = router.generate_script(fact_table, format_type="landscape")

    template = StatRaceTemplate(seed=42)
    timeline = template.plan(fact_table, script)
    assert timeline.total_frames > 0

    frame_start = template.draw(t=0.5)
    assert frame_start.size == (1920, 1080)

    frame_mid = template.draw(t=5.0)
    assert frame_mid.size == (1920, 1080)


def test_ranked_countdown_template_draw():
    fact_table = get_sample_fact_table()
    router = ProviderRouter()
    script = router.generate_script(fact_table, format_type="landscape")

    template = RankedCountdownTemplate(seed=42)
    timeline = template.plan(fact_table, script)
    assert timeline.total_frames > 0

    frame = template.draw(t=2.0)
    assert frame.size == (1920, 1080)


def test_render_engine_ffmpeg_pipe(tmp_path):
    fact_table = get_sample_fact_table()
    router = ProviderRouter()
    script = router.generate_script(fact_table, format_type="landscape")
    # 1.0 second test clip
    test_script = script.model_copy(update={"estimated_duration_sec": 1.0})

    template = StatRaceTemplate(seed=42)
    engine = RenderEngine()
    out_mp4 = tmp_path / "test_render.mp4"

    stats = engine.render(
        template=template,
        fact_table=fact_table,
        script=test_script,
        output_path=out_mp4,
        fps=24,
    )

    assert out_mp4.exists()
    assert out_mp4.stat().st_size > 1000
    assert stats.total_frames == 24
    assert stats.peak_ram_mb < 500.0  # Peak RAM should be well under 500 MB

