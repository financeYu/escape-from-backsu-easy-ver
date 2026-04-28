from content_research.research.data_matcher import match_issue_data


def test_match_oil_issue_to_eia_indicator():
    issues = [
        {
            "issue_id": "issue_oil",
            "issue_name": "Energy and oil prices",
            "representative_titles": ["Oil prices rise after supply warning"],
            "tags": ["international", "economy", "industry", "geopolitics"],
            "trend_reason": "Repeated oil market coverage.",
        }
    ]
    data = [
        {
            "evidence_id": "data_eia_wti",
            "source_id": "eia",
            "title_or_indicator": "WTI crude oil spot price",
            "published_or_observed_at": "2026-04-24",
            "value": "83.10",
            "unit": "dollars per barrel",
        }
    ]

    matches = match_issue_data(issues, data)

    assert len(matches) == 1
    assert matches[0].issue_id == "issue_oil"
    assert matches[0].matched_data == "data_eia_wti"
    assert matches[0].source_id == "eia"
    assert matches[0].indicator_name == "WTI crude oil spot price"
    assert matches[0].observed_at == "2026-04-24"
    assert matches[0].value == "83.10"
    assert matches[0].unit == "dollars per barrel"
    assert "EIA" in matches[0].match_reason
    assert matches[0].confidence == 0.85


def test_match_korean_oil_issue_to_eia_indicator():
    issues = [
        {
            "issue_id": "issue_oil_kr",
            "issue_name": "에너지와 유가",
            "representative_titles": ["유가 상승과 원유 재고 우려"],
            "tags": ["국제", "경제", "산업"],
            "trend_reason": "반복 출현.",
        }
    ]
    data = [
        {
            "evidence_id": "data_eia_wti",
            "source_id": "eia",
            "title_or_indicator": "WTI crude oil spot price",
            "published_or_observed_at": "2026-04-24",
            "value": "83.10",
            "unit": "dollars per barrel",
        }
    ]

    matches = match_issue_data(issues, data)

    assert len(matches) == 1
    assert matches[0].matched_data == "data_eia_wti"


def test_match_us_rates_issue_to_fred_indicator():
    issues = [
        {
            "issue_id": "issue_fed",
            "issue_name": "Fed rate cut debate",
            "representative_titles": ["Federal Reserve officials discuss interest rate timing"],
            "tags": ["international", "economy"],
            "trend_reason": "Repeated coverage.",
        }
    ]
    data = [
        {
            "evidence_id": "data_fred_fedfunds",
            "source_id": "fred",
            "title_or_indicator": "Federal Funds Effective Rate",
            "published_or_observed_at": "2026-03-01",
            "value": "4.33",
            "unit": "Percent",
        }
    ]

    match = match_issue_data(issues, data)[0]

    assert match.issue_id == "issue_fed"
    assert match.source_id == "fred"
    assert match.matched_data == "data_fred_fedfunds"
    assert "FRED" in match.match_reason
    assert match.confidence == 0.85


def test_match_korea_macro_issue_to_ecos_or_kosis_indicator():
    issues = [
        {
            "issue_id": "issue_korea_prices",
            "issue_name": "Korea inflation and employment",
            "representative_titles": ["Korean consumer price and employment indicators draw attention"],
            "tags": ["korea", "economy"],
            "trend_reason": "Repeated coverage.",
        }
    ]
    data = [
        {
            "evidence_id": "data_kosis_cpi",
            "source_id": "kosis",
            "title_or_indicator": "Korea consumer price index",
            "published_or_observed_at": "2026-03",
            "value": "114.2",
            "unit": "index",
        }
    ]

    match = match_issue_data(issues, data)[0]

    assert match.issue_id == "issue_korea_prices"
    assert match.source_id == "kosis"
    assert match.indicator_name == "Korea consumer price index"
    assert "ECOS or KOSIS" in match.match_reason
    assert match.confidence == 0.8


def test_match_korean_macro_issue_to_kosis_indicator():
    issues = [
        {
            "issue_id": "issue_korea_prices_kr",
            "issue_name": "한국 물가와 고용 흐름",
            "representative_titles": ["한국 소비자물가와 고용 지표가 주목받고 있다"],
            "tags": ["한국", "경제"],
            "trend_reason": "반복 출현.",
        }
    ]
    data = [
        {
            "evidence_id": "data_kosis_cpi",
            "source_id": "kosis",
            "title_or_indicator": "소비자물가지수",
            "published_or_observed_at": "2026-03",
            "value": "114.2",
            "unit": "index",
        }
    ]

    match = match_issue_data(issues, data)[0]

    assert match.source_id == "kosis"
    assert match.indicator_name == "소비자물가지수"


def test_match_trade_issue_to_un_comtrade():
    issues = [
        {
            "issue_id": "issue_trade",
            "issue_name": "Trade and tariff pressure",
            "representative_titles": ["Exports and tariffs put supply chains in focus"],
            "tags": ["international", "economy", "geopolitics"],
            "trend_reason": "Repeated coverage.",
        }
    ]
    data = [
        {
            "evidence_id": "data_comtrade_exports",
            "source_id": "un_comtrade",
            "title_or_indicator": "TOTAL / Export / Republic of Korea",
            "published_or_observed_at": "2024",
            "value": "683000000000",
            "unit": "USD",
        }
    ]

    match = match_issue_data(issues, data)[0]

    assert match.issue_id == "issue_trade"
    assert match.source_id == "un_comtrade"
    assert match.value == "683000000000"
    assert match.unit == "USD"
    assert "UN Comtrade" in match.match_reason
    assert match.confidence == 0.85


def test_uncertain_or_missing_data_lowers_confidence():
    issues = [
        {
            "issue_id": "issue_oil",
            "issue_name": "Oil prices",
            "representative_titles": ["Oil market update"],
            "tags": ["economy"],
            "trend_reason": "Single candidate.",
        }
    ]
    data = [
        {
            "evidence_id": "data_eia_missing",
            "source_id": "eia",
            "title_or_indicator": "WTI crude oil spot price",
            "published_or_observed_at": "2026-04-24",
            "value": "83.10",
        }
    ]

    match = match_issue_data(issues, data)[0]

    assert match.unit is None
    assert match.confidence == 0.55


def test_unrelated_official_data_is_not_forced_into_match():
    issues = [
        {
            "issue_id": "issue_oil",
            "issue_name": "Oil prices",
            "representative_titles": ["Oil market update"],
            "tags": ["economy"],
            "trend_reason": "Single candidate.",
        }
    ]
    data = [
        {
            "evidence_id": "data_fred_rate",
            "source_id": "fred",
            "title_or_indicator": "Federal Funds Effective Rate",
            "published_or_observed_at": "2026-03-01",
            "value": "4.33",
            "unit": "Percent",
        }
    ]

    assert match_issue_data(issues, data) == []
