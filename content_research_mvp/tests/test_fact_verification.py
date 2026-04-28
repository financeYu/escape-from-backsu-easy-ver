from content_research.models import (
    ClaimStrength,
    EvidenceCard,
    NumericFact,
    SourceKind,
    SourceRef,
    VerificationStatus,
)
from content_research.research.fact_verification import verify_evidence_card, verify_evidence_cards


def test_verify_evidence_card_confirms_primary_source_claim_and_number():
    source = SourceRef(
        title="Policy statement",
        publisher="Central Bank",
        url="https://example.com/policy",
        kind=SourceKind.OFFICIAL,
    )
    card = EvidenceCard(
        claim="The central bank changed its policy rate.",
        summary_ko="정책금리 변경은 공식 발표로 확인된다.",
        strength=ClaimStrength.VERIFIED,
        sources=[source],
        numeric_facts=[
            NumericFact(
                label="policy rate",
                value="4.5",
                unit="%",
                as_of="2026-04-27",
                source_url="https://example.com/policy",
            )
        ],
    )

    notes = verify_evidence_card(card)

    assert notes[0].status is VerificationStatus.CONFIRMED
    assert notes[1].status is VerificationStatus.CONFIRMED
    assert notes[1].unit_and_date == "4.5 %, as of 2026-04-27"


def test_verify_evidence_card_keeps_news_only_claim_reported():
    source = SourceRef(
        title="News report",
        publisher="Major News",
        url="https://example.com/news",
        kind=SourceKind.NEWS,
    )
    card = EvidenceCard(
        claim="Officials are reported to be discussing new rules.",
        summary_ko="주요 언론 보도지만 공식 발표는 아니다.",
        strength=ClaimStrength.VERIFIED,
        sources=[source],
    )

    notes = verify_evidence_card(card)

    assert notes[0].status is VerificationStatus.REPORTED


def test_verify_evidence_cards_marks_invalid_card_do_not_use():
    bad_card = EvidenceCard(
        claim="Unsupported claim",
        summary_ko="출처가 없다.",
        strength=ClaimStrength.VERIFIED,
        sources=[],
    )

    notes = verify_evidence_cards([bad_card])

    assert notes[0].status is VerificationStatus.DO_NOT_USE
    assert "Validation failed" in notes[0].note
