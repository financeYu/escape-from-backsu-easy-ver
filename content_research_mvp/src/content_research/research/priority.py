"""Research-priority selection for issue candidates.

The selector ranks candidates for research brief production. It is separate
from channel-fit scoring: a candidate can be interesting for the channel but
still be a poor research target when sources are weak or wording risk is high.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from content_research.models import (
    ResearchPriorityAssessment,
    ResearchPriorityCandidate,
    ResearchPriorityLevel,
    ResearchPrioritySignals,
    ResearchPriorityWeights,
    RiskLevel,
)


def clamp_score(value: float) -> float:
    return max(0.0, min(10.0, float(value)))


def assess_research_priority(
    candidate: ResearchPriorityCandidate,
    *,
    weights: ResearchPriorityWeights | None = None,
    rank: int = 0,
) -> ResearchPriorityAssessment:
    if not candidate.issue.strip():
        raise ValueError("issue is required")
    if not candidate.why_now.strip():
        raise ValueError("why_now is required")
    if not candidate.core_question.strip():
        raise ValueError("core_question is required")

    weights = weights or ResearchPriorityWeights()
    weighted_score = _weighted_score(candidate.signals, weights)
    source_risk = _source_risk(candidate.signals)
    wording_risk = _wording_risk(candidate.signals)
    priority = _priority_level(candidate.signals, weighted_score, source_risk, wording_risk)

    return ResearchPriorityAssessment(
        rank=rank,
        issue=candidate.issue.strip(),
        research_priority=priority,
        total_score=round(weighted_score, 2),
        reason=_build_reason(candidate, priority, source_risk, wording_risk),
        source_risk=source_risk,
        wording_risk=wording_risk,
        next_step=_next_step(priority, source_risk, wording_risk),
    )


def rank_research_priorities(
    candidates: Iterable[ResearchPriorityCandidate],
    *,
    weights: ResearchPriorityWeights | None = None,
    limit: int | None = None,
) -> list[ResearchPriorityAssessment]:
    assessments = [
        assess_research_priority(candidate, weights=weights)
        for candidate in candidates
    ]
    assessments.sort(
        key=lambda assessment: (
            _priority_sort_value(assessment.research_priority),
            assessment.total_score,
            _risk_sort_value(assessment.source_risk),
            _risk_sort_value(assessment.wording_risk),
            assessment.issue,
        ),
        reverse=True,
    )

    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        assessments = assessments[:limit]

    return [
        ResearchPriorityAssessment(
            rank=index,
            issue=assessment.issue,
            research_priority=assessment.research_priority,
            total_score=assessment.total_score,
            reason=assessment.reason,
            source_risk=assessment.source_risk,
            wording_risk=assessment.wording_risk,
            next_step=assessment.next_step,
        )
        for index, assessment in enumerate(assessments, start=1)
    ]


def _weighted_score(signals: ResearchPrioritySignals, weights: ResearchPriorityWeights) -> float:
    signal_values = {
        "social_economic_impact": clamp_score(signals.social_economic_impact),
        "timeliness": clamp_score(signals.timeliness),
        "breadth": clamp_score(signals.breadth),
        "explanation_need": clamp_score(signals.explanation_need),
        "korea_relevance": clamp_score(signals.korea_relevance),
        "source_availability": clamp_score(signals.source_availability),
        "fact_checkability": clamp_score(signals.fact_checkability),
        "trigger_clarity": clamp_score(signals.trigger_clarity),
        "structural_meaning": clamp_score(signals.structural_meaning),
    }
    weight_values = asdict(weights)
    total_weight = sum(weight_values.values())
    if total_weight <= 0:
        raise ValueError("total weight must be positive")
    return sum(signal_values[key] * weight_values[key] for key in signal_values) / total_weight


def _source_risk(signals: ResearchPrioritySignals) -> RiskLevel:
    source_floor = min(clamp_score(signals.source_availability), clamp_score(signals.fact_checkability))
    if source_floor < 4:
        return RiskLevel.HIGH
    if source_floor < 7:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _wording_risk(signals: ResearchPrioritySignals) -> RiskLevel:
    wording_floor = min(
        clamp_score(signals.neutrality_safety),
        clamp_score(signals.investment_advice_safety),
    )
    if wording_floor < 4:
        return RiskLevel.HIGH
    if wording_floor < 7:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _priority_level(
    signals: ResearchPrioritySignals,
    score: float,
    source_risk: RiskLevel,
    wording_risk: RiskLevel,
) -> ResearchPriorityLevel:
    hard_floor = min(
        clamp_score(signals.source_availability),
        clamp_score(signals.fact_checkability),
        clamp_score(signals.trigger_clarity),
    )
    if hard_floor < 3.5:
        return ResearchPriorityLevel.LOW
    if source_risk is RiskLevel.HIGH or wording_risk is RiskLevel.HIGH:
        return ResearchPriorityLevel.LOW
    if score >= 7.2 and source_risk is RiskLevel.LOW and wording_risk is not RiskLevel.HIGH:
        return ResearchPriorityLevel.HIGH
    if score >= 5.2:
        return ResearchPriorityLevel.MEDIUM
    return ResearchPriorityLevel.LOW


def _build_reason(
    candidate: ResearchPriorityCandidate,
    priority: ResearchPriorityLevel,
    source_risk: RiskLevel,
    wording_risk: RiskLevel,
) -> str:
    drivers = _top_signal_names(candidate.signals, limit=3)
    reason = f"{priority.value}: strongest drivers are {', '.join(drivers)}."
    if source_risk is not RiskLevel.LOW:
        reason += f" Source risk is {source_risk.value}; verify with stronger primary or official sources."
    if wording_risk is not RiskLevel.LOW:
        reason += f" Wording risk is {wording_risk.value}; avoid partisan, alarmist, or investment-advice framing."
    if candidate.risk_notes.strip():
        reason += f" Risk note: {candidate.risk_notes.strip()}"
    return reason


def _top_signal_names(signals: ResearchPrioritySignals, *, limit: int) -> list[str]:
    values = {
        "impact": signals.social_economic_impact,
        "timeliness": signals.timeliness,
        "breadth": signals.breadth,
        "explanation_need": signals.explanation_need,
        "korea_relevance": signals.korea_relevance,
        "source_availability": signals.source_availability,
        "fact_checkability": signals.fact_checkability,
        "trigger_clarity": signals.trigger_clarity,
        "structural_meaning": signals.structural_meaning,
    }
    return [
        name
        for name, _ in sorted(
            values.items(),
            key=lambda item: (clamp_score(item[1]), item[0]),
            reverse=True,
        )[:limit]
    ]


def _next_step(priority: ResearchPriorityLevel, source_risk: RiskLevel, wording_risk: RiskLevel) -> str:
    if priority is ResearchPriorityLevel.HIGH:
        return "send_to_fact_verification"
    if source_risk is RiskLevel.HIGH:
        return "collect_primary_sources_before_brief"
    if wording_risk is RiskLevel.HIGH:
        return "rewrite_angle_before_brief"
    if priority is ResearchPriorityLevel.MEDIUM:
        return "hold_or_verify_if_capacity_allows"
    return "do_not_brief_now"


def _priority_sort_value(priority: ResearchPriorityLevel) -> int:
    return {
        ResearchPriorityLevel.HIGH: 3,
        ResearchPriorityLevel.MEDIUM: 2,
        ResearchPriorityLevel.LOW: 1,
    }[priority]


def _risk_sort_value(risk: RiskLevel) -> int:
    return {
        RiskLevel.LOW: 3,
        RiskLevel.MEDIUM: 2,
        RiskLevel.HIGH: 1,
    }[risk]
