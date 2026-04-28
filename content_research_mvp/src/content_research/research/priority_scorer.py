"""Internal priority scorer for normalized issue candidates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable


@dataclass(frozen=True)
class PriorityScore:
    issue_id: str
    internal_score: float
    recommendation_reason: str
    risk_flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def score_issue_priorities(
    issue_candidates: Iterable[Any],
    *,
    data_matches: Iterable[Any] | None = None,
    claims: Iterable[Any] | None = None,
    limit: int | None = None,
) -> list[PriorityScore]:
    """Score issues for internal research ordering."""

    matches_by_issue = _group_by_issue_id(data_matches or [])
    claims_by_evidence = _group_claims_by_evidence_id(claims or [])
    scores: list[PriorityScore] = []
    for issue_candidate in issue_candidates:
        issue = _as_record(issue_candidate)
        issue_id = _as_str(issue.get("issue_id"))
        if not issue_id:
            continue
        matches = matches_by_issue.get(issue_id, [])
        related_claims = _claims_for_issue(issue, claims_by_evidence)
        scores.append(_score_issue(issue, matches, related_claims))

    scores.sort(key=lambda item: (item.internal_score, item.issue_id), reverse=True)
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        scores = scores[:limit]
    return scores


def _score_issue(issue: dict[str, Any], data_matches: list[dict[str, Any]], claims: list[dict[str, Any]]) -> PriorityScore:
    text = _issue_text(issue)
    official_data_bonus = min(2.0, len(data_matches) * 1.0)
    unverified_claim_penalty = min(1.5, sum(1 for claim in claims if claim.get("needs_verification")) * 0.5)
    risk_flags = _risk_flags(text, claims)
    risk_penalty = 2.0 if "investment_advice_risk" in risk_flags else 0.0
    risk_penalty += 1.5 if "alarmist_or_definitive_framing" in risk_flags else 0.0

    score = (
        _economic_impact(text)
        + _internationality(text)
        + _korea_connection(text)
        + _explanation_need(text)
        + official_data_bonus
        - unverified_claim_penalty
        - risk_penalty
    )
    score = round(max(0.0, min(10.0, score)), 2)
    return PriorityScore(
        issue_id=_as_str(issue.get("issue_id")),
        internal_score=score,
        recommendation_reason=_recommendation_reason(score, data_matches, risk_flags),
        risk_flags=risk_flags,
    )


def _economic_impact(text: str) -> float:
    keywords = (
        "rate",
        "inflation",
        "jobs",
        "employment",
        "oil",
        "energy",
        "trade",
        "export",
        "tariff",
        "supply chain",
        "market",
        "economy",
        "gdp",
        "금리",
        "물가",
        "고용",
        "실업",
        "유가",
        "원유",
        "에너지",
        "무역",
        "수출",
        "수입",
        "관세",
        "공급망",
        "시장",
        "경제",
        "경기",
    )
    return 2.0 if _contains_any(text, keywords) else 0.8


def _internationality(text: str) -> float:
    keywords = (
        "global",
        "world",
        "international",
        "us",
        "china",
        "europe",
        "japan",
        "fed",
        "opec",
        "국제",
        "세계",
        "미국",
        "중국",
        "유럽",
        "일본",
        "연준",
        "오펙",
        "지정학",
    )
    return 1.5 if _contains_any(text, keywords) else 0.5


def _korea_connection(text: str) -> float:
    keywords = ("korea", "korean", "seoul", "won", "kospi", "한국", "국내", "서울", "원화", "코스피")
    return 1.5 if _contains_any(text, keywords) else 0.4


def _explanation_need(text: str) -> float:
    keywords = (
        "rate",
        "inflation",
        "supply chain",
        "export control",
        "sanction",
        "energy",
        "employment",
        "tariff",
        "central bank",
        "금리",
        "물가",
        "공급망",
        "수출통제",
        "제재",
        "에너지",
        "고용",
        "관세",
        "중앙은행",
        "설명",
    )
    return 2.0 if _contains_any(text, keywords) else 1.0


def _risk_flags(text: str, claims: list[dict[str, Any]]) -> list[str]:
    flags: list[str] = []
    if _contains_any(
        text,
        (
            "buy",
            "sell",
            "target price",
            "investment advice",
            "stock pick",
            "매수",
            "매도",
            "목표가",
            "투자조언",
            "투자 조언",
            "종목 추천",
        ),
    ):
        flags.append("investment_advice_risk")
    if _contains_any(
        text,
        (
            "collapse",
            "crash",
            "disaster",
            "certain",
            "guaranteed",
            "panic",
            "붕괴",
            "폭락",
            "재앙",
            "확정",
            "보장",
            "패닉",
            "공포",
        ),
    ):
        flags.append("alarmist_or_definitive_framing")
    if any(claim.get("needs_verification") for claim in claims):
        flags.append("unverified_claims")
    return flags


def _recommendation_reason(score: float, data_matches: list[dict[str, Any]], risk_flags: list[str]) -> str:
    parts: list[str] = []
    if data_matches:
        parts.append("Official data is available for verification.")
    else:
        parts.append("Official data support is not yet attached.")
    if risk_flags:
        parts.append("Use conservative wording and verify unresolved claims before briefing.")
    elif score >= 7.0:
        parts.append("Good candidate for deeper research because the issue has broad explanatory value.")
    else:
        parts.append("Keep as a watch item unless more source support appears.")
    return " ".join(parts)


def _group_by_issue_id(items: Iterable[Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        record = _as_record(item)
        issue_id = _as_str(record.get("issue_id"))
        if issue_id:
            grouped.setdefault(issue_id, []).append(record)
    return grouped


def _group_claims_by_evidence_id(items: Iterable[Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        record = _as_record(item)
        evidence_id = _as_str(record.get("evidence_id"))
        if evidence_id:
            grouped.setdefault(evidence_id, []).append(record)
    return grouped


def _claims_for_issue(issue: dict[str, Any], claims_by_evidence: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    related_ids = issue.get("related_evidence_ids", [])
    if not isinstance(related_ids, list):
        return []
    claims: list[dict[str, Any]] = []
    for evidence_id in related_ids:
        claims.extend(claims_by_evidence.get(_as_str(evidence_id), []))
    return claims


def _issue_text(issue: dict[str, Any]) -> str:
    titles = issue.get("representative_titles", [])
    if not isinstance(titles, list):
        titles = []
    tags = issue.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    parts = [
        _as_str(issue.get("issue_name")),
        _as_str(issue.get("trend_reason")),
        " ".join(_as_str(title) for title in titles),
        " ".join(_as_str(tag) for tag in tags),
    ]
    return " ".join(parts).casefold()


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(_contains_keyword(text, keyword) for keyword in keywords)


def _contains_keyword(text: str, keyword: str) -> bool:
    normalized = keyword.casefold()
    if re.fullmatch(r"[0-9a-z ]+", normalized):
        pattern = rf"(?<![0-9a-z]){re.escape(normalized)}(?![0-9a-z])"
        return re.search(pattern, text) is not None
    return normalized in text


def _as_record(candidate: Any) -> dict[str, Any]:
    if isinstance(candidate, dict):
        return candidate
    to_dict = getattr(candidate, "to_dict", None)
    if callable(to_dict):
        value = to_dict()
        if isinstance(value, dict):
            return value
    return {}


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
