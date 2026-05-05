"""Korean shooting script builder."""

from __future__ import annotations

from content_research.models import ScriptSection, SlidePlan


def build_script(slides: list[SlidePlan]) -> list[ScriptSection]:
    script: list[ScriptSection] = []
    for slide in slides:
        narration = _narration_for_slide(slide)
        script.append(
            ScriptSection(
                slide_number=slide.number,
                section=slide.title,
                narration=narration,
                caption=_caption_for_slide(slide),
                source_refs=slide.source_refs,
            )
        )
    return script


def _narration_for_slide(slide: SlidePlan) -> str:
    source_note = _source_note(slide)
    title = slide.title
    if any(keyword in title for keyword in ("오늘의 질문", "문제 제기")):
        return (
            f"{slide.speaker_note} "
            "먼저 오늘의 질문을 생활비와 시장 지표로 좁혀 보겠습니다. "
            f"아직 결론을 정하지 않고, 확인 가능한 자료부터 따라가겠습니다.{source_note}"
        )
    if any(keyword in title for keyword in ("왜 지금인가", "배경")):
        return (
            f"{slide.speaker_note} "
            "이 대목에서는 언제 무슨 계기가 있었는지, 그리고 그 계기가 왜 지금 다시 중요해졌는지를 나눠 설명합니다. "
            f"날짜가 있는 정보는 기준일을 함께 말합니다.{source_note}"
        )
    if any(keyword in title for keyword in ("구조", "경로")):
        return (
            f"{slide.speaker_note} "
            "여기서는 사건 하나를 바로 결론으로 연결하지 않고, 가격과 정책, 기업 비용, 소비자 체감으로 이어지는 경로를 단계별로 보겠습니다. "
            f"원인과 결과가 불분명한 부분은 가능성으로 낮춰 말합니다.{source_note}"
        )
    if "데이터" in title:
        return (
            f"{slide.speaker_note} "
            "숫자는 단위와 기준일을 붙여 읽고, 공식 통계와 보도 해석을 섞지 않겠습니다. "
            f"그래프는 방향보다 기준과 출처를 먼저 확인하는 방식으로 설명합니다.{source_note}"
        )
    if any(keyword in title for keyword in ("보도", "쟁점", "확실한 사실", "불확실")):
        return (
            f"{slide.speaker_note} "
            "확인된 사실, 보도된 주장, 해석이 필요한 부분을 분리하겠습니다. "
            f"서로 다른 관점이 있는 경우 한쪽 결론으로 밀지 않고 쟁점으로 남겨 둡니다.{source_note}"
        )
    if any(keyword in title for keyword in ("오해", "반전")):
        return (
            f"{slide.speaker_note} "
            "흔한 오해를 하나 짚고, 실제로는 여러 요인이 함께 작동할 수 있다는 점을 설명합니다. "
            f"단정적인 미래 예측 대신 확인해야 할 조건을 남깁니다.{source_note}"
        )
    if "영향" in title:
        return (
            f"{slide.speaker_note} "
            "영향은 개인, 기업, 정부, 시장을 나눠 보겠습니다. "
            f"어느 한 집단에 책임을 몰아가기보다 비용과 선택지가 어떻게 달라지는지에 집중합니다.{source_note}"
        )
    if any(keyword in title for keyword in ("앞으로", "마무리", "체크포인트")):
        return (
            f"{slide.speaker_note} "
            "마지막으로 오늘 확인한 사실과 아직 남은 질문을 분리합니다. "
            f"결론은 행동 지시가 아니라 다음에 볼 지표를 정리하는 것으로 마무리합니다.{source_note}"
        )
    return (
        f"{slide.speaker_note} "
        f"이 부분은 확인된 자료와 아직 확인이 필요한 부분을 나눠 설명합니다.{source_note}"
    )


def _caption_for_slide(slide: SlidePlan) -> str:
    return slide.core_message[:80]


def _source_note(slide: SlidePlan) -> str:
    if not slide.source_refs:
        return ""
    return " 화면 하단에는 이번 슬라이드에 직접 쓰는 출처를 함께 표시합니다."
