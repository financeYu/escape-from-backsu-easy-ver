import json
from datetime import datetime
from zoneinfo import ZoneInfoNotFoundError

import content_research.collection.process as process_module
from content_research.collection.catalog import CollectionSource, DEFAULT_COLLECTION_SOURCES, MVP_COLLECTION_SOURCE_IDS
from content_research.collection.process import HourlyCollectionProcess


def test_collect_once_writes_partitioned_manifest(tmp_path):
    source = CollectionSource(
        source_id="test_source",
        display_name="Test Source",
        category="test",
        adapter="test.adapter",
        access_method="api",
        default_body_tier=0,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, jsonl_path, markdown_path = process.run_once(
        now=datetime(2026, 4, 27, 13, 25, 30),
        mode="test",
    )

    assert manifest.next_run_at == "2026-04-27T14:00:00+09:00"
    assert jsonl_path.exists()
    assert markdown_path.exists()
    assert "2026-04-27\\13" in str(jsonl_path) or "2026-04-27/13" in str(jsonl_path)

    records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]

    assert records[0]["type"] == "collection_run"
    assert records[0]["sources_enabled"] == 1
    assert records[1]["type"] == "source_result"
    assert records[1]["status"] == "planned_non_mvp"
    assert records[1]["rights_gate_status"] == "not_checked"


def test_collect_once_falls_back_when_asia_seoul_tzdata_is_missing(monkeypatch, tmp_path):
    original_zoneinfo = process_module.ZoneInfo

    def missing_zoneinfo(timezone_name):
        if timezone_name == "Asia/Seoul":
            raise ZoneInfoNotFoundError(timezone_name)
        return original_zoneinfo(timezone_name)

    monkeypatch.setattr(process_module, "ZoneInfo", missing_zoneinfo)
    source = CollectionSource(
        source_id="test_source",
        display_name="Test Source",
        category="test",
        adapter="test.adapter",
        access_method="api",
        default_body_tier=0,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, timezone_name="Asia/Seoul", sources=[source])

    manifest, jsonl_path, markdown_path = process.run_once(
        now=datetime(2026, 4, 27, 13, 25, 30),
        mode="test",
    )

    assert manifest.started_at == "2026-04-27T13:25:30+09:00"
    assert manifest.next_run_at == "2026-04-27T14:00:00+09:00"
    assert jsonl_path.exists()
    assert markdown_path.exists()


def test_collect_daemon_can_run_limited_cycles_without_sleeping(tmp_path):
    source = CollectionSource(
        source_id="test_source",
        display_name="Test Source",
        category="test",
        adapter="test.adapter",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    sleeps: list[float] = []
    manifests = process.run_forever(max_cycles=2, sleep_fn=sleeps.append)

    assert len(manifests) == 2
    assert len(sleeps) == 1
    assert manifests[0].sources_enabled == 1


def test_collect_once_uses_unique_run_ids_for_same_second(tmp_path):
    source = CollectionSource(
        source_id="test_source",
        display_name="Test Source",
        category="test",
        adapter="test.adapter",
        access_method="api",
        default_body_tier=0,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])
    now = datetime(2026, 4, 27, 13, 25, 30)

    first, first_path, _ = process.run_once(now=now, mode="test")
    second, second_path, _ = process.run_once(now=now, mode="test")

    assert first.run_id != second.run_id
    assert first_path.exists()
    assert second_path.exists()
    assert first_path != second_path


def test_mvp_sources_are_dispatched_to_real_handlers(monkeypatch, tmp_path):
    monkeypatch.setattr(process_module.NaverNewsClient, "from_env", classmethod(lambda cls: None))
    monkeypatch.setattr(process_module.NewsAPIClient, "from_env", classmethod(lambda cls: None))
    monkeypatch.setattr(process_module.NYTimesClient, "from_env", classmethod(lambda cls: None))
    monkeypatch.setattr(process_module.ECOSClient, "from_env", classmethod(lambda cls: None))
    monkeypatch.setattr(process_module.KOSISClient, "from_env", classmethod(lambda cls: None))
    monkeypatch.setattr(process_module.OpenDARTClient, "from_env", classmethod(lambda cls: None))
    monkeypatch.setattr(process_module.FREDClient, "from_env", classmethod(lambda cls: None))
    monkeypatch.setattr(process_module.EIAClient, "from_env", classmethod(lambda cls: None))
    monkeypatch.setattr(process_module.UNComtradeClient, "from_env", classmethod(lambda cls: None))
    sources = [source for source in DEFAULT_COLLECTION_SOURCES if source.source_id in MVP_COLLECTION_SOURCE_IDS]
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=sources)

    manifest, _, _ = process.run_once()

    assert {result.source_id for result in manifest.results} == MVP_COLLECTION_SOURCE_IDS
    assert all(result.adapter.startswith("content_research.sources.") for result in manifest.results)
    assert {result.status for result in manifest.results} == {"missing_credentials"}
    assert all(result.records_path == "" for result in manifest.results)
    assert all("required" in result.message for result in manifest.results)


def test_non_mvp_sources_are_separated_from_collection_handlers(tmp_path):
    source = next(source for source in DEFAULT_COLLECTION_SOURCES if source.source_id == "guardian")
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, jsonl_path, _ = process.run_once()

    result = manifest.results[0]
    assert result.source_id == "guardian"
    assert result.status == "planned_non_mvp"
    assert result.rights_gate_status == "not_checked"
    assert result.collected_records == 0
    assert result.records_path == ""
    assert "outside the MVP collection scope" in result.message

    records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert records[1]["status"] == "planned_non_mvp"
