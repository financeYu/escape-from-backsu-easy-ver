from content_research.models import (
    ContextConfidence,
    ContextNote,
    FactVerificationNote,
    VerificationStatus,
)
from content_research.research.brief_structuring import build_research_brief_draft


def test_build_research_brief_draft_separates_facts_and_uncertainty():
    draft = build_research_brief_draft(
        issue="정책 변화",
        why_matters="가계와 기업의 차입 비용에 영향을 준다.",
        verification_notes=[
            FactVerificationNote(
                claim_or_number="정책금리 변경",
                status=VerificationStatus.CONFIRMED,
                unit_and_date="4.5 %, as of 2026-04-27",
                source="Central Bank statement",
                note="confirmed",
            ),
            FactVerificationNote(
                claim_or_number="추가 인상 가능성",
                status=VerificationStatus.UNCERTAIN,
                unit_and_date="",
                source="Analyst note",
                note="scenario only",
            ),
        ],
        context_notes=[
            ContextNote(
                context_item="전달 경로",
                explanation="금리 변화는 대출, 환율, 소비 심리에 영향을 줄 수 있다.",
                confidence=ContextConfidence.HIGH,
                source_or_basis="standard macro channel",
                final_brief_use="background",
            )
        ],
    )

    assert draft.verified_facts == ["확인: 정책금리 변경 (4.5 %, as of 2026-04-27)"]
    assert any("불확실" in item for item in draft.watch_points)
    assert "Central Bank statement" in draft.sources


def test_research_brief_draft_renders_korean_sections():
    draft = build_research_brief_draft(
        issue="공급망 규제",
        why_matters="산업 비용과 교역 구조에 영향을 준다.",
        verification_notes=[],
        sources=["Official release"],
        final_check="ready",
    )

    markdown = draft.to_markdown()

    assert "### 1. 이슈명" in markdown
    assert "### 8. 출처 목록" in markdown
    assert "Official release" in markdown
