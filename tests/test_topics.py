"""Tests for topic angle discovery, scoring, and deduplication against history."""

import json
from pathlib import Path

from goldreel.adapters.cricsheet import CricsheetAdapter
from goldreel.adapters.wikidata import WikidataComicAdapter
from goldreel.topics.finder import AngleFinder
from goldreel.topics.history import TopicHistory, calculate_topic_similarity

FIXTURES_DIR = Path("tests/fixtures")


def test_topic_similarity_calculation():
    # Exactly same titles and entities
    sim_exact = calculate_topic_similarity(
        "IPL Most Centuries 2008-2024",
        ["Virat Kohli", "Jos Buttler"],
        "IPL Most Centuries 2008-2024",
        ["Virat Kohli", "Jos Buttler"],
    )
    assert sim_exact == 100.0

    # Completely different
    sim_diff = calculate_topic_similarity(
        "IPL Most Centuries 2008-2024",
        ["Virat Kohli", "Jos Buttler"],
        "Premier League Top Scorers",
        ["Erling Haaland", "Cole Palmer"],
    )
    assert sim_diff == 0.0

    # Partial overlap
    sim_partial = calculate_topic_similarity(
        "IPL Most Centuries 2024",
        ["Virat Kohli", "Jos Buttler"],
        "IPL Century Kings",
        ["Virat Kohli", "David Warner"],
    )
    assert 20.0 <= sim_partial <= 75.0


def test_topic_history_deduplication(tmp_path):
    history_file = tmp_path / "test_history.json"
    history = TopicHistory(history_file=history_file)

    # Initially empty
    is_dup, _, sim = history.check_similarity("IPL Centuries", ["Virat Kohli", "Jos Buttler"])
    assert not is_dup
    assert sim == 0.0

    # Record first video
    history.record_topic(
        job_id="job_001",
        topic_id="ipl_centuries",
        title="Most Centuries in IPL History",
        lane="sports",
        angle_id="stat_race",
        entities=["Virat Kohli", "Jos Buttler", "Chris Gayle"],
        facts_hash="hash_abc123",
    )

    # Check same fact hash (100% duplicate)
    is_dup_hash, dup_id, sim_hash = history.check_similarity(
        title="Different Title",
        entities=["Someone Else"],
        facts_hash="hash_abc123",
    )
    assert is_dup_hash is True
    assert dup_id == "ipl_centuries"
    assert sim_hash == 100.0

    # Check high text similarity (> 85%)
    is_dup_text, dup_id_text, sim_text = history.check_similarity(
        title="Most Centuries in IPL History",
        entities=["Virat Kohli", "Jos Buttler", "Chris Gayle"],
        threshold=85.0,
    )
    assert is_dup_text is True
    assert sim_text >= 85.0


def test_angle_finder_matching(tmp_path):
    history = TopicHistory(history_file=tmp_path / "history.json")
    finder = AngleFinder(history=history)

    # Sports facts
    with open(FIXTURES_DIR / "SAMPLE_cricket_facts.json", encoding="utf-8") as f:
        cricket_facts = CricsheetAdapter().extract_facts(json.load(f))

    candidates_sports = finder.find_angles(cricket_facts, target_format="landscape")
    assert len(candidates_sports) >= 1
    angle_ids = [c.angle_id for c in candidates_sports]
    assert "stat_race" in angle_ids or "ranked_countdown" in angle_ids
    assert all(c.lane == "sports" for c in candidates_sports)

    # Comics facts
    with open(FIXTURES_DIR / "SAMPLE_wikidata_comic.json", encoding="utf-8") as f:
        comic_facts = WikidataComicAdapter().extract_facts(json.load(f))

    candidates_comics = finder.find_angles(comic_facts, target_format="landscape")
    assert len(candidates_comics) >= 1
    assert all(c.lane == "comics" for c in candidates_comics)
