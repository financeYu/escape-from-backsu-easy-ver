from content_research.research.priority_scorer import score_issue_priorities


def test_priority_scorer_adds_weight_for_official_data_match():
    issue = {
        "issue_id": "issue_oil",
        "issue_name": "Energy and oil prices",
        "representative_titles": ["Oil prices rise after supply warning"],
        "related_evidence_ids": ["ev_oil"],
        "tags": ["international", "economy", "industry"],
        "trend_reason": "Repeated coverage.",
    }
    data_match = {
        "issue_id": "issue_oil",
        "source_id": "eia",
        "indicator_name": "WTI crude oil spot price",
        "value": "83.10",
        "unit": "dollars per barrel",
        "confidence": 0.85,
    }

    with_data = score_issue_priorities([issue], data_matches=[data_match])[0]
    without_data = score_issue_priorities([issue])[0]

    assert with_data.issue_id == "issue_oil"
    assert with_data.internal_score > without_data.internal_score
    assert "Official data is available" in with_data.recommendation_reason
    assert with_data.risk_flags == []


def test_priority_scorer_flags_risky_framing_and_uses_conservative_reason():
    issue = {
        "issue_id": "issue_risky",
        "issue_name": "Market crash certain after rate decision",
        "representative_titles": ["Analyst says buy before guaranteed rebound"],
        "related_evidence_ids": ["ev_risky"],
        "tags": ["economy"],
        "trend_reason": "Single candidate.",
    }
    claim = {
        "evidence_id": "ev_risky",
        "needs_verification": True,
    }

    score = score_issue_priorities([issue], claims=[claim])[0]

    assert "investment_advice_risk" in score.risk_flags
    assert "alarmist_or_definitive_framing" in score.risk_flags
    assert "unverified_claims" in score.risk_flags
    assert "Use conservative wording" in score.recommendation_reason
    assert score.internal_score < 5


def test_priority_scorer_handles_korean_economy_and_risk_keywords():
    issue = {
        "issue_id": "issue_korean_risk",
        "issue_name": "한국 물가와 금리 급등 이후 시장 폭락 확정",
        "representative_titles": ["매수 추천과 목표가 제시가 이어진다"],
        "related_evidence_ids": [],
        "tags": ["한국", "경제"],
        "trend_reason": "반복 출현.",
    }

    score = score_issue_priorities([issue])[0]

    assert "investment_advice_risk" in score.risk_flags
    assert "alarmist_or_definitive_framing" in score.risk_flags
    assert "Use conservative wording" in score.recommendation_reason


def test_priority_scorer_weights_korean_economy_keywords():
    issue = {
        "issue_id": "issue_korean_macro",
        "issue_name": "한국 물가와 금리 흐름",
        "representative_titles": ["한국 소비자물가와 기준금리 부담이 커진다"],
        "related_evidence_ids": [],
        "tags": ["한국", "경제"],
        "trend_reason": "반복 출현.",
    }

    score = score_issue_priorities([issue])[0]

    assert score.internal_score >= 6.0


def test_priority_scorer_orders_by_internal_score_without_exposing_to_reason():
    issues = [
        {
            "issue_id": "issue_watch",
            "issue_name": "Company product update",
            "representative_titles": ["One company updated one product"],
            "related_evidence_ids": [],
            "tags": ["industry"],
            "trend_reason": "Single candidate.",
        },
        {
            "issue_id": "issue_trade",
            "issue_name": "Trade tariffs affect global supply chains",
            "representative_titles": ["Exports and tariffs put supply chains in focus"],
            "related_evidence_ids": [],
            "tags": ["international", "economy"],
            "trend_reason": "Repeated coverage.",
        },
    ]

    scores = score_issue_priorities(issues)

    assert [score.issue_id for score in scores] == ["issue_trade", "issue_watch"]
    assert "internal_score" not in scores[0].recommendation_reason
