from content_research.research.claim_extractor import extract_claims


def test_extract_claims_gets_numbers_dates_and_marks_news_for_verification():
    evidence = [
        {
            "evidence_id": "ev_news",
            "source_id": "newsapi",
            "title_or_indicator": "Oil prices rose 3% on 2026-04-27",
            "snippet": "WTI traded near 83.10 dollars per barrel as supply concerns persisted.",
            "published_or_observed_at": "2026-04-27T02:00:00Z",
            "confidence": 0.65,
        }
    ]

    claim = extract_claims(evidence)[0]

    assert "Oil prices rose 3%" in claim.claim
    assert "3%" in claim.key_numbers
    assert "83.10 dollars" in claim.key_numbers
    assert "2026-04-27T02:00:00Z" in claim.dates
    assert "2026-04-27" in claim.dates
    assert claim.source_id == "newsapi"
    assert claim.evidence_id == "ev_news"
    assert claim.needs_verification is True
    assert claim.confidence == 0.65


def test_extract_claims_from_official_data_is_verifiable_when_complete():
    evidence = [
        {
            "evidence_id": "fred_fedfunds",
            "source_id": "fred",
            "title_or_indicator": "Federal Funds Effective Rate",
            "published_or_observed_at": "2026-03-01",
            "value": "4.33",
            "unit": "Percent",
            "confidence": 0.9,
            "rights_status": {"allowed": True},
        }
    ]

    claim = extract_claims(evidence)[0]

    assert claim.claim == "Federal Funds Effective Rate was 4.33 Percent on 2026-03-01."
    assert claim.key_numbers == ["4.33 Percent", "4.33"]
    assert claim.dates == ["2026-03-01"]
    assert claim.needs_verification is False
    assert claim.confidence == 0.9


def test_extract_claims_marks_incomplete_official_data_for_verification():
    claim = extract_claims(
        [
            {
                "source_id": "eia",
                "title_or_indicator": "WTI crude oil spot price",
                "value": "83.10",
            }
        ]
    )[0]

    assert claim.needs_verification is True
    assert claim.confidence == 0.65
