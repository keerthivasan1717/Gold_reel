"""Benchmark script to measure render time and peak RAM for full videos.

Measures:
1. 3-minute 1080p landscape video (1920x1080, 180 seconds @ 24 fps = 4,320 frames).
2. 45-second vertical Short (1080x1920, 45 seconds @ 24 fps = 1,080 frames).
"""

import json
from pathlib import Path

from goldreel.adapters.cricsheet import CricsheetAdapter
from goldreel.adapters.wikidata import WikidataComicAdapter
from goldreel.render.engine import RenderEngine
from goldreel.render.layouts.landscape import LandscapeLayout
from goldreel.render.templates.ranked_countdown import RankedCountdownTemplate
from goldreel.render.templates.stat_race import StatRaceTemplate
from goldreel.script.router import ProviderRouter


def run_benchmarks(output_dir: Path | str = "out/benchmark"):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    engine = RenderEngine()

    print("=== GOLDREEL MILESTONE 4 RENDERING BENCHMARK ===")

    # 1. 3-Minute 1080p Landscape Video (Stat Race)
    print("\n[1/2] Benchmarking 3-minute 1080p Landscape Video (1920x1080, 180s @ 24fps)...")
    with open("tests/fixtures/SAMPLE_cricket_facts.json", encoding="utf-8") as f:
        sports_facts = CricsheetAdapter().extract_facts(json.load(f))

    router = ProviderRouter()
    script_3min = router.generate_script(
        sports_facts, format_type="landscape", target_duration_sec=180
    )
    template_race = StatRaceTemplate(seed=42)

    mp4_3min = out_path / "benchmark_3min_landscape.mp4"
    stats_3min = engine.render(
        template=template_race,
        fact_table=sports_facts,
        script=script_3min,
        output_path=mp4_3min,
        fps=24,
    )

    print(f"  -> Total Frames:     {stats_3min.total_frames}")
    print(f"  -> Render Duration:  {stats_3min.elapsed_time_sec:.2f} s")
    print(f"  -> Render Speed:     {stats_3min.fps_render_speed:.1f} fps")
    print(f"  -> Peak RAM:         {stats_3min.peak_ram_mb:.2f} MB")
    print(f"  -> Output Size:      {mp4_3min.stat().st_size / (1024 * 1024):.2f} MB")

    # 2. 45-Second Vertical Short (Ranked Countdown)
    print("\n[2/2] Benchmarking 45-second Vertical Short (1080x1920, 45s @ 24fps)...")
    with open("tests/fixtures/SAMPLE_wikidata_comic.json", encoding="utf-8") as f:
        comic_facts = WikidataComicAdapter().extract_facts(json.load(f))

    script_short = router.generate_script(
        comic_facts, format_type="portrait", target_duration_sec=45
    )
    portrait_layout = LandscapeLayout(width=1080, height=1920, margin=60)
    template_short = RankedCountdownTemplate(layout=portrait_layout, seed=99)

    mp4_short = out_path / "benchmark_45s_short.mp4"
    stats_short = engine.render(
        template=template_short,
        fact_table=comic_facts,
        script=script_short,
        output_path=mp4_short,
        fps=24,
    )

    print(f"  -> Total Frames:     {stats_short.total_frames}")
    print(f"  -> Render Duration:  {stats_short.elapsed_time_sec:.2f} s")
    print(f"  -> Render Speed:     {stats_short.fps_render_speed:.1f} fps")
    print(f"  -> Peak RAM:         {stats_short.peak_ram_mb:.2f} MB")
    print(f"  -> Output Size:      {mp4_short.stat().st_size / (1024 * 1024):.2f} MB")

    return stats_3min, stats_short


if __name__ == "__main__":
    run_benchmarks()
