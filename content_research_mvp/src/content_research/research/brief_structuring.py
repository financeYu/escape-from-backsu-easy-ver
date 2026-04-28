"""Build compact Research Master brief drafts from verified material."""

from __future__ import annotations

from content_research.models import (
    ContextNote,
    FactVerificationNote,
    ResearchBriefDraft,
    VerificationStatus,
)


def build_research_brief_draft(
    *,
    issue: str,
    why_matters: str,
    verification_notes: list[FactVerificationNote],
    context_notes: list[ContextNote] | None = None,
    summary_lines: list[str] | None = None,
    watch_points: list[str] | None = None,
    sources: list[str] | None = None,
    final_check: str = "",
) -> ResearchBriefDraft:
    if not issue.strip():
        raise ValueError("issue is required")
    if not why_matters.strip():
        raise ValueError("why_matters is required")

    context_notes = context_notes or []
    fact_lines = _fact_lines(verification_notes)
    flow_lines = _flow_lines(verification_notes)
    context_lines = _context_lines(context_notes)
    watch_lines = [*(watch_points or []), *_uncertainty_lines(verification_notes), *_low_confidence_context(context_notes)]
    source_lines = _source_lines(verification_notes, sources or [])

    return ResearchBriefDraft(
        issue=issue.strip(),
        summary_lines=_summary_lines(issue, why_matters, fact_lines, summary_lines),
        why_matters=why_matters.strip(),
        verified_facts=fact_lines,
        key_flow=flow_lines,
        context=context_lines,
        watch_points=watch_lines,
        sources=source_lines,
        final_check=final_check,
    )


def _summary_lines(
    issue: str,
    why_matters: str,
    fact_lines: list[str],
    provided: list[str] | None,
) -> list[str]:
    if provided:
        return [line.strip() for line in provided if line.strip()][:3]
    fact_summary = fact_lines[0] if fact_lines else "핵심 사실은 추가 검증이 필요합니다."
    return [
        issue.strip(),
        why_matters.strip(),
        fact_summary,
    ]


def _fact_lines(notes: list[FactVerificationNote]) -> list[str]:
    lines: list[str] = []
    for note in notes:
        if note.status is VerificationStatus.CONFIRMED:
            suffix = f" ({note.unit_and_date})" if note.unit_and_date else ""
            lines.append(f"확인: {note.claim_or_number}{suffix}")
        elif note.status is VerificationStatus.REPORTED:
            suffix = f" ({note.unit_and_date})" if note.unit_and_date else ""
            lines.append(f"보도: {note.claim_or_number}{suffix}")
        elif note.status is VerificationStatus.INTERPRETATION:
            lines.append(f"해석: {note.claim_or_number}")
    return lines


def _flow_lines(notes: list[FactVerificationNote]) -> list[str]:
    return [
        f"{note.claim_or_number}: {note.unit_and_date}"
        for note in notes
        if note.unit_and_date and note.status is not VerificationStatus.DO_NOT_USE
    ]


def _context_lines(notes: list[ContextNote]) -> list[str]:
    return [
        f"{note.context_item}: {note.explanation}"
        for note in notes
        if note.final_brief_use != "omit"
    ]


def _uncertainty_lines(notes: list[FactVerificationNote]) -> list[str]:
    return [
        f"불확실: {note.claim_or_number} - {note.note}"
        for note in notes
        if note.status is VerificationStatus.UNCERTAIN
    ]


def _low_confidence_context(notes: list[ContextNote]) -> list[str]:
    return [
        f"맥락 주의: {note.context_item} - {note.explanation}"
        for note in notes
        if note.confidence.value == "low"
    ]


def _source_lines(notes: list[FactVerificationNote], explicit_sources: list[str]) -> list[str]:
    source_lines = [source.strip() for source in explicit_sources if source.strip()]
    for note in notes:
        if note.source.strip() and note.status is not VerificationStatus.DO_NOT_USE:
            source_lines.append(note.source.strip())
    return list(dict.fromkeys(source_lines))
