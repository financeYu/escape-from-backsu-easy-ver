from content_research.models import (
    ResearchPriorityCandidate,
    ResearchPriorityLevel,
    ResearchPrioritySignals,
    RiskLevel,
)
from content_research.research.priority import assess_research_priority, rank_research_priorities


def test_assess_research_priority_marks_strong_candidate_high():
    candidate = ResearchPriorityCandidate(
        issue="Central bank rate decision",
        why_now="A new policy decision was announced today.",
        core_question="Why did the central bank change its guidance?",
        source_notes=["central bank statement", "inflation data"],
        signals=ResearchPrioritySignals(
            social_economic_impact=9,
            timeliness=9,
            breadth=8,
            explanation_need=8,
            korea_relevance=7,
            source_availability=9,
            fact_checkability=9,
            neutrality_safety=8,
            investment_advice_safety=8,
            trigger_clarity=9,
            structural_meaning=8,
        ),
    )

    assessment = assess_research_priority(candidate)

    assert assessment.research_priority is ResearchPriorityLevel.HIGH
    assert assessment.source_risk is RiskLevel.LOW
    assert assessment.wording_risk is RiskLevel.LOW
    assert assessment.next_step == "send_to_fact_verification"


def test_assess_research_priority_downgrades_weak_sources():
    candidate = ResearchPriorityCandidate(
        issue="Unconfirmed acquisition rumor",
        why_now="Several unnamed reports mention talks.",
        core_question="Is a deal actually happening?",
        source_notes=["unnamed media reports"],
        risk_notes="Mostly unnamed sources.",
        signals=ResearchPrioritySignals(
            social_economic_impact=8,
            timeliness=9,
            breadth=7,
            explanation_need=7,
            korea_relevance=6,
            source_availability=2,
            fact_checkability=3,
            neutrality_safety=7,
            investment_advice_safety=5,
            trigger_clarity=3,
            structural_meaning=6,
        ),
    )

    assessment = assess_research_priority(candidate)

    assert assessment.research_priority is ResearchPriorityLevel.LOW
    assert assessment.source_risk is RiskLevel.HIGH
    assert assessment.next_step == "collect_primary_sources_before_brief"


def test_rank_research_priorities_orders_and_ranks_candidates():
    strong = ResearchPriorityCandidate(
        issue="Supply chain export controls",
        why_now="New official rules were released.",
        core_question="Which industries are affected?",
        source_notes=["official rule", "company disclosure"],
        signals=ResearchPrioritySignals(8, 8, 8, 8, 8, 8, 8, 8, 9, 9, 8),
    )
    medium = ResearchPriorityCandidate(
        issue="Narrow company earnings",
        why_now="Quarterly earnings were released.",
        core_question="Does this show a broader consumption change?",
        source_notes=["company filing"],
        signals=ResearchPrioritySignals(5, 6, 4, 5, 5, 8, 8, 8, 8, 7, 4),
    )

    assessments = rank_research_priorities([medium, strong])

    assert [assessment.rank for assessment in assessments] == [1, 2]
    assert assessments[0].issue == "Supply chain export controls"
    assert assessments[0].research_priority is ResearchPriorityLevel.HIGH
