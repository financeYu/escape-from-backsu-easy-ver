"""Context note builder for Research Master briefs."""

from __future__ import annotations

from content_research.models import (
    ContextConfidence,
    ContextNote,
    FactVerificationNote,
    VerificationStatus,
)


def build_context_notes(
    *,
    issue: str,
    verification_notes: list[FactVerificationNote],
    structural_background: str = "",
    korea_connection: str = "",
    common_misunderstandings: list[str] | None = None,
) -> list[ContextNote]:
    if not issue.strip():
        raise ValueError("issue is required")

    notes: list[ContextNote] = []

    if structural_background.strip():
        notes.append(
            ContextNote(
                context_item="structural_background",
                explanation=structural_background.strip(),
                confidence=ContextConfidence.MEDIUM,
                source_or_basis="user_or_research_context",
                final_brief_use="background",
            )
        )

    if korea_connection.strip():
        notes.append(
            ContextNote(
                context_item="korea_connection",
                explanation=korea_connection.strip(),
                confidence=ContextConfidence.MEDIUM,
                source_or_basis="clear_material_link_required",
                final_brief_use="core_fact_if_verified",
            )
        )

    notes.extend(_notes_from_verification(verification_notes))

    for misunderstanding in common_misunderstandings or []:
        if not misunderstanding.strip():
            continue
        notes.append(
            ContextNote(
                context_item="common_misunderstanding",
                explanation=misunderstanding.strip(),
                confidence=ContextConfidence.MEDIUM,
                source_or_basis="analysis",
                final_brief_use="watch_point",
            )
        )

    return notes


def _notes_from_verification(notes: list[FactVerificationNote]) -> list[ContextNote]:
    context_notes: list[ContextNote] = []
    for note in notes:
        if note.status is VerificationStatus.DO_NOT_USE:
            continue
        if note.status is VerificationStatus.CONFIRMED:
            context_notes.append(
                ContextNote(
                    context_item="confirmed_base",
                    explanation=f"{note.claim_or_number} can anchor the brief as a verified fact.",
                    confidence=ContextConfidence.HIGH,
                    source_or_basis=note.source,
                    final_brief_use="core_fact",
                )
            )
        elif note.status is VerificationStatus.REPORTED:
            context_notes.append(
                ContextNote(
                    context_item="reported_context",
                    explanation=f"{note.claim_or_number} can be used only with reported-claim wording.",
                    confidence=ContextConfidence.MEDIUM,
                    source_or_basis=note.source,
                    final_brief_use="reported_claim",
                )
            )
        elif note.status is VerificationStatus.INTERPRETATION:
            context_notes.append(
                ContextNote(
                    context_item="interpretive_context",
                    explanation=f"{note.claim_or_number} should be separated from confirmed facts.",
                    confidence=ContextConfidence.MEDIUM,
                    source_or_basis=note.source,
                    final_brief_use="background",
                )
            )
        elif note.status is VerificationStatus.UNCERTAIN:
            context_notes.append(
                ContextNote(
                    context_item="uncertainty",
                    explanation=f"{note.claim_or_number} is not settled and belongs in watch points.",
                    confidence=ContextConfidence.LOW,
                    source_or_basis=note.source,
                    final_brief_use="watch_point",
                )
            )
    return context_notes
