from content_research.research.issue_radar import detect_issue_candidates


def test_issue_radar_dedupes_duplicate_urls():
    evidence = [
        {
            "evidence_id": "ev1",
            "source_id": "newsapi",
            "title_or_indicator": "Fed rate cut debate intensifies",
            "url": "https://example.com/fed-rate",
            "published_or_observed_at": "2026-04-27T01:00:00Z",
            "snippet": "Central bank officials discuss interest rate timing.",
        },
        {
            "evidence_id": "ev2",
            "source_id": "nytimes",
            "title_or_indicator": "Fed rate cut debate intensifies",
            "url": "https://www.example.com/fed-rate/",
            "published_or_observed_at": "2026-04-27T02:00:00Z",
            "snippet": "Duplicate URL from another feed.",
        },
    ]

    issues = detect_issue_candidates(evidence)

    assert len(issues) == 1
    assert issues[0].related_evidence_ids == ["ev1"]
    assert issues[0].trend_reason == "단건 후보: 추가 출처 확인이 필요함."


def test_issue_radar_groups_titles_and_snippets_by_keywords():
    evidence = [
        {
            "evidence_id": "ev1",
            "source_id": "newsapi",
            "title_or_indicator": "Oil prices rise after supply warning",
            "url": "https://example.com/oil-1",
            "published_or_observed_at": "2026-04-26T01:00:00Z",
            "snippet": "Energy markets watch OPEC supply signals.",
        },
        {
            "evidence_id": "ev2",
            "source_id": "nytimes",
            "title_or_indicator": "Energy shares move as crude market tightens",
            "url": "https://example.com/oil-2",
            "published_or_observed_at": "2026-04-27T01:00:00Z",
            "snippet": "Crude oil benchmarks gained.",
        },
    ]

    issues = detect_issue_candidates(evidence)

    assert len(issues) == 1
    issue = issues[0]
    assert issue.issue_name == "에너지와 유가"
    assert issue.related_evidence_ids == ["ev1", "ev2"]
    assert issue.first_seen_at == "2026-04-26T01:00:00Z"
    assert issue.last_seen_at == "2026-04-27T01:00:00Z"
    assert "반복 출현" in issue.trend_reason


def test_issue_radar_assigns_minimum_tags():
    evidence = [
        {
            "evidence_id": "ev1",
            "source_id": "naver_news",
            "title_or_indicator": "한국 반도체 수출 회복 기대",
            "url": "https://example.kr/chips",
            "published_or_observed_at": "2026-04-27T03:00:00Z",
            "snippet": "AI 수요와 공급망 재편이 산업 흐름에 영향을 주고 있다.",
        }
    ]

    issue = detect_issue_candidates(evidence)[0]

    assert "한국" in issue.tags
    assert "경제" in issue.tags


def test_issue_radar_ignores_official_data_candidates():
    evidence = [
        {
            "evidence_id": "official1",
            "source_id": "fred",
            "title_or_indicator": "Federal Funds Effective Rate",
            "url": "https://fred.stlouisfed.org/series/FEDFUNDS",
            "published_or_observed_at": "2026-03-01",
            "value": "4.33",
            "unit": "Percent",
        }
    ]

    assert detect_issue_candidates(evidence) == []
