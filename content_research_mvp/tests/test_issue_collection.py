import pytest

from content_research.models import IssueCollectionCandidate
from content_research.research.issue_collection import build_issue_candidate, normalize_issue_candidates


def test_build_issue_candidate_cleans_and_validates_fields():
    candidate = build_issue_candidate(
        candidate_issue="  Central bank decision  ",
        current_trigger="  New statement released  ",
        why_it_may_matter="  Affects borrowing costs  ",
        source_types_needed=[" official statement ", " official statement ", "inflation data"],
    )

    assert candidate.candidate_issue == "Central bank decision"
    assert candidate.source_types_needed == ["official statement", "inflation data"]


def test_build_issue_candidate_requires_sources():
    with pytest.raises(ValueError, match="source_types_needed"):
        build_issue_candidate(
            candidate_issue="Issue",
            current_trigger="Trigger",
            why_it_may_matter="Impact",
            source_types_needed=[],
        )


def test_normalize_issue_candidates_dedupes_and_filters_high_risk():
    candidates = [
        IssueCollectionCandidate(
            candidate_issue="Export controls",
            current_trigger="Official rule released",
            why_it_may_matter="Could affect supply chains",
            source_types_needed=["official rule"],
        ),
        IssueCollectionCandidate(
            candidate_issue="export controls",
            current_trigger="Duplicate",
            why_it_may_matter="Duplicate",
            source_types_needed=["news"],
        ),
        IssueCollectionCandidate(
            candidate_issue="Acquisition rumor",
            current_trigger="Social media posts",
            why_it_may_matter="Could move markets",
            source_types_needed=["news"],
            uncertainty_or_risk="rumor only",
        ),
    ]

    normalized = normalize_issue_candidates(candidates)

    assert len(normalized) == 1
    assert normalized[0].candidate_issue == "Export controls"
