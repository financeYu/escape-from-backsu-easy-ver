import json

import pytest

from content_research.collection.catalog import CollectionSource
from content_research.collection.process import HourlyCollectionProcess
from content_research.sources.official_data import kosis
from content_research.sources.official_data.kosis import KOSISClient, KOSISCredentials


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_kosis_statistics_list_parses_rows(monkeypatch):
    payload = [
        {
            "VW_CD": "MT_ZTITLE",
            "VW_NM": "국내통계 주제별",
            "LIST_ID": "A",
            "LIST_NM": "인구",
            "ORG_ID": "",
            "TBL_ID": "",
            "TBL_NM": "",
            "STAT_ID": "",
            "SEND_DE": "20260427",
            "REC_TBL_SE": "",
        }
    ]

    def fake_urlopen(request, timeout):
        assert "statisticsList.do" in request.full_url
        assert "apiKey=secret" in request.full_url
        assert "vwCd=MT_ZTITLE" in request.full_url
        return FakeResponse(payload)

    monkeypatch.setattr(kosis, "urlopen", fake_urlopen)

    client = KOSISClient(KOSISCredentials("secret"))
    result = client.statistics_list()

    assert result.items[0].list_name == "인구"
    assert result.items[0].view_code == "MT_ZTITLE"
    assert result.items[0].body_collection_tier == 3


def test_kosis_credentials_adds_base64_decoded_candidate():
    credentials = KOSISCredentials("YmE4NzhlOTEwZTVmYzYyZGQyYjQ3MzVhNTk0NGZjZmU")

    assert credentials.candidates()[0].startswith("YmE")
    assert credentials.candidates()[1] == "ba878e910e5fc62dd2b4735a5944fcfe"


def test_collection_process_writes_kosis_records(monkeypatch, tmp_path):
    item = kosis.KOSISStatisticsListItem(
        source_id="kosis",
        view_code="MT_ZTITLE",
        view_name="국내통계 주제별",
        list_id="A",
        list_name="인구",
        organization_id="",
        table_id="",
        table_name="",
        statistics_id="",
        updated_at="20260427",
        recommended_table="",
        raw={"LIST_NM": "인구"},
    )

    class FakeClient:
        def statistics_list(self, view_code="MT_ZTITLE", parent_id="", content=None):
            assert view_code == "MT_ZTITLE"
            assert parent_id == ""
            return kosis.KOSISStatisticsListResult(view_code=view_code, parent_id=parent_id, items=[item])

    monkeypatch.setattr(kosis.KOSISClient, "from_env", classmethod(lambda cls: FakeClient()))

    source = CollectionSource(
        source_id="kosis",
        display_name="KOSIS OpenAPI",
        category="korean_official_data",
        adapter="official_data.kosis",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, jsonl_path, _ = process.run_once()

    assert manifest.results[0].status == "fetched_catalog"
    assert manifest.results[0].collected_records == 1
    records_path = tmp_path / manifest.output_partition / "records" / "kosis.jsonl"
    assert records_path.exists()
    assert "인구" in records_path.read_text(encoding="utf-8")

    manifest_records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    source_result = next(record for record in manifest_records if record["type"] == "source_result")
    assert source_result["records_path"].endswith("kosis.jsonl")


def test_kosis_missing_credentials_returns_status(monkeypatch, tmp_path):
    monkeypatch.setattr(kosis.KOSISClient, "from_env", classmethod(lambda cls: None))
    source = CollectionSource(
        source_id="kosis",
        display_name="KOSIS OpenAPI",
        category="korean_official_data",
        adapter="official_data.kosis",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, _, _ = process.run_once()

    assert manifest.results[0].status == "missing_credentials"
    assert "KOSIS_API_KEY" in manifest.results[0].message


def test_invalid_kosis_view_code_rejected():
    client = KOSISClient(KOSISCredentials("secret"))

    with pytest.raises(ValueError, match="view_code"):
        client.statistics_list(view_code="")
