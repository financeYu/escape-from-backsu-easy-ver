from content_research.config import ScoringWeights
from content_research.scoring.channel_fit_score import calculate_channel_fit_score, clamp_score


def test_clamp_score_limits_values_to_zero_and_ten():
    assert clamp_score(-1) == 0
    assert clamp_score(12) == 10
    assert clamp_score(6.5) == 6.5


def test_calculate_channel_fit_score_uses_weights():
    score = calculate_channel_fit_score(
        popularity=10,
        economic_linkage=10,
        story_potential=0,
        source_availability=0,
        risk_safety=10,
        weights=ScoringWeights(
            popularity=1,
            economic_linkage=1,
            story_potential=1,
            source_availability=1,
            risk_safety=1,
        ),
        rationale="테스트",
    )

    assert score.total == 6.0
    assert score.rationale == "테스트"

