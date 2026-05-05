"""Risk report builder."""

from __future__ import annotations

from content_research.models import EvidenceCard, RiskFinding, RiskLevel


FORBIDDEN_PHRASES = (
    "무조건 오른다",
    "확정",
    "매수",
    "매도",
    "대박",
)


def build_risk_report(cards: list[EvidenceCard], script_text: str = "") -> list[RiskFinding]:
    findings: list[RiskFinding] = []
    for card in cards:
        try:
            card.validate()
        except ValueError as exc:
            findings.append(
                RiskFinding(
                    item=card.claim or "EvidenceCard",
                    problem_type="validation",
                    risk_level=RiskLevel.HIGH,
                    recommendation=str(exc),
                )
            )
    for phrase in FORBIDDEN_PHRASES:
        if phrase in script_text:
            findings.append(
                RiskFinding(
                    item=phrase,
                    problem_type="investment_or_overclaim_language",
                    risk_level=RiskLevel.HIGH,
                    recommendation="투자 조언이나 단정 표현으로 읽힐 수 있으므로 가능성 중심 표현으로 바꾸세요.",
                )
            )
    if not findings:
        findings.append(
            RiskFinding(
                item="전체",
                problem_type="review_status",
                risk_level=RiskLevel.LOW,
                recommendation="자동 점검에서 고위험 표현은 발견되지 않았습니다. 최종 출처 대조는 사람이 확인하세요.",
            )
        )
    return findings
