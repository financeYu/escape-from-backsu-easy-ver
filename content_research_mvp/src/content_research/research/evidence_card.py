"""EvidenceCard helpers."""

from __future__ import annotations

from content_research.models import ClaimStrength, EvidenceCard, NumericFact, SourceRef


def build_evidence_card(
    *,
    claim: str,
    summary_ko: str,
    sources: list[SourceRef],
    strength: ClaimStrength = ClaimStrength.VERIFIED,
    numeric_facts: list[NumericFact] | None = None,
    caveats: list[str] | None = None,
    tags: list[str] | None = None,
) -> EvidenceCard:
    card = EvidenceCard(
        claim=claim,
        summary_ko=summary_ko,
        strength=strength,
        sources=sources,
        numeric_facts=numeric_facts or [],
        caveats=caveats or [],
        tags=tags or [],
    )
    card.validate()
    return card


def validate_evidence_cards(cards: list[EvidenceCard]) -> list[str]:
    errors: list[str] = []
    for index, card in enumerate(cards, start=1):
        try:
            card.validate()
        except ValueError as exc:
            errors.append(f"card {index}: {exc}")
    return errors

