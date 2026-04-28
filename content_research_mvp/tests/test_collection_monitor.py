import json
from pathlib import Path

from content_research.collection.monitor import (
    monitor_jsonl_files,
    monitor_records,
    notify_stub,
    summarize_report,
)


def test_monitor_records_summarizes_success_and_last_success():
    report = monitor_records(
        [
            {
                "type": "source_result",
                "source_id": "newsapi",
                "status": "fetched_metadata",
                "collected_records": 12,
                "finished_at": "2026-04-27T10:00:00+09:00",
            },
            {
                "type": "source_result",
                "source_id": "newsapi",
                "status": "fetched_metadata",
                "collected_records": 15,
                "finished_at": "2026-04-27T11:00:00+09:00",
            },
        ]
    )

    status = report.sources[0]

    assert status.source_id == "newsapi"
    assert status.status == "success"
    assert status.last_success_at == "2026-04-27T11:00:00+09:00"
    assert status.recent_count == 15
    assert status.error_type is None
    assert status.warning_reason is None


def test_monitor_detects_missing_credentials_and_permission_denied():
    report = monitor_records(
        [
            {
                "source_id": "fred",
                "status": "missing_credentials",
                "collected_records": 0,
                "message": "FRED_API_KEY is required.",
                "finished_at": "2026-04-27T10:00:00+09:00",
            },
            {
                "source_id": "eia",
                "status": "error",
                "collected_records": 0,
                "message": "HTTP 403 forbidden: plan lacks permission",
                "finished_at": "2026-04-27T10:00:00+09:00",
            },
        ]
    )

    by_source = {source.source_id: source for source in report.sources}

    assert by_source["fred"].error_type == "missing_credentials"
    assert by_source["eia"].status == "source_error"
    assert by_source["eia"].error_type == "permission_denied"
    assert by_source["fred"].last_success_at is None


def test_monitor_uses_collection_run_finished_at_when_source_result_lacks_time():
    report = monitor_records(
        [
            {
                "type": "collection_run",
                "run_id": "run-abc",
                "started_at": "2026-04-27T10:00:00+09:00",
                "finished_at": "2026-04-27T10:01:00+09:00",
            },
            {
                "type": "source_result",
                "run_id": "run-abc",
                "source_id": "eia",
                "status": "fetched_energy_series",
                "collected_records": 1,
            },
        ]
    )

    assert report.sources[0].last_success_at == "2026-04-27T10:01:00+09:00"


def test_monitor_ignores_evidence_records_with_source_id():
    report = monitor_records(
        [
            {
                "evidence_id": "ev_news",
                "source_id": "newsapi",
                "title_or_indicator": "Oil prices rise",
                "rights_status": {"allowed": False, "storage_policy": "metadata_only"},
            }
        ]
    )

    assert report.sources == []


def test_monitor_detects_collection_count_drop_against_baseline():
    report = monitor_records(
        [
            {
                "source_id": "naver_news",
                "status": "fetched_metadata",
                "collected_records": 100,
                "finished_at": "2026-04-27T09:00:00+09:00",
            },
            {
                "source_id": "naver_news",
                "status": "fetched_metadata",
                "collected_records": 90,
                "finished_at": "2026-04-27T10:00:00+09:00",
            },
            {
                "source_id": "naver_news",
                "status": "fetched_metadata",
                "collected_records": 20,
                "finished_at": "2026-04-27T11:00:00+09:00",
            },
        ],
        drop_ratio=0.5,
    )

    status = report.sources[0]

    assert status.status == "success"
    assert status.recent_count == 20
    assert "dropped below" in status.warning_reason


def test_monitor_detects_expected_min_records_warning():
    report = monitor_records(
        [
            {
                "source_id": "nytimes",
                "status": "fetched_metadata",
                "collected_records": 3,
                "finished_at": "2026-04-27T11:00:00+09:00",
            }
        ],
        expected_min_records={"nytimes": 10},
    )

    assert report.sources[0].warning_reason == "recent_count 3 is below expected_min_records 10"


def test_monitor_reads_jsonl_file_and_generates_report():
    path = Path(__file__).parent / "fixtures" / "collection_manifest_sample.jsonl"

    report = monitor_jsonl_files([path])
    summary = summarize_report(report)
    notifications = notify_stub(report)
    markdown = report.to_markdown()

    assert report.sources[0].source_id == "un_comtrade"
    assert summary["status_counts"] == {"success": 1}
    assert notifications == []
    assert "un_comtrade" in markdown
