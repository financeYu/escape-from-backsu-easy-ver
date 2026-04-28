"""Korean shooting script builder."""

from __future__ import annotations

from content_research.models import ScriptSection, SlidePlan


def build_script(slides: list[SlidePlan]) -> list[ScriptSection]:
    script: list[ScriptSection] = []
    for slide in slides:
        script.append(
            ScriptSection(
                slide_number=slide.number,
                section=slide.title,
                narration=(
                    f"{slide.speaker_note} "
                    "여기서는 단정 대신 확인된 자료와 가능한 경로를 나누어 보겠습니다."
                ),
                caption=slide.core_message[:80],
                source_refs=slide.source_refs,
            )
        )
    return script

