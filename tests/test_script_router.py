"""Tests for AI provider router and offline script synthesis."""

import json
from pathlib import Path

from goldreel.adapters.cricsheet import CricsheetAdapter
from goldreel.script.router import ProviderRouter

FIXTURES_DIR = Path("tests/fixtures")


def test_provider_router_offline_synthesis():
    with open(FIXTURES_DIR / "SAMPLE_cricket_facts.json", encoding="utf-8") as f:
        fact_table = CricsheetAdapter().extract_facts(json.load(f))

    router = ProviderRouter()
    # In test environment without external API keys, router gracefully falls back to deterministic synthesizer
    script = router.generate_script(fact_table, format_type="landscape", target_duration_sec=120)

    assert script.topic_id == fact_table.topic_id
    assert script.hook is not None
    assert len(script.scenes) >= 2
    assert "Virat Kohli" in script.full_text
    assert script.insight is not None and len(script.insight) > 10
    assert "Cricsheet" in script.outro_text
    assert script.total_words > 20


def test_provider_router_fallback_chain_without_keys():
    router = ProviderRouter()
    assert "gemini" in router.config.default_chain
    assert "groq" in router.config.default_chain
