"""PPT outline builder."""

from __future__ import annotations

from content_research.models import NarrativeOutline, SlidePlan


def build_ppt_outline(outline: NarrativeOutline) -> list[SlidePlan]:
    sections = [
        ("오늘의 질문", outline.hook, "질문형 타이틀과 간단한 아이콘", outline.hook),
        ("왜 지금인가", outline.background, "타임라인", outline.background),
        ("경제로 연결되는 경로", outline.structure, "3단계 흐름도", outline.structure),
        ("쟁점 정리", outline.issues, "찬반 또는 관점 비교표", outline.issues),
        ("흔한 오해", outline.twist, "오해와 실제 구조 비교", outline.twist),
        ("생활 영향", outline.impact, "개인·기업·정부·시장 4분면", outline.impact),
        ("마무리 체크포인트", outline.conclusion, "체크리스트", outline.conclusion),
    ]
    return [
        SlidePlan(
            number=index,
            title=title,
            core_message=message,
            visual_idea=visual,
            speaker_note=note,
            source_refs=[],
        )
        for index, (title, message, visual, note) in enumerate(sections, start=1)
    ]

