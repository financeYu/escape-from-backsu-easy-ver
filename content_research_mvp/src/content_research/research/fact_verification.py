"""Core fact verification for Research Master briefs."""

from __future__ import annotations

from content_research.models import (
    ClaimStrength,
    EvidenceCard,
    FactVerificationNote,
    SourceKind,
    VerificationStatus,
)


PRIMARY_CONFIRMING_KINDS = {
    SourceKind.OFFICIAL,
    SourceKind.PRIMARY,
    SourceKind.STATISTICS,
}


def verify_evidence_card(card: EvidenceCard) -> list[FactVerificationNote]:
    """Convert one EvidenceCard into compact verification notes.

    The function does not upgrade weak material. A verified claim backed only by
    news sources is treated as reported, while official/primary/statistical
    support can be marked confirmed.
    """

    try:
        card.validate()
    except ValueError as exc:
        return [
            FactVerificationNote(
                claim_or_number=card.claim or "EvidenceCard",
                status=VerificationStatus.DO_NOT_USE,
                unit_and_date="",
                source=_source_summary(card),
                note=f"Validation failed: {exc}",
            )
        ]

    claim_status = _claim_status(card)
    notes = [
        FactVerificationNote(
            claim_or_number=card.claim,
            status=claim_status,
            unit_and_date="",
            source=_source_summary(card),
            note=_claim_note(card, claim_status),
        )
    ]

    for fact in card.numeric_facts:
        try:
            fact.validate()
        except ValueError as exc:
            notes.append(
                FactVerificationNote(
                    claim_or_number=fact.label or fact.value,
                    status=VerificationStatus.DO_NOT_USE,
                    unit_and_date="",
                    source=fact.source_url,
                    note=f"Numeric fact validation failed: {exc}",
                )
            )
            continue

        notes.append(
            FactVerificationNote(
                claim_or_number=fact.label or f"{fact.value} {fact.unit}",
                status=_numeric_fact_status(card, claim_status),
                unit_and_date=f"{fact.value} {fact.unit}, as of {fact.as_of}",
                source=fact.source_url,
                note="Use only with unit, as-of date, and source attached.",
            )
        )

    return notes


def verify_evidence_cards(cards: list[EvidenceCard]) -> list[FactVerificationNote]:
    notes: list[FactVerificationNote] = []
    for card in cards:
        notes.extend(verify_evidence_card(card))
    return notes


def _claim_status(card: EvidenceCard) -> VerificationStatus:
    if card.strength is ClaimStrength.UNVERIFIED:
        return VerificationStatus.UNCERTAIN
    if card.strength is ClaimStrength.SCENARIO:
        return VerificationStatus.UNCERTAIN
    if card.strength is ClaimStrength.INTERPRETIVE:
        return VerificationStatus.INTERPRETATION
    if any(source.kind in PRIMARY_CONFIRMING_KINDS for source in card.sources):
        return VerificationStatus.CONFIRMED
    return VerificationStatus.REPORTED


def _numeric_fact_status(card: EvidenceCard, claim_status: VerificationStatus) -> VerificationStatus:
    if any(source.kind in {SourceKind.STATISTICS, SourceKind.OFFICIAL, SourceKind.PRIMARY} for source in card.sources):
        return VerificationStatus.CONFIRMED
    if claim_status is VerificationStatus.CONFIRMED:
        return VerificationStatus.CONFIRMED
    if claim_status is VerificationStatus.INTERPRETATION:
        return VerificationStatus.REPORTED
    return claim_status


def _claim_note(card: EvidenceCard, status: VerificationStatus) -> str:
    if status is VerificationStatus.CONFIRMED:
        return "Backed by official, primary, or statistical source material."
    if status is VerificationStatus.REPORTED:
        return "Credible enough to mention as reported, not as official confirmation."
    if status is VerificationStatus.INTERPRETATION:
        return "Use as interpretation and keep separate from confirmed facts."
    return "Use only as uncertainty or scenario; do not state as settled fact."


def _source_summary(card: EvidenceCard) -> str:
    if not card.sources:
        return ""
    return "; ".join(f"{source.publisher}: {source.title} ({source.url})" for source in card.sources)
