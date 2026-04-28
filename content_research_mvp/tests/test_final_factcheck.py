from content_research.models import (
    FactVerificationNote,
    FinalFactcheckStatus,
    VerificationStatus,
)
from content_research.review.final_factcheck import review_final_brief


def test_review_final_brief_ready_when_sources_and_notes_are_clean():
    report = review_final_brief(
        "### 1. 이슈명\n정책 변화\n\n### 8. 출처 목록\n- Central Bank statement",
        [
            FactVerificationNote(
                claim_or_number="정책 변화",
                status=VerificationStatus.CONFIRMED,
                unit_and_date="",
                source="Central Bank",
                note="confirmed",
            )
        ],
    )

    assert report.status is FinalFactcheckStatus.READY
    assert report.findings == []


def test_review_final_brief_blocks_do_not_use_claims():
    report = review_final_brief(
        "### 1. 이슈명\n출처\nUnsupported claim",
        [
            FactVerificationNote(
                claim_or_number="Unsupported claim",
                status=VerificationStatus.DO_NOT_USE,
                unit_and_date="",
                source="",
                note="missing source",
            )
        ],
    )

    assert report.status is FinalFactcheckStatus.SOURCE_MORE_BEFORE_DELIVERY
    assert report.findings[0].issue == "do_not_use_claim_present"


def test_review_final_brief_flags_investment_and_production_language():
    report = review_final_brief("출처 목록\n매수 관점의 제목 후보")

    assert report.status is FinalFactcheckStatus.REVISE_BEFORE_DELIVERY
    assert {finding.issue for finding in report.findings} >= {
        "investment_advice_like_wording",
        "production_element_in_research_brief",
    }
