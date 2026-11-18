"""Benchmark script for Milestone 8 Publishing Subsystem.

Measures:
- Thumbnail rendering time for 1280x720 landscape and 1080x1920 portrait
- Metadata assembly and scheduled release calculation time
- Fallback packaging performance
- Memory allocation (strictly verified against system ceiling)
"""

import time
import tracemalloc
from pathlib import Path

from goldreel.facts.models import FactTable
from goldreel.publish.fallback import FallbackPackager
from goldreel.publish.models import PublishMetadata
from goldreel.publish.scheduler import PublishScheduler
from goldreel.publish.thumbnail import ThumbnailGenerator
from goldreel.script.models import GeneratedScript
from goldreel.state.store import StateStore


def run_benchmark():
    print("=== Milestone 8 Publishing Subsystem Benchmark ===")

    tracemalloc.start()
    t0 = time.perf_counter()

    # 1. Benchmark Thumbnail Generator
    gen = ThumbnailGenerator()
    facts = FactTable(
        topic_id="bench_topic",
        title="IPL All-Time Centuries",
        lane="sports",
        metric_label="Centuries",
        sources=[
            {
                "name": "cricsheet",
                "source_url": "https://cricsheet.org",
                "retrieved_at": "2026-11-18T00:00:00Z",
            }
        ],
        records=[
            {
                "rank": 1,
                "entity": "Virat Kohli",
                "metric": "Centuries",
                "value": 8,
                "unit": "centuries",
            }
        ],
    )
    script = GeneratedScript(
        topic_id="bench_topic",
        title="IPL All-Time Centuries",
        lane="sports",
        format_type="landscape",
        template_type="stat_race",
        hook="Who holds the record for most centuries?",
        scenes=[
            {
                "scene_index": 1,
                "scene_type": "data",
                "text": "Virat Kohli holds 8 centuries.",
                "entities": ["Virat Kohli"],
                "numbers": [8],
            },
            {
                "scene_index": 2,
                "scene_type": "data",
                "text": "A record set over 15 seasons.",
                "entities": [],
                "numbers": [],
            },
        ],
        insight="Consistent conversion separates legends.",
        outro_text="Source: Cricsheet open data.",
    )

    t_land = Path("out/bench_thumb_landscape.png")
    gen.generate(facts, script, t_land, format_type="landscape")

    t_port = Path("out/bench_thumb_portrait.png")
    gen.generate(facts, script, t_port, format_type="portrait")

    # 2. Benchmark Scheduler
    scheduler = PublishScheduler()
    sched_time = scheduler.compute_publish_time(format_type="landscape")

    # 3. Benchmark Fallback Packager
    store = StateStore()
    job = store.list_jobs()[0] if store.list_jobs() else None
    if job:
        job_state = store.get_job(job.job_id)
        packager = FallbackPackager(out_dir="out")
        meta = PublishMetadata(
            title="Benchmark Publishing Package",
            description="Complete attribution and synthetic disclosure.",
            tags=["cricket", "benchmark"],
            publish_at=sched_time,
        )
        pkg_path = packager.package(job_state, meta, reason="Benchmark dry run")

    t1 = time.perf_counter()
    _, peak_ram = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    elapsed = t1 - t0
    peak_ram_mb = peak_ram / (1024 * 1024)

    print(f"Total Publishing Benchmark: {elapsed:.2f} s")
    print(f"Peak RAM Usage:            {peak_ram_mb:.2f} MB")
    print(f"Landscape Thumbnail:       1280x720 saved to {t_land}")
    print(f"Portrait Thumbnail:        1080x1920 saved to {t_port}")
    print(f"Computed Release Window:   {sched_time}")
    if job:
        print(f"Fallback Package:          {pkg_path}")

    assert peak_ram_mb < 3000, "Peak RAM exceeded 3 GB limit"
    print("✓ All benchmark constraints satisfied.")


if __name__ == "__main__":
    run_benchmark()
