import pytest

from content_research.models import ClaimStrength, EvidenceCard, NumericFact, SourceKind, SourceRef
from content_research.research.evidence_card import build_evidence_card, validate_evidence_cards


def test_build_evidence_card_accepts_valid_numeric_fact():
    source = SourceRef(
        title="통계 발표",
        publisher="공식 기관",
        url="https://example.com/stat",
        kind=SourceKind.STATISTICS,
    )
    fact = NumericFact(
        label="물가 상승률",
        value="2.1",
        unit="%",
        as_of="2026-03",
        source_url="https://example.com/stat",
    )

    card = build_evidence_card(
        claim="물가 상승률은 기준일과 출처를 함께 제시해야 한다.",
        summary_ko="숫자는 단위, 기준일, 출처가 필요하다.",
        sources=[source],
        numeric_facts=[fact],
    )

    assert card.numeric_facts[0].unit == "%"


def test_unverified_card_requires_caveat():
    source = SourceRef(
        title="보도",
        publisher="언론사",
        url="https://example.com/news",
        kind=SourceKind.NEWS,
    )

    with pytest.raises(ValueError, match="require caveats"):
        build_evidence_card(
            claim="아직 확인되지 않은 주장",
            summary_ko="주의가 필요한 주장",
            sources=[source],
            strength=ClaimStrength.UNVERIFIED,
        )


def test_validate_evidence_cards_returns_errors():
    source = SourceRef(
        title="Bad URL",
        publisher="공식 기관",
        url="not-a-url",
        kind=SourceKind.OFFICIAL,
    )
    bad_card = EvidenceCard(
        claim="주장",
        summary_ko="요약",
        strength=ClaimStrength.VERIFIED,
        sources=[source],
    )

    errors = validate_evidence_cards([bad_card])

    assert errors
    assert "source url" in errors[0]
