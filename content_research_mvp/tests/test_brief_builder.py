from content_research.research.brief_builder import build_research_brief


def test_build_research_brief_for_single_issue_with_official_data():
    issue = {
        "issue_id": "issue_oil",
        "issue_name": "Energy and oil prices",
        "representative_titles": ["Oil prices rise after supply warning"],
        "related_evidence_ids": ["ev_news"],
        "tags": ["international", "economy", "industry"],
        "trend_reason": "Repeated coverage from 2026-04-26 to 2026-04-27.",
    }
    evidence = [
        {
            "evidence_id": "ev_news",
            "source_id": "newsapi",
            "publisher_or_institution": "Reuters",
            "title_or_indicator": "Oil prices rise after supply warning",
            "url": "https://example.com/oil",
            "published_or_observed_at": "2026-04-27T02:00:00Z",
            "snippet": "Short metadata snippet only.",
            "rights_status": {"allowed": False, "storage_policy": "metadata_only"},
        }
    ]
    data_matches = [
        {
            "issue_id": "issue_oil",
            "matched_data": "data_eia_wti",
            "indicator_name": "WTI crude oil spot price",
            "source_id": "eia",
            "observed_at": "2026-04-24",
            "value": "83.10",
            "unit": "dollars per barrel",
            "confidence": 0.85,
        }
    ]
    claims = [
        {
            "claim": "Oil prices rose 3% on 2026-04-27.",
            "key_numbers": ["3%"],
            "dates": ["2026-04-27"],
            "source_id": "newsapi",
            "evidence_id": "ev_news",
            "needs_verification": True,
            "confidence": 0.65,
        }
    ]

    brief = build_research_brief(
        issue_id="issue_oil",
        issue_candidates=[issue],
        evidence_candidates=evidence,
        data_matches=data_matches,
        claims=claims,
    )

    assert brief.issue_name == "Energy and oil prices"
    assert len(brief.summary_lines) == 3
    assert any("83.10 dollars per barrel" in fact for fact in brief.key_facts)
    assert any("needs_verification" in item for item in brief.final_check)
    assert any("no body use" in source for source in brief.sources)


def test_brief_markdown_has_required_sections_and_sources():
    brief = build_research_brief(
        issue_id="issue_trade",
        issue_candidates=[
            {
                "issue_id": "issue_trade",
                "issue_name": "Trade and tariff pressure",
                "representative_titles": ["Exports and tariffs put supply chains in focus"],
                "related_evidence_ids": [],
                "tags": ["international", "economy"],
                "trend_reason": "Repeated trade coverage.",
            }
        ],
        evidence_candidates=[
            {
                "source_id": "un_comtrade",
                "title_or_indicator": "TOTAL / Export / Republic of Korea",
                "url": "https://comtradeplus.un.org/",
                "rights_status": {"allowed": True, "storage_policy": "official_or_public_data"},
            }
        ],
        data_matches=[
            {
                "issue_id": "issue_trade",
                "matched_data": "data_comtrade_exports",
                "indicator_name": "TOTAL / Export / Republic of Korea",
                "source_id": "un_comtrade",
                "observed_at": "2024",
                "value": "683000000000",
                "unit": "USD",
            }
        ],
        claims=[],
    )

    markdown = brief.to_markdown()

    assert "## 이슈명" in markdown
    assert "## 핵심 사실" in markdown
    assert "## 출처 목록" in markdown
    assert "683000000000 USD" in markdown
    assert "https://comtradeplus.un.org/" in markdown


def test_brief_requires_existing_issue_id():
    try:
        build_research_brief(
            issue_id="missing",
            issue_candidates=[],
            evidence_candidates=[],
        )
    except ValueError as exc:
        assert "issue_id not found" in str(exc)
    else:
        raise AssertionError("expected ValueError")
