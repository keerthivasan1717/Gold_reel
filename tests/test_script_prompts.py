"""Tests for script prompts generation."""

import json
from pathlib import Path

from goldreel.adapters.cricsheet import CricsheetAdapter
from goldreel.script.prompts import SYSTEM_PROMPT, build_script_prompt

FIXTURES_DIR = Path("tests/fixtures")


def test_build_script_prompt():
    with open(FIXTURES_DIR / "SAMPLE_cricket_facts.json", encoding="utf-8") as f:
        fact_table = CricsheetAdapter().extract_facts(json.load(f))

    prompt = build_script_prompt(fact_table, format_type="landscape", target_duration_sec=120)

    assert "FACT TABLE (Ground Truth):" in prompt
    assert "Virat Kohli" in prompt
    assert "REQUIRED JSON SCHEMA:" in prompt
    assert "TRUTH & FACTS ONLY" in SYSTEM_PROMPT
    assert "ZERO HALLUCINATION" in SYSTEM_PROMPT
