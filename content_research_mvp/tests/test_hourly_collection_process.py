import json
from datetime import datetime

from content_research.collection.catalog import CollectionSource
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
    assert records[1]["rights_gate_status"] == "metadata_only"


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
