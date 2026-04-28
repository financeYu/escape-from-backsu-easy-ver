"""Narrative outline builder."""

from __future__ import annotations

from content_research.models import EvidenceCard, NarrativeOutline


def build_outline(topic: str, evidence_cards: list[EvidenceCard]) -> NarrativeOutline:
    source_count = len(evidence_cards)
    return NarrativeOutline(
        hook=f"{topic}은 왜 지금 우리의 물가, 환율, 산업 이야기로 이어질까요?",
        background=f"이 주제는 최근 이슈를 출발점으로 삼되, 확인된 자료 {source_count}개를 중심으로 배경을 설명합니다.",
        structure="핵심 구조는 사건 -> 경제 경로 -> 시청자 생활 영향 순서로 정리합니다.",
        issues="찬반 또는 복수 관점이 있는 지점은 원문 자료와 해석을 분리해 보여줍니다.",
        twist="흔한 오해는 단일 원인으로 모든 결과를 설명하려는 태도입니다. 실제 영향은 기간, 정책 대응, 시장 반응에 따라 달라집니다.",
        impact="개인, 기업, 정부, 시장에 미칠 수 있는 영향을 각각 구분해 설명합니다.",
        conclusion="결론은 공포 조장이 아니라 구조 이해입니다. 무엇을 계속 확인해야 하는지 체크포인트로 마무리합니다.",
    )

