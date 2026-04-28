import json

import pytest

from content_research.collection.catalog import CollectionSource
from content_research.collection.process import HourlyCollectionProcess
from content_research.sources.official_data import fred
from content_research.sources.official_data.fred import FREDClient, FREDCredentials


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_fred_series_metadata_parses(monkeypatch):
    payload = {
        "seriess": [
            {
                "id": "FEDFUNDS",
                "title": "Federal Funds Effective Rate",
                "frequency": "Monthly",
                "frequency_short": "M",
                "units": "Percent",
                "units_short": "%",
                "seasonal_adjustment": "Not Seasonally Adjusted",
                "last_updated": "2026-04-01 15:16:02-05",
                "observation_start": "1954-07-01",
                "observation_end": "2026-03-01",
                "popularity": 95,
                "notes": "A rate series.",
                "realtime_start": "2026-04-27",
                "realtime_end": "2026-04-27",
            }
        ]
    }

    def fake_urlopen(request, timeout):
        assert "/fred/series?" in request.full_url
        assert "series_id=FEDFUNDS" in request.full_url
        assert "api_key=secret" in request.full_url
        assert "file_type=json" in request.full_url
        return FakeResponse(payload)

    monkeypatch.setattr(fred, "urlopen", fake_urlopen)

    client = FREDClient(FREDCredentials("secret"))
    result = client.series_metadata("fedfunds")

    assert result.series_id == "FEDFUNDS"
    assert result.title == "Federal Funds Effective Rate"
    assert result.frequency_short == "M"


def test_fred_observations_parses_rows(monkeypatch):
    metadata_payload = {
        "seriess": [
            {
                "id": "FEDFUNDS",
                "title": "Federal Funds Effective Rate",
                "frequency": "Monthly",
                "frequency_short": "M",
                "units": "Percent",
                "units_short": "%",
                "seasonal_adjustment": "Not Seasonally Adjusted",
                "last_updated": "2026-04-01 15:16:02-05",
                "realtime_start": "2026-04-27",
                "realtime_end": "2026-04-27",
            }
        ]
    }
    observations_payload = {
        "count": 1,
        "observations": [
            {
                "realtime_start": "2026-04-27",
                "realtime_end": "2026-04-27",
                "date": "2026-03-01",
                "value": "4.33",
            }
        ],
    }

    def fake_urlopen(request, timeout):
        if "/fred/series/observations?" in request.full_url:
            assert "limit=1" in request.full_url
            assert "sort_order=desc" in request.full_url
            return FakeResponse(observations_payload)
        return FakeResponse(metadata_payload)

    monkeypatch.setattr(fred, "urlopen", fake_urlopen)

    client = FREDClient(FREDCredentials("secret"))
    result = client.observations("FEDFUNDS", limit=1)

    assert result.count == 1
    assert result.items[0].series_id == "FEDFUNDS"
    assert result.items[0].title == "Federal Funds Effective Rate"
    assert result.items[0].observation_date == "2026-03-01"
    assert result.items[0].value == "4.33"
    assert result.items[0].body_collection_tier == 3


def test_collection_process_writes_fred_records(monkeypatch, tmp_path):
    item = fred.FREDObservationItem(
        source_id="fred",
        series_id="FEDFUNDS",
        title="Federal Funds Effective Rate",
        observation_date="2026-03-01",
        value="4.33",
        realtime_start="2026-04-27",
        realtime_end="2026-04-27",
        frequency="Monthly",
        frequency_short="M",
        units="Percent",
        units_short="%",
        seasonal_adjustment="Not Seasonally Adjusted",
        last_updated="2026-04-01 15:16:02-05",
    )

    class FakeClient:
        def collect_default(self):
            return [item]

    monkeypatch.setattr(fred.FREDClient, "from_env", classmethod(lambda cls: FakeClient()))

    source = CollectionSource(
        source_id="fred",
        display_name="FRED API",
        category="us_official_data",
        adapter="official_data.fred",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, jsonl_path, _ = process.run_once()

    assert manifest.results[0].status == "fetched_observations"
    assert manifest.results[0].collected_records == 1
    records_path = tmp_path / manifest.output_partition / "records" / manifest.run_id / "fred.jsonl"
    assert records_path.exists()
    assert "Federal Funds Effective Rate" in records_path.read_text(encoding="utf-8")

    manifest_records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    source_result = next(record for record in manifest_records if record["type"] == "source_result")
    assert source_result["records_path"].endswith("fred.jsonl")


def test_fred_missing_credentials_returns_status(monkeypatch, tmp_path):
    monkeypatch.setattr(fred.FREDClient, "from_env", classmethod(lambda cls: None))
    source = CollectionSource(
        source_id="fred",
        display_name="FRED API",
        category="us_official_data",
        adapter="official_data.fred",
        access_method="api",
        default_body_tier=3,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, _, _ = process.run_once()

    assert manifest.results[0].status == "missing_credentials"
    assert "FRED_API_KEY" in manifest.results[0].message


def test_invalid_fred_limit_rejected():
    client = FREDClient(FREDCredentials("secret"))

    with pytest.raises(ValueError, match="limit"):
        client.observations("FEDFUNDS", limit=0)
