"""Tests for the Automated Fact Gate."""

import json
from pathlib import Path

from goldreel.facts.gate import FactGate
from goldreel.facts.models import FactTable

FIXTURES_DIR = Path("tests/fixtures")


def load_sample_cricket_facts() -> FactTable:
    path = FIXTURES_DIR / "SAMPLE_cricket_facts.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    from goldreel.adapters.cricsheet import CricsheetAdapter

    adapter = CricsheetAdapter()
    return adapter.extract_facts(data)


def test_fact_gate_passes_verified_script():
    table = load_sample_cricket_facts()
    gate = FactGate(table)

    valid_script = {
        "hook": "Who owns the most centuries in Indian Premier League history?",
        "narration_scenes": [
            {
                "scene_index": 1,
                "text": "At number 1 is Virat Kohli with 8 centuries.",
            },
            {
                "scene_index": 2,
                "text": "Jos Buttler sits second with 7 centuries.",
            },
            {
                "scene_index": 3,
                "text": "Chris Gayle ranks 3rd with 6 centuries.",
            },
        ],
        "outro_text": "Source: Cricsheet 2008 to 2024 open data.",
    }

    result = gate.verify_script(valid_script)
    assert result.passed is True
    assert len(result.violations) == 0
    assert "Virat Kohli" in result.checked_entities
    assert "8" in result.checked_numbers


def test_fact_gate_fails_hallucinated_number():
    table = load_sample_cricket_facts()
    gate = FactGate(table)

    hallucinated_script = {
        "hook": "Who owns the most centuries in IPL history?",
        "narration_scenes": [
            {
                "scene_index": 1,
                # 99 centuries is hallucinated / unverified
                "text": "Virat Kohli smashed an unbelievable 99 centuries.",
            }
        ],
    }

    result = gate.verify_script(hallucinated_script)
    assert result.passed is False
    assert len(result.violations) >= 1
    assert any("99" in v for v in result.violations)
    assert "Unverified number '99'" in result.violations[0]


def test_fact_gate_fails_hallucinated_year():
    table = load_sample_cricket_facts()
    gate = FactGate(table)

    hallucinated_year_script = {
        "hook": "Cricket history check",
        "narration_scenes": [
            {
                "scene_index": 1,
                # 1985 is not in IPL fact table (2008-2024)
                "text": "The IPL was founded back in 1985.",
            }
        ],
    }

    result = gate.verify_script(hallucinated_year_script)
    assert result.passed is False
    assert any("1985" in v for v in result.violations)
