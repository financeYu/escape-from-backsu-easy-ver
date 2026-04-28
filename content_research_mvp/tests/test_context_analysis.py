from content_research.models import (
    ContextConfidence,
    FactVerificationNote,
    VerificationStatus,
)
from content_research.research.context_analysis import build_context_notes


def test_build_context_notes_maps_verification_status_to_confidence():
    notes = build_context_notes(
        issue="금리 결정",
        verification_notes=[
            FactVerificationNote(
                claim_or_number="정책금리 변경",
                status=VerificationStatus.CONFIRMED,
                unit_and_date="4.5 %, as of 2026-04-27",
                source="Central Bank",
                note="confirmed",
            ),
            FactVerificationNote(
                claim_or_number="추가 인상 가능성",
                status=VerificationStatus.UNCERTAIN,
                unit_and_date="",
                source="Analyst note",
                note="scenario",
            ),
        ],
    )

    assert notes[0].confidence is ContextConfidence.HIGH
    assert notes[1].confidence is ContextConfidence.LOW
    assert notes[1].final_brief_use == "watch_point"


def test_build_context_notes_adds_background_and_korea_link():
    notes = build_context_notes(
        issue="수출 통제",
        verification_notes=[],
        structural_background="첨단 제조 공급망에 영향을 줄 수 있다.",
        korea_connection="한국 반도체 기업의 장비 조달과 연결된다.",
        common_misunderstandings=["정책 발표가 곧바로 모든 수출 중단을 뜻하지는 않는다."],
    )

    assert [note.context_item for note in notes] == [
        "structural_background",
        "korea_connection",
        "common_misunderstanding",
    ]
