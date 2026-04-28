import json

from content_research.research.evidence_normalizer import (
    candidates_to_jsonl,
    normalize_jsonl_lines,
    normalize_record,
)


def test_normalize_news_jsonl_record_uses_metadata_and_rights_gate():
    lines = [
        json.dumps(
            {
                "source_id": "newsapi",
                "source_api_id": "reuters",
                "source_name": "Reuters",
                "title": "Global Economy Story",
                "description": "Short description",
                "url": "https://example.com/economy",
                "published_at": "2026-04-27T02:00:00Z",
                "content_snippet": "Truncated snippet [+100 chars]",
                "body_collection_tier": 0,
            }
        )
    ]

    candidates = normalize_jsonl_lines(lines)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.source_id == "newsapi"
    assert candidate.publisher_or_institution == "Reuters"
    assert candidate.title_or_indicator == "Global Economy Story"
    assert candidate.url == "https://example.com/economy"
    assert candidate.published_or_observed_at == "2026-04-27T02:00:00Z"
    assert candidate.value is None
    assert candidate.unit is None
    assert candidate.snippet == "Truncated snippet [+100 chars]"
    assert candidate.rights_status["body_collection_tier"] == 0
    assert candidate.rights_status["allowed"] is False
    assert candidate.rights_status["storage_policy"] == "metadata_only"
    assert candidate.confidence == 0.65


def test_normalize_official_data_record_preserves_value_unit_and_observation_date():
    record = {
        "source_id": "fred",
        "series_id": "FEDFUNDS",
        "title": "Federal Funds Effective Rate",
        "observation_date": "2026-03-01",
        "value": "4.33",
        "units": "Percent",
        "last_updated": "2026-04-01 15:00:00-05",
        "body_collection_tier": 3,
    }

    candidate = normalize_record(record)

    assert candidate.source_id == "fred"
    assert candidate.publisher_or_institution == "Federal Reserve Bank of St. Louis"
    assert candidate.title_or_indicator == "Federal Funds Effective Rate"
    assert candidate.url == "https://fred.stlouisfed.org/series/FEDFUNDS"
    assert candidate.published_or_observed_at == "2026-03-01"
    assert candidate.value == "4.33"
    assert candidate.unit == "Percent"
    assert candidate.rights_status["body_collection_tier"] == 3
    assert candidate.rights_status["allowed"] is True
    assert candidate.rights_status["storage_policy"] == "official_or_public_data"
    assert candidate.confidence == 0.9


def test_normalize_unknown_source_marks_missing_fields_and_blocks_body_storage():
    candidate = normalize_record({"source_id": "unknown_feed", "title": "Loose item"})

    assert candidate.source_id == "unknown_feed"
    assert candidate.publisher_or_institution is None
    assert candidate.title_or_indicator == "Loose item"
    assert candidate.url is None
    assert candidate.published_or_observed_at is None
    assert candidate.value is None
    assert candidate.unit is None
    assert candidate.snippet is None
    assert candidate.rights_status["license_basis"] == "unknown"
    assert candidate.rights_status["allowed"] is False
    assert candidate.confidence == 0.4


def test_candidates_serialize_to_jsonl():
    candidates = normalize_jsonl_lines(
        [
            json.dumps(
                {
                    "source_id": "un_comtrade",
                    "period": "2024",
                    "reporter_name": "Republic of Korea",
                    "partner_name": "World",
                    "flow_name": "Export",
                    "commodity_name": "TOTAL",
                    "primary_value": "683000000000",
                }
            )
        ]
    )

    jsonl = candidates_to_jsonl(candidates)
    payload = json.loads(jsonl)

    assert payload["source_id"] == "un_comtrade"
    assert payload["publisher_or_institution"] == "UN Comtrade"
    assert payload["title_or_indicator"] == "TOTAL / Export / Republic of Korea"
    assert payload["published_or_observed_at"] == "2024"
    assert payload["value"] == "683000000000"
    assert payload["unit"] == "USD"
