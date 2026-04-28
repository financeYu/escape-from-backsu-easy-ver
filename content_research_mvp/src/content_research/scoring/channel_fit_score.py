"""Channel-fit scoring."""

from __future__ import annotations

from dataclasses import asdict

from content_research.config import ScoringWeights
from content_research.models import ChannelFitScore


def clamp_score(value: float) -> float:
    return max(0.0, min(10.0, float(value)))


def calculate_channel_fit_score(
    *,
    popularity: float,
    economic_linkage: float,
    story_potential: float,
    source_availability: float,
    risk_safety: float,
    weights: ScoringWeights | None = None,
    rationale: str = "",
) -> ChannelFitScore:
    weights = weights or ScoringWeights()
    values = {
        "popularity": clamp_score(popularity),
        "economic_linkage": clamp_score(economic_linkage),
        "story_potential": clamp_score(story_potential),
        "source_availability": clamp_score(source_availability),
        "risk_safety": clamp_score(risk_safety),
    }
    weight_values = asdict(weights)
    total_weight = sum(weight_values.values())
    weighted_total = sum(values[key] * weight_values[key] for key in values) / total_weight
    return ChannelFitScore(
        **values,
        total=round(weighted_total, 2),
        rationale=rationale or "대중성, 경제 연결성, 이야기성, 자료성, 리스크 안전성을 가중 평균했습니다.",
    )

