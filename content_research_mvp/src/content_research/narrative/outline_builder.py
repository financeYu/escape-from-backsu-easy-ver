"""Narrative outline builder."""

from __future__ import annotations

from content_research.models import EvidenceCard, NarrativeOutline


def build_outline(topic: str, evidence_cards: list[EvidenceCard]) -> NarrativeOutline:
    source_count = len(evidence_cards)
    topic_with_subject = _with_subject_particle(topic)
    return NarrativeOutline(
        hook=f"{topic_with_subject} 지금 물가, 금리, 산업, 생활비 이야기로 어떻게 이어질까?",
        background=f"이 주제는 확인 가능한 근거 자료 {source_count}개를 중심으로 배경을 설명합니다.",
        structure="핵심 계기, 경제 경로, 시청자 생활 영향 순서로 정리합니다.",
        issues="확인된 사실과 해석이 필요한 부분을 분리하고, 복수 관점이 있으면 함께 제시합니다.",
        twist="하나의 원인으로 모든 결과를 설명하지 않고 기간, 정책 대응, 시장 반응을 나눠 봅니다.",
        impact="개인, 기업, 정부, 시장에 미칠 수 있는 영향을 각각 구분합니다.",
        conclusion="결론은 행동 지시가 아니라 구조 이해와 다음 확인 지표로 마무리합니다.",
    )


def _with_subject_particle(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return text
    return f"{stripped}{'은' if _has_final_consonant(stripped[-1]) else '는'}"


def _has_final_consonant(char: str) -> bool:
    codepoint = ord(char)
    if not 0xAC00 <= codepoint <= 0xD7A3:
        return False
    return (codepoint - 0xAC00) % 28 != 0
