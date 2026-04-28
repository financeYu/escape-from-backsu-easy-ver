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
                "collected_at": "2026-04-27T11:00:00+09:00",
                "accessed_at": "2026-04-27T11:01:00+09:00",
                "content_snippet": "Truncated snippet [+100 chars]",
                "body_collection_tier": 0,
            }
        )
    ]

    candidates = normalize_jsonl_lines(lines)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.source_id == "newsapi"
    assert candidate.source_name == "Reuters"
    assert candidate.publisher_or_institution == "Reuters"
    assert candidate.title_or_indicator == "Global Economy Story"
    assert candidate.url == "https://example.com/economy"
    assert candidate.published_or_observed_at == "2026-04-27T02:00:00Z"
    assert candidate.collected_at == "2026-04-27T11:00:00+09:00"
    assert candidate.accessed_at == "2026-04-27T11:01:00+09:00"
    assert candidate.value is None
    assert candidate.unit is None
    assert candidate.snippet == "Truncated snippet [+100 chars]"
    assert candidate.field_status["source_url"] == "present"
    assert candidate.field_status["collected_at"] == "present"
    assert candidate.field_status["accessed_at"] == "present"
    assert candidate.field_status["key_number"] == "unsupported"
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
        "retrieved_at": "2026-04-27T12:00:00+09:00",
        "body_collection_tier": 3,
    }

    candidate = normalize_record(record)

    assert candidate.source_id == "fred"
    assert candidate.source_name == "Federal Reserve Bank of St. Louis"
    assert candidate.publisher_or_institution == "Federal Reserve Bank of St. Louis"
    assert candidate.title_or_indicator == "Federal Funds Effective Rate"
    assert candidate.url == "https://fred.stlouisfed.org/series/FEDFUNDS"
    assert candidate.published_or_observed_at == "2026-03-01"
    assert candidate.collected_at == "2026-04-27T12:00:00+09:00"
    assert candidate.accessed_at == "2026-04-27T12:00:00+09:00"
    assert candidate.value == "4.33"
    assert candidate.unit == "Percent"
    assert candidate.field_status["key_number"] == "present"
    assert candidate.field_status["snippet_or_context"] == "unsupported"
    assert candidate.rights_status["body_collection_tier"] == 3
    assert candidate.rights_status["allowed"] is True
    assert candidate.rights_status["storage_policy"] == "official_or_public_data"
    assert candidate.confidence == 0.9


def test_normalize_ecos_record_preserves_adapter_specific_unit_and_cycle():
    candidate = normalize_record(
        {
            "source_id": "ecos",
            "statistic_name": "Bank of Korea Base Rate",
            "data_value": "2.50",
            "unit_name": "%",
            "cycle": "202604",
            "body_collection_tier": 3,
        }
    )

    assert candidate.title_or_indicator == "Bank of Korea Base Rate"
    assert candidate.published_or_observed_at == "202604"
    assert candidate.value == "2.50"
    assert candidate.unit == "%"
    assert candidate.field_status["collected_at"] == "missing"
    assert candidate.confidence == 0.9


def test_normalize_kosis_record_preserves_updated_at_and_catalog_title():
    candidate = normalize_record(
        {
            "source_id": "kosis",
            "list_name": "Population",
            "updated_at": "20260427",
            "body_collection_tier": 3,
        }
    )

    assert candidate.title_or_indicator == "Population"
    assert candidate.published_or_observed_at == "20260427"
    assert candidate.field_status["key_number"] == "missing"


def test_normalize_unknown_source_marks_missing_fields_and_blocks_body_storage():
    candidate = normalize_record({"source_id": "unknown_feed", "title": "Loose item"})

    assert candidate.source_id == "unknown_feed"
    assert candidate.publisher_or_institution is None
    assert candidate.title_or_indicator == "Loose item"
    assert candidate.url is None
    assert candidate.published_or_observed_at is None
    assert candidate.collected_at is None
    assert candidate.accessed_at is None
    assert candidate.value is None
    assert candidate.unit is None
    assert candidate.snippet is None
    assert candidate.field_status["source_url"] == "missing"
    assert candidate.field_status["collected_at"] == "missing"
    assert candidate.field_status["accessed_at"] == "missing"
    assert candidate.rights_status["license_basis"] == "unknown"
    assert candidate.rights_status["allowed"] is False
    assert candidate.confidence == 0.4


def test_normalize_jsonl_lines_skips_manifest_and_non_mvp_placeholder_records():
    lines = [
        json.dumps({"type": "collection_run", "run_id": "run_1"}),
        json.dumps(
            {
                "type": "source_result",
                "run_id": "run_1",
                "source_id": "guardian",
                "status": "planned_non_mvp",
                "title": "Should not become evidence",
            }
        ),
        json.dumps(
            {
                "source_id": "guardian",
                "status": "planned_non_mvp",
                "title": "Should also not become evidence",
            }
        ),
        json.dumps(
            {
                "source_id": "newsapi",
                "source_name": "Reuters",
                "title": "Usable metadata item",
                "url": "https://example.com/economy",
                "published_at": "2026-04-27T02:00:00Z",
                "collected_at": "2026-04-27T11:00:00+09:00",
            }
        ),
    ]

    candidates = normalize_jsonl_lines(lines)

    assert len(candidates) == 1
    assert candidates[0].source_id == "newsapi"
    assert candidates[0].title_or_indicator == "Usable metadata item"


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
    assert payload["field_status"]["collected_at"] == "missing"
    assert payload["value"] == "683000000000"
    assert payload["unit"] == "USD"
