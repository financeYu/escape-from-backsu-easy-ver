import json

import pytest

from content_research.collection.catalog import CollectionSource
from content_research.collection.process import HourlyCollectionProcess
from content_research.sources.official_data import ecos
from content_research.sources.official_data.ecos import ECOSClient, ECOSCredentials


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_ecos_key_statistics_parses_rows(monkeypatch):
    payload = {
        "KeyStatisticList": {
            "list_total_count": 1,
            "row": [
                {
                    "CLASS_NAME": "시장금리",
                    "KEYSTAT_NAME": "한국은행 기준금리",
                    "DATA_VALUE": "2.50",
                    "UNIT_NAME": "%",
                    "CYCLE": "202604",
                }
            ],
        }
    }

    def fake_urlopen(request, timeout):
        assert "KeyStatisticList/secret/json/kr/1/100" in request.full_url
        return FakeResponse(payload)

    monkeypatch.setattr(ecos, "urlopen", fake_urlopen)

    client = ECOSClient(ECOSCredentials("secret"))
    result = client.key_statistics()

    assert result.list_total_count == 1
    assert result.items[0].statistic_name == "한국은행 기준금리"
    assert result.items[0].data_value == "2.50"
    assert result.items[0].unit_name == "%"
    assert result.items[0].body_collection_tier == 3


def test_collection_process_writes_ecos_records(monkeypatch, tmp_path):
    item = ecos.ECOSKeyStatisticItem(
        source_id="ecos",
        statistic_name="한국은행 기준금리",
        data_value="2.50",
        unit_name="%",
        cycle="202604",
        class_name="시장금리",
        raw={"KEYSTAT_NAME": "한국은행 기준금리"},
    )

    class FakeClient:
        def key_statistics(self, start=1, end=100, language="kr"):
            assert start == 1
            assert end == 100
            assert language == "kr"
            return ecos.ECOSKeyStatisticResult(list_total_count=1, items=[item])

    monkeypatch.setattr(ecos.ECOSClient, "from_env", classmethod(lambda cls: FakeClient()))

    source = CollectionSource(
        source_id="ecos",
        display_name="Bank of Korea ECOS",
        category="korean_official_data",
        adapter="official_data.ecos",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, jsonl_path, _ = process.run_once()

    assert manifest.results[0].status == "fetched_statistics"
    assert manifest.results[0].collected_records == 1
    records_path = tmp_path / manifest.output_partition / "records" / manifest.run_id / "ecos.jsonl"
    assert records_path.exists()
    assert "한국은행 기준금리" in records_path.read_text(encoding="utf-8")

    manifest_records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    source_result = next(record for record in manifest_records if record["type"] == "source_result")
    assert source_result["records_path"].endswith("ecos.jsonl")


def test_ecos_missing_credentials_returns_status(monkeypatch, tmp_path):
    monkeypatch.setattr(ecos.ECOSClient, "from_env", classmethod(lambda cls: None))
    source = CollectionSource(
        source_id="ecos",
        display_name="Bank of Korea ECOS",
        category="korean_official_data",
        adapter="official_data.ecos",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, _, _ = process.run_once()

    assert manifest.results[0].status == "missing_credentials"
    assert "ECOS_API_KEY" in manifest.results[0].message


def test_invalid_ecos_range_rejected():
    client = ECOSClient(ECOSCredentials("secret"))

    with pytest.raises(ValueError, match="end"):
        client.key_statistics(start=10, end=1)
