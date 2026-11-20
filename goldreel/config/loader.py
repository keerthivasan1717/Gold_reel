"""Configuration models and loader for GoldReel."""

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class PublishingConfig(BaseModel):
    publish_enabled: bool = False
    mode: str = "scheduled"
    max_uploads_per_day: int = 1
    max_uploads_per_week: int = 7
    synthetic_content_disclosure: bool = True
    made_for_kids: bool = False


class ProductionCadenceConfig(BaseModel):
    target_long_videos_per_week: int = 7
    target_shorts_per_week: int = 5
    long_video_min_duration_sec: int = 120
    long_video_max_duration_sec: int = 180
    short_video_min_duration_sec: int = 30
    short_video_max_duration_sec: int = 45


class SportsSourceConfig(BaseModel):
    name: str
    enabled: bool = True
    attribution_required: bool = True


class SportsLaneConfig(BaseModel):
    enabled: bool = True
    sources: list[SportsSourceConfig] = Field(default_factory=list)


class ComicSourceConfig(BaseModel):
    name: str
    enabled: bool = True


class ComicsLaneConfig(BaseModel):
    enabled: bool = True
    require_two_sources: bool = True
    artwork_allowed: bool = False
    sources: list[ComicSourceConfig] = Field(default_factory=list)


class LanesConfig(BaseModel):
    sports: SportsLaneConfig = Field(default_factory=SportsLaneConfig)
    comics: ComicsLaneConfig = Field(default_factory=ComicsLaneConfig)


class QualityControlConfig(BaseModel):
    similarity_threshold_percent: float = 85.0
    target_loudness_lufs: float = -14.0
    max_true_peak_dbfs: float = -1.0
    font_safe_margin_px: int = 60


class PipelineConfig(BaseModel):
    pipeline: dict[str, Any] = Field(default_factory=dict)
    publishing: PublishingConfig = Field(default_factory=PublishingConfig)
    production_cadence: ProductionCadenceConfig = Field(default_factory=ProductionCadenceConfig)
    lanes: LanesConfig = Field(default_factory=LanesConfig)
    quality_control: QualityControlConfig = Field(default_factory=QualityControlConfig)


class RateLimitConfig(BaseModel):
    requests_per_minute: int
    requests_per_day: int


class ProviderItem(BaseModel):
    name: str
    model: str
    env_key: str
    rate_limit: RateLimitConfig
    max_tokens: int = 1024
    temperature: float = 0.2


class ProvidersConfig(BaseModel):
    default_chain: list[str] = Field(default_factory=list)
    providers: dict[str, ProviderItem] = Field(default_factory=dict)


class TopicAngle(BaseModel):
    id: str
    name: str
    lane: str
    description: str
    min_data_points: int = 1
    max_data_points: int | None = None
    scoring_weight: float = 1.0
    preferred_format: str = "landscape"


class TopicsConfig(BaseModel):
    angles: list[TopicAngle] = Field(default_factory=list)


def get_default_config_dir() -> Path:
    """Return default directory containing config files."""
    return Path(__file__).resolve().parent


def load_pipeline_config(path: Path | None = None) -> PipelineConfig:
    """Load and validate pipeline.yaml."""
    import os

    cfg_path = path or (get_default_config_dir() / "pipeline.yaml")
    if not cfg_path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {cfg_path}")
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    cfg = PipelineConfig.model_validate(data or {})
    env_pub = os.getenv("GOLDREEL_PUBLISH_ENABLED")
    if env_pub is not None:
        cfg.publishing.publish_enabled = env_pub.lower() in ("1", "true", "yes")
    return cfg


def load_providers_config(path: Path | None = None) -> ProvidersConfig:
    """Load and validate providers.json."""
    cfg_path = path or (get_default_config_dir() / "providers.json")
    if not cfg_path.exists():
        raise FileNotFoundError(f"Providers config not found: {cfg_path}")
    with open(cfg_path, encoding="utf-8") as f:
        data = json.load(f)
    return ProvidersConfig.model_validate(data or {})


def load_topics_config(path: Path | None = None) -> TopicsConfig:
    """Load and validate topics.yaml."""
    cfg_path = path or (get_default_config_dir() / "topics.yaml")
    if not cfg_path.exists():
        raise FileNotFoundError(f"Topics config not found: {cfg_path}")
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return TopicsConfig.model_validate(data or {})
