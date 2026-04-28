"""FRED official data adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from content_research.env import load_dotenv


FRED_SERIES_ENDPOINT = "https://api.stlouisfed.org/fred/series"
FRED_SERIES_OBSERVATIONS_ENDPOINT = "https://api.stlouisfed.org/fred/series/observations"

DEFAULT_FRED_SERIES: tuple[str, ...] = (
    "FEDFUNDS",
    "DFF",
    "DGS10",
    "DGS2",
    "CPIAUCSL",
    "PCEPI",
    "UNRATE",
    "PAYEMS",
    "GDPC1",
    "INDPRO",
    "RSAFS",
    "HOUST",
)


class FREDApiError(RuntimeError):
    """Raised when FRED returns an error or unexpected response."""


@dataclass(frozen=True)
class FREDCredentials:
    api_key: str

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "FREDCredentials | None":
        load_dotenv(env_path)
        api_key = os.environ.get("FRED_API_KEY", "").strip()
        if not api_key:
            return None
        return cls(api_key=api_key)


@dataclass(frozen=True)
class FREDSeriesMetadata:
    series_id: str
    title: str
    frequency: str
    frequency_short: str
    units: str
    units_short: str
    seasonal_adjustment: str
    last_updated: str
    observation_start: str
    observation_end: str
    popularity: str
    notes: str
    realtime_start: str
    realtime_end: str


@dataclass(frozen=True)
class FREDObservationItem:
    source_id: str
    series_id: str
    title: str
    observation_date: str
    value: str
    realtime_start: str
    realtime_end: str
    frequency: str
    frequency_short: str
    units: str
    units_short: str
    seasonal_adjustment: str
    last_updated: str
    retrieval_method: str = "fred_api"
    body_collection_tier: int = 3
    raw_text_storage: str = "official_data_record"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FREDObservationResult:
    series_id: str
    count: int
    items: list[FREDObservationItem]


class FREDClient:
    def __init__(
        self,
        credentials: FREDCredentials,
        *,
        series_endpoint: str = FRED_SERIES_ENDPOINT,
        observations_endpoint: str = FRED_SERIES_OBSERVATIONS_ENDPOINT,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.credentials = credentials
        self.series_endpoint = series_endpoint
        self.observations_endpoint = observations_endpoint
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "FREDClient | None":
        credentials = FREDCredentials.from_env(env_path)
        if credentials is None:
            return None
        return cls(credentials)

    def series_metadata(self, series_id: str) -> FREDSeriesMetadata:
        series_id = _validate_series_id(series_id)
        data = self._get_json(
            self.series_endpoint,
            {
                "series_id": series_id,
                "file_type": "json",
            },
        )
        seriess = data.get("seriess", [])
        if not isinstance(seriess, list) or not seriess:
            raise FREDApiError(f"FRED series metadata not found for {series_id}.")
        first = seriess[0]
        if not isinstance(first, dict):
            raise FREDApiError("Unexpected FRED series metadata response shape.")
        return _series_metadata_from_response(first)

    def observations(
        self,
        series_id: str,
        *,
        limit: int = 12,
        sort_order: str = "desc",
    ) -> FREDObservationResult:
        series_id = _validate_series_id(series_id)
        if limit < 1 or limit > 100000:
            raise ValueError("limit must be between 1 and 100000")
        if sort_order not in {"asc", "desc"}:
            raise ValueError("sort_order must be asc or desc")

        metadata = self.series_metadata(series_id)
        data = self._get_json(
            self.observations_endpoint,
            {
                "series_id": series_id,
                "file_type": "json",
                "limit": str(limit),
                "sort_order": sort_order,
            },
        )
        observations = data.get("observations", [])
        if observations is None:
            observations = []
        if not isinstance(observations, list):
            raise FREDApiError("Unexpected FRED observations response shape.")
        return FREDObservationResult(
            series_id=series_id,
            count=int(data.get("count", len(observations)) or 0),
            items=[
                _observation_from_response(observation, metadata)
                for observation in observations
                if isinstance(observation, dict)
            ],
        )

    def collect_default(
        self,
        series_ids: tuple[str, ...] = DEFAULT_FRED_SERIES,
        *,
        limit_per_series: int = 12,
    ) -> list[FREDObservationItem]:
        items: list[FREDObservationItem] = []
        for series_id in series_ids:
            result = self.observations(series_id, limit=limit_per_series, sort_order="desc")
            items.extend(result.items)
        return items

    def _get_json(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        query = {"api_key": self.credentials.api_key, **params}
        request = Request(
            f"{endpoint}?{urlencode(query)}",
            headers={
                "Accept": "application/json",
                "User-Agent": "content-research-mvp/0.1",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise FREDApiError(f"FRED HTTP {exc.code}: {_safe_error_detail(detail)}") from exc
        except URLError as exc:
            raise FREDApiError(f"FRED request failed: {exc.reason}") from exc
        data = json.loads(body)
        if not isinstance(data, dict):
            raise FREDApiError("Unexpected FRED response type.")
        _raise_if_fred_error(data)
        return data


def _validate_series_id(series_id: str) -> str:
    value = series_id.strip().upper()
    if not value:
        raise ValueError("series_id is required")
    return value


def _series_metadata_from_response(value: dict[str, Any]) -> FREDSeriesMetadata:
    return FREDSeriesMetadata(
        series_id=_as_str(value.get("id")),
        title=_as_str(value.get("title")),
        frequency=_as_str(value.get("frequency")),
        frequency_short=_as_str(value.get("frequency_short")),
        units=_as_str(value.get("units")),
        units_short=_as_str(value.get("units_short")),
        seasonal_adjustment=_as_str(value.get("seasonal_adjustment")),
        last_updated=_as_str(value.get("last_updated")),
        observation_start=_as_str(value.get("observation_start")),
        observation_end=_as_str(value.get("observation_end")),
        popularity=_as_str(value.get("popularity")),
        notes=_as_str(value.get("notes")),
        realtime_start=_as_str(value.get("realtime_start")),
        realtime_end=_as_str(value.get("realtime_end")),
    )


def _observation_from_response(value: dict[str, Any], metadata: FREDSeriesMetadata) -> FREDObservationItem:
    return FREDObservationItem(
        source_id="fred",
        series_id=metadata.series_id,
        title=metadata.title,
        observation_date=_as_str(value.get("date")),
        value=_as_str(value.get("value")),
        realtime_start=_as_str(value.get("realtime_start")) or metadata.realtime_start,
        realtime_end=_as_str(value.get("realtime_end")) or metadata.realtime_end,
        frequency=metadata.frequency,
        frequency_short=metadata.frequency_short,
        units=metadata.units,
        units_short=metadata.units_short,
        seasonal_adjustment=metadata.seasonal_adjustment,
        last_updated=metadata.last_updated,
    )


def _raise_if_fred_error(data: dict[str, Any]) -> None:
    if "error_code" in data or "error_message" in data:
        code = _as_str(data.get("error_code"))
        message = _as_str(data.get("error_message"))
        raise FREDApiError(f"FRED error {code}: {message}")


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_error_detail(value: str) -> str:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return value[:300]
    return json.dumps(data, ensure_ascii=False)[:300]
