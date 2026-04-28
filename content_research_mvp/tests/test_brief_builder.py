import re

from content_research.research.brief_builder import ResearchBrief, build_research_brief


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

    assert "## 제목" in markdown
    assert "## 주요 날짜·핵심 수치·직접 원인" in markdown
    assert "## 한국과의 연결점" in markdown
    assert "## 근거와 출처" in markdown
    assert "683000000000 USD" in markdown
    assert "https://comtradeplus.un.org/" in markdown


def test_research_brief_markdown_uses_korean_heading_snapshot_without_mojibake():
    brief = ResearchBrief(
        issue_name="무역 압력",
        summary_lines=["수출 지표가 둔화됐다.", "관세 변수가 남아 있다.", "추가 공식 통계 확인이 필요하다."],
        why_important="",
        key_facts=["2024년 수출액 683000000000 USD"],
        main_flow=["관세 압력이 공급망 비용으로 이어졌다."],
        actors_and_context=["산업통상자원부: 공식 통계 출처"],
        watch_points=["다음 월간 수출 통계를 확인한다."],
        sources=["official_data - exports - data_comtrade_exports"],
        final_check=["단일 원인으로 단정하지 않는다."],
    )

    markdown = brief.to_markdown()

    assert markdown == """## 제목
무역 압력

## 핵심 요약
- 수출 지표가 둔화됐다.
- 관세 변수가 남아 있다.
- 추가 공식 통계 확인이 필요하다.

## 주요 날짜·핵심 수치·직접 원인
- 2024년 수출액 683000000000 USD
- 관세 압력이 공급망 비용으로 이어졌다.

## 관련 국가·기업·기관·배경 맥락
- 산업통상자원부: 공식 통계 출처

## 변수·전망·불확실성
- 다음 월간 수출 통계를 확인한다.

## 오해하기 쉬운 부분
- 단일 원인으로 단정하지 않는다.

## 근거와 출처
- official_data - exports - data_comtrade_exports
"""
    assert re.findall(r"^## (.+)$", markdown, flags=re.MULTILINE) == [
        "제목",
        "핵심 요약",
        "주요 날짜·핵심 수치·직접 원인",
        "관련 국가·기업·기관·배경 맥락",
        "변수·전망·불확실성",
        "오해하기 쉬운 부분",
        "근거와 출처",
    ]


def test_brief_keeps_trace_and_excludes_source_less_or_certain_future_claims():
    brief = build_research_brief(
        issue_id="issue_supply",
        issue_candidates=[
            {
                "issue_id": "issue_supply",
                "issue_name": "Supply chain pressure",
                "representative_titles": ["Supply chain pressure rises"],
                "related_evidence_ids": ["ev_known"],
                "tags": ["economy"],
                "trend_reason": "Repeated coverage.",
            }
        ],
        evidence_candidates=[
            {
                "evidence_id": "ev_known",
                "source_id": "newsapi",
                "source_name": "Reuters",
                "publisher_or_institution": "Reuters",
                "title_or_indicator": "Supply chain pressure rises",
                "url": "https://example.com/supply",
                "published_or_observed_at": "2026-04-27T02:00:00Z",
                "collected_at": "2026-04-27T11:00:00+09:00",
                "accessed_at": "2026-04-27T11:01:00+09:00",
                "rights_status": {"allowed": False, "storage_policy": "metadata_only"},
                "field_status": {
                    "issue_title": "present",
                    "published_or_observed_at": "present",
                    "source_name": "present",
                    "source_url": "present",
                    "collected_at": "present",
                    "accessed_at": "present",
                },
            }
        ],
        data_matches=[],
        claims=[
            {
                "claim": "This sourced claim is usable.",
                "source_id": "newsapi",
                "evidence_id": "ev_known",
                "needs_verification": False,
            },
            {
                "claim": "This claim has no source trace.",
                "source_id": None,
                "evidence_id": "ev_known",
                "needs_verification": False,
            },
            {
                "claim": "The economy will recover fully next month.",
                "source_id": "newsapi",
                "evidence_id": "ev_known",
                "needs_verification": False,
            },
        ],
    )

    markdown = brief.to_markdown()

    assert "This sourced claim is usable." in "\n".join(brief.key_facts)
    assert "This claim has no source trace." not in "\n".join(brief.key_facts)
    assert "will recover fully" not in "\n".join(brief.key_facts)
    assert "This claim has no source trace." not in markdown
    assert "will recover fully" not in markdown
    assert "출처명 Reuters" in markdown
    assert "발행/관측 2026-04-27T02:00:00Z" in markdown
    assert "수집 2026-04-27T11:00:00+09:00" in markdown
    assert any("source_trace 누락 주장 1건" in item for item in brief.final_check)
    assert any("단정적 미래 전망 표현 1건" in item for item in brief.final_check)


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
