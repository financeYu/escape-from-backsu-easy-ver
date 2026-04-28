"""Configuration loading for content research MVP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class PolicyConfig:
    youtube_metadata_only: bool = True
    forbid_youtube_html_scraping: bool = True
    forbid_video_download: bool = True
    forbid_unauthorized_transcripts: bool = True
    forbid_bulk_comment_scraping: bool = True
    forbid_creator_style_cloning: bool = True
    forbid_investment_advice: bool = True


@dataclass(frozen=True)
class ScoringWeights:
    popularity: float = 0.22
    economic_linkage: float = 0.24
    story_potential: float = 0.20
    source_availability: float = 0.20
    risk_safety: float = 0.14


@dataclass(frozen=True)
class CollectionConfig:
    enabled: bool = True
    interval_minutes: int = 60
    timezone: str = "Asia/Seoul"
    output_dir: Path = Path("outputs/collections")


@dataclass(frozen=True)
class AppConfig:
    language: str = "ko"
    output_dir: Path = Path("outputs")
    default_as_of: str = ""
    policy: PolicyConfig = PolicyConfig()
    scoring_weights: ScoringWeights = ScoringWeights()
    collection: CollectionConfig = CollectionConfig()


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path else Path(__file__).resolve().parents[2] / "config" / "default.toml"
    if not config_path.exists():
        return AppConfig()
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    policy = PolicyConfig(**data.get("policy", {}))
    weights = ScoringWeights(**data.get("scoring", {}).get("weights", {}))
    collection_data = data.get("collection", {})
    collection = CollectionConfig(
        enabled=collection_data.get("enabled", True),
        interval_minutes=collection_data.get("interval_minutes", 60),
        timezone=collection_data.get("timezone", "Asia/Seoul"),
        output_dir=Path(collection_data.get("output_dir", "outputs/collections")),
    )
    return AppConfig(
        language=project.get("language", "ko"),
        output_dir=Path(project.get("output_dir", "outputs")),
        default_as_of=project.get("default_as_of", ""),
        policy=policy,
        scoring_weights=weights,
        collection=collection,
    )
