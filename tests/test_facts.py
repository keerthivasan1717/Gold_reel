"""Tests for fact models, validation rules, and fact store."""

import pytest

from goldreel.facts.models import ComicFact, FactRecord, FactTable, SourceAttribution
from goldreel.facts.store import FactStore


def test_fact_table_requires_provenance():
    # Missing sources should fail
    with pytest.raises(ValueError):
        FactTable(
            topic_id="test_topic",
            title="Test Title",
            lane="sports",
            metric_label="Test Rule",
            sources=[],
            records=[FactRecord(entity="Player A", metric="Runs", value=100)],
        )

    # Valid fact table
    src = SourceAttribution(
        name="cricsheet",
        source_url="https://cricsheet.org/matches/",
        retrieved_at="2026-11-18T12:00:00Z",
    )
    table = FactTable(
        topic_id="test_topic",
        title="Test Title",
        lane="sports",
        metric_label="By IPL runs",
        sources=[src],
        records=[FactRecord(rank=1, entity="Player A", metric="Runs", value=100)],
    )
    assert len(table.records) == 1
    assert table.sources[0].name == "cricsheet"


def test_comic_fact_requires_two_agreeing_sources():
    src1 = SourceAttribution(
        name="wikidata",
        source_url="https://www.wikidata.org/wiki/Q79037",
        retrieved_at="2026-11-18T12:00:00Z",
    )
    src2 = SourceAttribution(
        name="grand_comics_database",
        source_url="https://www.comics.org/issue/17106/",
        retrieved_at="2026-11-18T12:00:00Z",
    )

    # Valid comic fact with 2 sources and agreement_verified=True
    cf = ComicFact(
        topic_id="spiderman_debut",
        entity="Spider-Man",
        publisher="Marvel Comics",
        creators=["Stan Lee", "Steve Ditko"],
        first_appearance_title="Amazing Fantasy #15",
        publication_year=1962,
        cover_date="August 1962",
        sources=[src1, src2],
        agreement_verified=True,
    )
    assert cf.publication_year == 1962

    # Reject if only 1 source provided
    with pytest.raises((ValueError, Exception), match="at least"):
        ComicFact(
            topic_id="spiderman_debut",
            entity="Spider-Man",
            publisher="Marvel Comics",
            first_appearance_title="Amazing Fantasy #15",
            publication_year=1962,
            cover_date="August 1962",
            sources=[src1],
            agreement_verified=True,
        )

    # Reject if sources are duplicate names
    src1_dup = SourceAttribution(
        name="wikidata", source_url="https://other.url", retrieved_at="2026-11-18T12:00:00Z"
    )
    with pytest.raises(ValueError, match="distinct sources"):
        ComicFact(
            topic_id="spiderman_debut",
            entity="Spider-Man",
            publisher="Marvel Comics",
            first_appearance_title="Amazing Fantasy #15",
            publication_year=1962,
            cover_date="August 1962",
            sources=[src1, src1_dup],
            agreement_verified=True,
        )

    # Reject if agreement_verified is False
    with pytest.raises(ValueError, match="agreement_verified=True"):
        ComicFact(
            topic_id="spiderman_debut",
            entity="Spider-Man",
            publisher="Marvel Comics",
            first_appearance_title="Amazing Fantasy #15",
            publication_year=1962,
            cover_date="August 1962",
            sources=[src1, src2],
            agreement_verified=False,
        )


def test_fact_store_save_and_load(tmp_path):
    store = FactStore(base_dir=tmp_path / "facts")
    src = SourceAttribution(
        name="cricsheet",
        source_url="https://cricsheet.org",
        retrieved_at="2026-11-18T12:00:00Z",
    )
    table = FactTable(
        topic_id="ipl_centuries",
        title="IPL Centuries",
        lane="sports",
        metric_label="By centuries",
        sources=[src],
        records=[FactRecord(rank=1, entity="Virat Kohli", metric="Centuries", value=8)],
    )

    saved_path = store.save(table)
    assert saved_path.exists()

    reloaded = store.load("ipl_centuries")
    assert reloaded.topic_id == "ipl_centuries"
    assert reloaded.records[0].entity == "Virat Kohli"
    assert reloaded.records[0].value == 8
