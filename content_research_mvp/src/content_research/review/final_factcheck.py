"""Final delivery gate for Research Master briefs."""

from __future__ import annotations

from content_research.models import (
    FactVerificationNote,
    FinalFactcheckFinding,
    FinalFactcheckReport,
    FinalFactcheckStatus,
    RiskLevel,
    VerificationStatus,
)


INVESTMENT_ADVICE_PHRASES = (
    "매수",
    "매도",
    "목표가",
    "투자 추천",
    "수익 보장",
    "buy signal",
    "sell signal",
)

DEFINITIVE_FORECAST_PHRASES = (
    "반드시",
    "무조건",
    "확실히",
    "필연적으로",
    "will definitely",
    "guaranteed",
    "inevitable",
)

PRODUCTION_ELEMENT_PHRASES = (
    "썸네일",
    "제목 후보",
    "오프닝 멘트",
    "촬영 스크립트",
    "shorts",
    "thumbnail",
)


def review_final_brief(
    brief_text: str,
    verification_notes: list[FactVerificationNote] | None = None,
) -> FinalFactcheckReport:
    findings: list[FinalFactcheckFinding] = []
    text = brief_text.strip()
    notes = verification_notes or []

    if not text:
        findings.append(
            FinalFactcheckFinding(
                item="brief",
                issue="empty_brief",
                required_revision="Write a brief before final factcheck.",
                risk_level=RiskLevel.HIGH,
            )
        )

    if "출처" not in text and "source" not in text.lower():
        findings.append(
            FinalFactcheckFinding(
                item="sources",
                issue="missing_source_section",
                required_revision="Add a source list or explicit source notes before delivery.",
                risk_level=RiskLevel.HIGH,
            )
        )

    for note in notes:
        if note.status is VerificationStatus.DO_NOT_USE:
            findings.append(
                FinalFactcheckFinding(
                    item=note.claim_or_number,
                    issue="do_not_use_claim_present",
                    required_revision="Remove the claim or source more before delivery.",
                    risk_level=RiskLevel.HIGH,
                )
            )
        elif note.status is VerificationStatus.UNCERTAIN and note.claim_or_number in text:
            findings.append(
                FinalFactcheckFinding(
                    item=note.claim_or_number,
                    issue="uncertain_claim_needs_label",
                    required_revision="Label this as uncertainty or remove it from confirmed facts.",
                    risk_level=RiskLevel.MEDIUM,
                )
            )

    findings.extend(_phrase_findings(text, INVESTMENT_ADVICE_PHRASES, "investment_advice_like_wording"))
    findings.extend(_phrase_findings(text, DEFINITIVE_FORECAST_PHRASES, "definitive_forecast_wording"))
    findings.extend(_phrase_findings(text, PRODUCTION_ELEMENT_PHRASES, "production_element_in_research_brief"))

    return FinalFactcheckReport(
        status=_status_from_findings(findings),
        findings=findings,
    )


def _phrase_findings(
    text: str,
    phrases: tuple[str, ...],
    issue: str,
) -> list[FinalFactcheckFinding]:
    lowered = text.lower()
    findings: list[FinalFactcheckFinding] = []
    for phrase in phrases:
        if phrase.lower() in lowered:
            findings.append(
                FinalFactcheckFinding(
                    item=phrase,
                    issue=issue,
                    required_revision="Remove or rewrite this wording before delivery.",
                    risk_level=RiskLevel.HIGH,
                )
            )
    return findings


def _status_from_findings(findings: list[FinalFactcheckFinding]) -> FinalFactcheckStatus:
    if any(finding.issue in {"missing_source_section", "do_not_use_claim_present"} for finding in findings):
        return FinalFactcheckStatus.SOURCE_MORE_BEFORE_DELIVERY
    if any(finding.risk_level is RiskLevel.HIGH for finding in findings):
        return FinalFactcheckStatus.REVISE_BEFORE_DELIVERY
    if findings:
        return FinalFactcheckStatus.REVISE_BEFORE_DELIVERY
    return FinalFactcheckStatus.READY
