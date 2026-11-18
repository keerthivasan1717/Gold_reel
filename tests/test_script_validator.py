"""Tests for script validator and fact consistency."""

import json
from pathlib import Path

from goldreel.adapters.cricsheet import CricsheetAdapter
from goldreel.script.models import GeneratedScript, ScriptScene
from goldreel.script.router import ProviderRouter
from goldreel.script.validator import ScriptValidator

FIXTURES_DIR = Path("tests/fixtures")


def get_sample_fact_table():
    with open(FIXTURES_DIR / "SAMPLE_cricket_facts.json", encoding="utf-8") as f:
        return CricsheetAdapter().extract_facts(json.load(f))


def test_script_validator_passes_synthesized_script():
    fact_table = get_sample_fact_table()
    router = ProviderRouter()
    script = router.generate_script(fact_table, format_type="landscape")

    validator = ScriptValidator(fact_table)
    result = validator.validate(script)

    assert result.passed is True
    assert len(result.violations) == 0
    assert result.word_count > 0


def test_script_validator_rejects_missing_insight():
    fact_table = get_sample_fact_table()
    router = ProviderRouter()
    script = router.generate_script(fact_table, format_type="landscape")

    # Clear analytical insight
    invalid_script = script.model_copy(update={"insight": ""})
    validator = ScriptValidator(fact_table)
    result = validator.validate(invalid_script)

    assert result.passed is False
    assert any("insight" in v.lower() for v in result.violations)


def test_script_validator_rejects_hallucinated_facts():
    fact_table = get_sample_fact_table()
    scenes = [
        ScriptScene(
            scene_index=1,
            scene_type="data",
            text="Virat Kohli scored 99 centuries in IPL history.",  # 99 is unverified!
            bound_entities=["Virat Kohli"],
            bound_numbers=[99],
        ),
        ScriptScene(
            scene_index=2,
            scene_type="data",
            text="Jos Buttler scored 7 centuries.",
            bound_entities=["Jos Buttler"],
            bound_numbers=[7],
        ),
    ]
    hallucinated_script = GeneratedScript(
        topic_id=fact_table.topic_id,
        title=fact_table.title,
        lane="sports",
        format_type="landscape",
        template_type="stat_race",
        hook="Who scored the most centuries in IPL history?",
        scenes=scenes,
        insight="A record that may never be broken.",
        outro_text="Source: Cricsheet data.",
    )

    validator = ScriptValidator(fact_table)
    result = validator.validate(hallucinated_script)

    assert result.passed is False
    assert any("99" in v for v in result.violations)
