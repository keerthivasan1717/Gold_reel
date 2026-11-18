"""Tests for GoldReel configuration loader."""

from goldreel.config.loader import (
    load_pipeline_config,
    load_providers_config,
    load_topics_config,
)


def test_pipeline_config_loads_defaults():
    cfg = load_pipeline_config()
    assert cfg.publishing.publish_enabled is False  # Safe default kill-switch
    assert cfg.publishing.max_uploads_per_day <= 6
    assert cfg.publishing.synthetic_content_disclosure is True
    assert cfg.lanes.sports.enabled is True
    assert cfg.lanes.comics.enabled is True
    assert cfg.lanes.comics.require_two_sources is True
    assert cfg.lanes.comics.artwork_allowed is False
    assert cfg.quality_control.similarity_threshold_percent == 85.0


def test_providers_config_chain():
    cfg = load_providers_config()
    assert "gemini" in cfg.default_chain
    assert "groq" in cfg.default_chain
    assert "gemini" in cfg.providers
    assert cfg.providers["gemini"].rate_limit.requests_per_minute > 0
    assert cfg.providers["groq"].rate_limit.requests_per_minute > 0


def test_topics_config_angles():
    cfg = load_topics_config()
    angle_ids = [a.id for a in cfg.angles]
    assert "stat_race" in angle_ids
    assert "ranked_countdown" in angle_ids
    assert "scroll_compare" in angle_ids
    assert "milestone_anniversary" in angle_ids
    for angle in cfg.angles:
        assert angle.lane in ("sports", "comics")
        assert angle.scoring_weight > 0
