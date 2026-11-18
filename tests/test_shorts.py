"""Tests for YouTube Shorts portrait layouts and templates."""

import json
from pathlib import Path

from goldreel.adapters.cricsheet import CricsheetAdapter
from goldreel.adapters.wikidata import WikidataComicAdapter
from goldreel.render.engine import RenderEngine
from goldreel.render.layouts.portrait import PortraitLayout
from goldreel.render.templates.milestone import MilestoneTemplate
from goldreel.render.templates.scroll_compare import ScrollCompareTemplate
from goldreel.script.router import ProviderRouter

FIXTURES_DIR = Path("tests/fixtures")


def test_portrait_layout_safe_margins():
    layout = PortraitLayout()
    assert layout.width == 1080
    assert layout.height == 1920
    assert layout.margin_x == 60
    assert layout.margin_top == 60
    assert layout.margin_bottom == 120  # Crucial 120px platform UI safe area
    assert layout.usable_w == 1080 - 120
    assert layout.footer_y < (1920 - 120)  # Footer must sit above exclusion zone


def test_scroll_compare_template_portrait():
    with open(FIXTURES_DIR / "SAMPLE_wikidata_comic.json", encoding="utf-8") as f:
        comic_facts = WikidataComicAdapter().extract_facts(json.load(f))

    router = ProviderRouter()
    script = router.generate_script(comic_facts, format_type="portrait", target_duration_sec=30)

    template = ScrollCompareTemplate(seed=42)
    timeline = template.plan(comic_facts, script)

    assert timeline.width == 1080
    assert timeline.height == 1920
    assert timeline.total_frames > 0

    frame_start = template.draw(t=1.0)
    assert frame_start.size == (1080, 1920)

    frame_mid = template.draw(t=15.0)
    assert frame_mid.size == (1080, 1920)


def test_milestone_template_portrait():
    with open(FIXTURES_DIR / "SAMPLE_cricket_facts.json", encoding="utf-8") as f:
        sports_facts = CricsheetAdapter().extract_facts(json.load(f))

    router = ProviderRouter()
    script = router.generate_script(sports_facts, format_type="portrait", target_duration_sec=30)

    template = MilestoneTemplate(seed=42)
    timeline = template.plan(sports_facts, script)

    assert timeline.width == 1080
    assert timeline.height == 1920

    frame_start = template.draw(t=0.5)
    assert frame_start.size == (1080, 1920)

    frame_mid = template.draw(t=10.0)
    assert frame_mid.size == (1080, 1920)


def test_render_short_to_mp4(tmp_path):
    with open(FIXTURES_DIR / "SAMPLE_cricket_facts.json", encoding="utf-8") as f:
        sports_facts = CricsheetAdapter().extract_facts(json.load(f))

    router = ProviderRouter()
    script = router.generate_script(sports_facts, format_type="portrait", target_duration_sec=2)
    script_2s = script.model_copy(update={"estimated_duration_sec": 2.0})

    template = MilestoneTemplate(seed=42)
    engine = RenderEngine()
    out_mp4 = tmp_path / "test_milestone_short.mp4"

    stats = engine.render(
        template=template,
        fact_table=sports_facts,
        script=script_2s,
        output_path=out_mp4,
        fps=24,
    )

    assert out_mp4.exists()
    assert out_mp4.stat().st_size > 2000
    assert stats.total_frames == 48
    assert stats.peak_ram_mb < 500.0
