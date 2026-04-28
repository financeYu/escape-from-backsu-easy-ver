import json

import pytest

from content_research.collection.catalog import CollectionSource
from content_research.collection.process import HourlyCollectionProcess
from content_research.sources.official_data import opendart
from content_research.sources.official_data.opendart import OpenDARTClient, OpenDARTCredentials


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_opendart_disclosure_list_parses_rows(monkeypatch):
    payload = {
        "status": "000",
        "message": "정상",
        "page_no": 1,
        "page_count": 100,
        "total_count": 1,
        "list": [
            {
                "corp_code": "00126380",
                "corp_name": "삼성전자",
                "stock_code": "005930",
                "corp_cls": "Y",
                "report_nm": "분기보고서",
                "rcept_no": "20260427000001",
                "rcept_dt": "20260427",
                "flr_nm": "삼성전자",
                "rm": "",
            }
        ],
    }

    def fake_urlopen(request, timeout):
        assert "list.json" in request.full_url
        assert "crtfc_key=secret" in request.full_url
        assert "bgn_de=20260420" in request.full_url
        assert "end_de=20260427" in request.full_url
        return FakeResponse(payload)

    monkeypatch.setattr(opendart, "urlopen", fake_urlopen)

    client = OpenDARTClient(OpenDARTCredentials("secret"))
    result = client.disclosure_list(begin_date="20260420", end_date="20260427")

    assert result.status == "000"
    assert result.items[0].corp_name == "삼성전자"
    assert result.items[0].report_name == "분기보고서"
    assert result.items[0].body_collection_tier == 3


def test_collection_process_writes_opendart_records(monkeypatch, tmp_path):
    item = opendart.OpenDARTDisclosureItem(
        source_id="opendart",
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        corp_cls="Y",
        report_name="분기보고서",
        receipt_no="20260427000001",
        filing_date="20260427",
        submitter="삼성전자",
        remarks="",
        raw={"corp_name": "삼성전자"},
    )

    class FakeClient:
        def recent_disclosures(self, today=None, lookback_days=7, page_count=100):
            assert lookback_days == 7
            return opendart.OpenDARTDisclosureListResult(
                status="000",
                message="정상",
                page_no=1,
                page_count=100,
                total_count=1,
                items=[item],
            )

    monkeypatch.setattr(opendart.OpenDARTClient, "from_env", classmethod(lambda cls: FakeClient()))

    source = CollectionSource(
        source_id="opendart",
        display_name="OpenDART",
        category="korean_filing_data",
        adapter="official_data.opendart",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, jsonl_path, _ = process.run_once()

    assert manifest.results[0].status == "fetched_disclosures"
    assert manifest.results[0].collected_records == 1
    records_path = tmp_path / manifest.output_partition / "records" / manifest.run_id / "opendart.jsonl"
    assert records_path.exists()
    assert "삼성전자" in records_path.read_text(encoding="utf-8")

    manifest_records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    source_result = next(record for record in manifest_records if record["type"] == "source_result")
    assert source_result["records_path"].endswith("opendart.jsonl")


def test_opendart_missing_credentials_returns_status(monkeypatch, tmp_path):
    monkeypatch.setattr(opendart.OpenDARTClient, "from_env", classmethod(lambda cls: None))
    source = CollectionSource(
        source_id="opendart",
        display_name="OpenDART",
        category="korean_filing_data",
        adapter="official_data.opendart",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, _, _ = process.run_once()

    assert manifest.results[0].status == "missing_credentials"
    assert "OPENDART_API_KEY" in manifest.results[0].message


def test_invalid_opendart_date_rejected():
    client = OpenDARTClient(OpenDARTCredentials("secret"))

    with pytest.raises(ValueError, match="begin_date"):
        client.disclosure_list(begin_date="2026-04-27", end_date="20260427")
