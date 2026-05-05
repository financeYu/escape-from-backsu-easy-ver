"""PPT outline builder."""

from __future__ import annotations

from content_research.models import NarrativeOutline, SlidePlan


def build_ppt_outline(outline: NarrativeOutline) -> list[SlidePlan]:
    sections = [
        ("오늘의 질문", outline.hook, "핵심 질문과 관련 지표를 한 화면에 배치", outline.hook),
        ("문제 제기", outline.hook, "시청자 생활과 연결되는 질문 카드", outline.hook),
        ("왜 지금인가", outline.background, "최근 계기와 기준일 타임라인", outline.background),
        ("배경 맥락", outline.background, "정책·시장·산업 배경을 나눈 3열 표", outline.background),
        ("기본 구조", outline.structure, "원인에서 시장 반응까지 이어지는 흐름도", outline.structure),
        ("경제로 이어지는 경로", outline.structure, "물가·금리·환율·산업 연결 경로", outline.structure),
        ("핵심 데이터 1", outline.structure, "공식 통계 수치를 재시각화한 선그래프", outline.structure),
        ("핵심 데이터 2", outline.structure, "기준일과 단위가 보이는 비교표", outline.structure),
        ("주요 보도 정리", outline.issues, "보도별 확인된 사실과 해석 분리표", outline.issues),
        ("쟁점 정리", outline.issues, "찬반 또는 복수 관점 비교표", outline.issues),
        ("확실한 사실", outline.issues, "확인된 사실만 모은 체크리스트", outline.issues),
        ("아직 불확실한 부분", outline.issues, "추가 확인이 필요한 주장과 자료 공백", outline.issues),
        ("흔한 오해", outline.twist, "오해와 확인된 사실 비교", outline.twist),
        ("반전 포인트", outline.twist, "단일 원인이 아닌 복수 요인 구조", outline.twist),
        ("생활 영향", outline.impact, "가계 비용과 소비 심리 영향 지도", outline.impact),
        ("기업 영향", outline.impact, "업종별 비용·수요 영향 매트릭스", outline.impact),
        ("정부·시장 영향", outline.impact, "정책 대응과 시장 지표 체크포인트", outline.impact),
        ("앞으로 볼 지표", outline.conclusion, "추적할 지표와 발표 일정 체크리스트", outline.conclusion),
        ("마무리 체크포인트", outline.conclusion, "추적할 지표와 다음 질문 체크리스트", outline.conclusion),
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
