"""Issue candidate normalization for the Research Master workflow."""

from __future__ import annotations

from collections.abc import Iterable

from content_research.models import IssueCollectionCandidate


DEFAULT_LIMIT = 8

HIGH_RISK_MARKERS = (
    "rumor only",
    "viral only",
    "unverified social",
    "investment call",
)


def build_issue_candidate(
    *,
    candidate_issue: str,
    current_trigger: str,
    why_it_may_matter: str,
    source_types_needed: list[str],
    uncertainty_or_risk: str = "",
) -> IssueCollectionCandidate:
    candidate = IssueCollectionCandidate(
        candidate_issue=_clean(candidate_issue),
        current_trigger=_clean(current_trigger),
        why_it_may_matter=_clean(why_it_may_matter),
        source_types_needed=_clean_list(source_types_needed),
        uncertainty_or_risk=_clean(uncertainty_or_risk),
    )
    _validate_candidate(candidate)
    return candidate


def normalize_issue_candidates(
    candidates: Iterable[IssueCollectionCandidate],
    *,
    limit: int = DEFAULT_LIMIT,
    allow_high_risk: bool = False,
) -> list[IssueCollectionCandidate]:
    if limit <= 0:
        raise ValueError("limit must be positive")

    normalized: list[IssueCollectionCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            cleaned = build_issue_candidate(
                candidate_issue=candidate.candidate_issue,
                current_trigger=candidate.current_trigger,
                why_it_may_matter=candidate.why_it_may_matter,
                source_types_needed=candidate.source_types_needed,
                uncertainty_or_risk=candidate.uncertainty_or_risk,
            )
        except ValueError:
            continue

        key = cleaned.candidate_issue.casefold()
        if key in seen:
            continue
        if not allow_high_risk and _is_high_risk(cleaned):
            continue
        seen.add(key)
        normalized.append(cleaned)
        if len(normalized) >= limit:
            break

    return normalized


def _validate_candidate(candidate: IssueCollectionCandidate) -> None:
    if not candidate.candidate_issue:
        raise ValueError("candidate_issue is required")
    if not candidate.current_trigger:
        raise ValueError("current_trigger is required")
    if not candidate.why_it_may_matter:
        raise ValueError("why_it_may_matter is required")
    if not candidate.source_types_needed:
        raise ValueError("source_types_needed is required")


def _is_high_risk(candidate: IssueCollectionCandidate) -> bool:
    risk = candidate.uncertainty_or_risk.casefold()
    return any(marker in risk for marker in HIGH_RISK_MARKERS)


def _clean(value: str) -> str:
    return " ".join(value.strip().split())


def _clean_list(values: list[str]) -> list[str]:
    cleaned = [_clean(value) for value in values]
    return list(dict.fromkeys(value for value in cleaned if value))
