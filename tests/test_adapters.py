"""Tests for Cricsheet, Football, and Wikidata open data adapters."""

from pathlib import Path

from goldreel.adapters.cricsheet import CricsheetAdapter
from goldreel.adapters.football import FootballAdapter
from goldreel.adapters.wikidata import WikidataComicAdapter

FIXTURES_DIR = Path("tests/fixtures")


def test_cricsheet_adapter_match_aggregation():
    adapter = CricsheetAdapter()
    match_file = FIXTURES_DIR / "SAMPLE_cricsheet_match.json"
    import json

    with open(match_file, encoding="utf-8") as f:
        match_data = json.load(f)

    # In the sample match: Virat Kohli scores 50+59 = 109 runs (1 century), AB de Villiers scores 129 runs (1 century)
    centuries = adapter.aggregate_centuries_from_matches([match_data])
    players = [p[0] for p in centuries]
    assert "Virat Kohli" in players
    assert "AB de Villiers" in players
    for _p, count in centuries:
        assert count == 1

    # Extract facts into FactTable
    fact_table = adapter.extract_facts([match_data])
    assert fact_table.lane == "sports"
    assert len(fact_table.records) >= 2
    assert fact_table.sources[0].name == "cricsheet"
    assert "CC-BY 4.0" in fact_table.sources[0].attribution_text


def test_football_adapter():
    adapter = FootballAdapter()
    standings_file = FIXTURES_DIR / "SAMPLE_football_standings.json"
    fact_table = adapter.extract_facts(standings_file)

    assert fact_table.lane == "sports"
    assert len(fact_table.records) == 5
    assert fact_table.records[0].entity == "Erling Haaland"
    assert fact_table.records[0].value == 27
    assert fact_table.records[0].unit == "goals"


def test_wikidata_adapter_cross_verification_agreement():
    adapter = WikidataComicAdapter()
    comics_file = FIXTURES_DIR / "SAMPLE_wikidata_comic.json"
    fact_table = adapter.extract_facts(comics_file)

    assert fact_table.lane == "comics"
    assert len(fact_table.records) >= 2
    entities = [r.entity for r in fact_table.records]
    assert "Spider-Man" in entities
    assert "Batman" in entities

    # Check sources
    src_names = [s.name for s in fact_table.sources]
    assert "wikidata" in src_names
    assert "secondary_catalog" in src_names or "grand_comics_database" in src_names


def test_wikidata_adapter_drops_fact_on_disagreement():
    adapter = WikidataComicAdapter()

    primary = {
        "entity": "Spider-Man",
        "publisher": "Marvel Comics",
        "first_appearance_title": "Amazing Fantasy #15",
        "publication_year": 1962,
    }
    # Disagreement on year: secondary says 1965
    secondary_year_mismatch = {
        "entity": "Spider-Man",
        "publisher": "Marvel Comics",
        "first_appearance_title": "Amazing Fantasy #15",
        "publication_year": 1965,
    }
    result = adapter.cross_verify(primary, secondary_year_mismatch)
    assert result is None, "Fact should be dropped when publication years disagree"

    # Disagreement on publisher: secondary says DC Comics
    secondary_pub_mismatch = {
        "entity": "Spider-Man",
        "publisher": "DC Comics",
        "first_appearance_title": "Amazing Fantasy #15",
        "publication_year": 1962,
    }
    result_pub = adapter.cross_verify(primary, secondary_pub_mismatch)
    assert result_pub is None, "Fact should be dropped when publishers disagree"
