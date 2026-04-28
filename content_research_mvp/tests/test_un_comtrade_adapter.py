import json

import pytest

from content_research.collection.catalog import CollectionSource
from content_research.collection.process import HourlyCollectionProcess
from content_research.sources.official_data import un_comtrade
from content_research.sources.official_data.un_comtrade import UNComtradeClient, UNComtradeCredentials


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_un_comtrade_trade_data_parses_rows(monkeypatch):
    payload = {
        "count": 1,
        "data": [
            {
                "typeCode": "C",
                "freqCode": "A",
                "clCode": "HS",
                "period": "2024",
                "reporterCode": 410,
                "reporterDesc": "Rep. of Korea",
                "partnerCode": 0,
                "partnerDesc": "World",
                "flowCode": "X",
                "flowDesc": "Export",
                "cmdCode": "TOTAL",
                "cmdDesc": "All Commodities",
                "primaryValue": 683500000000,
                "netWgt": 0,
                "qty": 0,
                "qtyUnitAbbr": "",
                "isAggregate": True,
            }
        ],
    }

    def fake_urlopen(request, timeout):
        assert "comtradeapi.un.org/data/v1/get/C/A/HS" in request.full_url
        assert "reporterCode=410" in request.full_url
        assert "partnerCode=0" in request.full_url
        assert "partner2Code=0" in request.full_url
        assert "cmdCode=TOTAL" in request.full_url
        assert "flowCode=X" in request.full_url
        assert "customsCode=C00" in request.full_url
        assert "motCode=0" in request.full_url
        assert "period=2024" in request.full_url
        assert request.headers["Ocp-apim-subscription-key"] == "secret"
        return FakeResponse(payload)

    monkeypatch.setattr(un_comtrade, "urlopen", fake_urlopen)

    client = UNComtradeClient(UNComtradeCredentials("secret"))
    result = client.trade_data(reporter_code="410", flow_code="X", period="2024")

    assert result.count == 1
    assert result.items[0].source_id == "un_comtrade"
    assert result.items[0].reporter_name == "Rep. of Korea"
    assert result.items[0].flow_name == "Export"
    assert result.items[0].commodity_code == "TOTAL"
    assert result.items[0].primary_value == "683500000000"
    assert result.items[0].body_collection_tier == 3


def test_collection_process_writes_un_comtrade_records(monkeypatch, tmp_path):
    item = un_comtrade.UNComtradeTradeItem(
        source_id="un_comtrade",
        type_code="C",
        frequency_code="A",
        classification_code="HS",
        period="2024",
        reporter_code="410",
        reporter_name="Rep. of Korea",
        partner_code="0",
        partner_name="World",
        flow_code="X",
        flow_name="Export",
        commodity_code="TOTAL",
        commodity_name="All Commodities",
        primary_value="683500000000",
        net_weight="",
        quantity="",
        quantity_unit="",
        is_aggregate="True",
        raw={"reporterCode": 410},
    )

    class FakeClient:
        def collect_default(self):
            return [item]

    monkeypatch.setattr(un_comtrade.UNComtradeClient, "from_env", classmethod(lambda cls: FakeClient()))

    source = CollectionSource(
        source_id="un_comtrade",
        display_name="UN Comtrade",
        category="international_trade_data",
        adapter="official_data.un_comtrade",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, jsonl_path, _ = process.run_once()

    assert manifest.results[0].status == "fetched_trade_data"
    assert manifest.results[0].collected_records == 1
    records_path = tmp_path / manifest.output_partition / "records" / manifest.run_id / "un_comtrade.jsonl"
    assert records_path.exists()
    assert "Rep. of Korea" in records_path.read_text(encoding="utf-8")

    manifest_records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    source_result = next(record for record in manifest_records if record["type"] == "source_result")
    assert source_result["records_path"].endswith("un_comtrade.jsonl")


def test_un_comtrade_missing_credentials_returns_status(monkeypatch, tmp_path):
    monkeypatch.setattr(un_comtrade.UNComtradeClient, "from_env", classmethod(lambda cls: None))
    source = CollectionSource(
        source_id="un_comtrade",
        display_name="UN Comtrade",
        category="international_trade_data",
        adapter="official_data.un_comtrade",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, _, _ = process.run_once()

    assert manifest.results[0].status == "missing_credentials"
    assert "UN_COMTRADE_KEY" in manifest.results[0].message


def test_invalid_un_comtrade_period_rejected():
    client = UNComtradeClient(UNComtradeCredentials("secret"))

    with pytest.raises(ValueError, match="period"):
        client.trade_data(reporter_code="410", flow_code="X", period="24")
