import json

import pytest

from content_research.collection.catalog import CollectionSource
from content_research.collection.process import HourlyCollectionProcess
from content_research.sources.official_data import eia
from content_research.sources.official_data.eia import EIAClient, EIACredentials


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_eia_seriesid_parses_value_rows(monkeypatch):
    payload = {
        "response": {
            "total": 1,
            "data": [
                {
                    "period": "2026-04-20",
                    "duoarea": "YCUOK",
                    "area-name": "NA",
                    "product-name": "WTI Crude Oil",
                    "process-name": "Spot Price FOB",
                    "series-description": "Cushing, OK WTI Spot Price FOB (Dollars per Barrel)",
                    "value": 91.06,
                    "units": "$/BBL",
                }
            ],
        }
    }

    def fake_urlopen(request, timeout):
        assert "/v2/seriesid/PET.RWTC.D" in request.full_url
        assert "api_key=secret" in request.full_url
        assert "length=1" in request.full_url
        return FakeResponse(payload)

    monkeypatch.setattr(eia, "urlopen", fake_urlopen)

    client = EIAClient(EIACredentials("secret"))
    result = client.seriesid("pet.rwtc.d", length=1)

    assert result.total == 1
    assert result.items[0].series_id == "PET.RWTC.D"
    assert result.items[0].value == "91.06"
    assert result.items[0].units == "$/BBL"
    assert result.items[0].value_field == "value"
    assert result.items[0].body_collection_tier == 3


def test_eia_seriesid_parses_metric_specific_units(monkeypatch):
    payload = {
        "response": {
            "total": 1,
            "data": [
                {
                    "period": "2026-02",
                    "location": "US",
                    "stateDescription": "U.S. Total",
                    "sectorDescription": "All Sectors",
                    "fuelTypeDescription": "all fuels",
                    "generation": 342800.61492,
                    "generation-units": "thousand megawatthours",
                }
            ],
        }
    }

    def fake_urlopen(request, timeout):
        assert "/v2/seriesid/ELEC.GEN.ALL-US-99.M" in request.full_url
        return FakeResponse(payload)

    monkeypatch.setattr(eia, "urlopen", fake_urlopen)

    client = EIAClient(EIACredentials("secret"))
    result = client.seriesid("ELEC.GEN.ALL-US-99.M", length=1)

    assert result.items[0].value == "342800.61492"
    assert result.items[0].units == "thousand megawatthours"
    assert result.items[0].value_field == "generation"
    assert result.items[0].area_name == "U.S. Total"


def test_collection_process_writes_eia_records(monkeypatch, tmp_path):
    item = eia.EIAEnergySeriesItem(
        source_id="eia",
        series_id="PET.RWTC.D",
        period="2026-04-20",
        value="91.06",
        units="$/BBL",
        value_field="value",
        series_description="Cushing, OK WTI Spot Price FOB (Dollars per Barrel)",
        area_name="NA",
        product_name="WTI Crude Oil",
        process_name="Spot Price FOB",
        sector_description="",
        fuel_type_description="",
        raw={"period": "2026-04-20"},
    )

    class FakeClient:
        def collect_default(self):
            return [item]

    monkeypatch.setattr(eia.EIAClient, "from_env", classmethod(lambda cls: FakeClient()))

    source = CollectionSource(
        source_id="eia",
        display_name="U.S. Energy Information Administration API",
        category="us_energy_data",
        adapter="official_data.eia",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, jsonl_path, _ = process.run_once()

    assert manifest.results[0].status == "fetched_energy_series"
    assert manifest.results[0].collected_records == 1
    records_path = tmp_path / manifest.output_partition / "records" / "eia.jsonl"
    assert records_path.exists()
    assert "WTI Crude Oil" in records_path.read_text(encoding="utf-8")

    manifest_records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    source_result = next(record for record in manifest_records if record["type"] == "source_result")
    assert source_result["records_path"].endswith("eia.jsonl")


def test_eia_missing_credentials_returns_status(monkeypatch, tmp_path):
    monkeypatch.setattr(eia.EIAClient, "from_env", classmethod(lambda cls: None))
    source = CollectionSource(
        source_id="eia",
        display_name="U.S. Energy Information Administration API",
        category="us_energy_data",
        adapter="official_data.eia",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, _, _ = process.run_once()

    assert manifest.results[0].status == "missing_credentials"
    assert "EIA_API_KEY" in manifest.results[0].message


def test_invalid_eia_length_rejected():
    client = EIAClient(EIACredentials("secret"))

    with pytest.raises(ValueError, match="length"):
        client.seriesid("PET.RWTC.D", length=0)
