"""U.S. EIA official energy data adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from content_research.env import load_dotenv
from content_research.sources.json_api import parse_json_response


EIA_SERIESID_ENDPOINT_PREFIX = "https://api.eia.gov/v2/seriesid"

DEFAULT_EIA_SERIES: tuple[str, ...] = (
    "PET.RWTC.D",
    "PET.RBRTE.D",
    "NG.RNGWHHD.D",
    "PET.EMM_EPM0_PTE_NUS_DPG.W",
    "PET.WCRSTUS1.W",
    "PET.WCESTUS1.W",
    "ELEC.GEN.ALL-US-99.M",
)


class EIAApiError(RuntimeError):
    """Raised when EIA returns an error or unexpected response."""


@dataclass(frozen=True)
class EIACredentials:
    api_key: str

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "EIACredentials | None":
        load_dotenv(env_path)
        api_key = os.environ.get("EIA_API_KEY", "").strip()
        if not api_key:
            return None
        return cls(api_key=api_key)


@dataclass(frozen=True)
class EIAEnergySeriesItem:
    source_id: str
    series_id: str
    period: str
    value: str
    units: str
    value_field: str
    series_description: str
    area_name: str
    product_name: str
    process_name: str
    sector_description: str
    fuel_type_description: str
    raw: dict[str, Any]
    retrieval_method: str = "eia_api_v2_seriesid"
    body_collection_tier: int = 3
    raw_text_storage: str = "official_data_record"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EIAEnergySeriesResult:
    series_id: str
    total: int
    items: list[EIAEnergySeriesItem]


class EIAClient:
    def __init__(
        self,
        credentials: EIACredentials,
        *,
        seriesid_endpoint_prefix: str = EIA_SERIESID_ENDPOINT_PREFIX,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.credentials = credentials
        self.seriesid_endpoint_prefix = seriesid_endpoint_prefix.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "EIAClient | None":
        credentials = EIACredentials.from_env(env_path)
        if credentials is None:
            return None
        return cls(credentials)

    def seriesid(
        self,
        series_id: str,
        *,
        length: int = 12,
    ) -> EIAEnergySeriesResult:
        series_id = _validate_series_id(series_id)
        if length < 1 or length > 5000:
            raise ValueError("length must be between 1 and 5000")

        endpoint = f"{self.seriesid_endpoint_prefix}/{quote(series_id, safe='')}"
        data = self._get_json(endpoint, {"length": str(length)})
        response = data.get("response", {})
        if not isinstance(response, dict):
            raise EIAApiError("Unexpected EIA response shape.")
        rows = response.get("data", [])
        if rows is None:
            rows = []
        if not isinstance(rows, list):
            raise EIAApiError("Unexpected EIA data response shape.")
        return EIAEnergySeriesResult(
            series_id=series_id,
            total=int(response.get("total", len(rows)) or len(rows)),
            items=[_energy_series_item_from_row(row, series_id=series_id) for row in rows if isinstance(row, dict)],
        )

    def collect_default(
        self,
        series_ids: tuple[str, ...] = DEFAULT_EIA_SERIES,
        *,
        length_per_series: int = 12,
    ) -> list[EIAEnergySeriesItem]:
        items: list[EIAEnergySeriesItem] = []
        for series_id in series_ids:
            result = self.seriesid(series_id, length=length_per_series)
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
            raise EIAApiError(f"EIA HTTP {exc.code}: {_safe_error_detail(detail)}") from exc
        except URLError as exc:
            raise EIAApiError(f"EIA request failed: {exc.reason}") from exc
        data = parse_json_response(body, "EIA API", EIAApiError)
        if not isinstance(data, dict):
            raise EIAApiError("Unexpected EIA response type.")
        _raise_if_eia_error(data)
        return data


def _energy_series_item_from_row(row: dict[str, Any], *, series_id: str) -> EIAEnergySeriesItem:
    value_field = _value_field_from_row(row)
    return EIAEnergySeriesItem(
        source_id="eia",
        series_id=series_id,
        period=_first_present(row, "period"),
        value=_first_present(row, value_field),
        units=_first_present(row, f"{value_field}-units", "units"),
        value_field=value_field,
        series_description=_first_present(row, "series-description", "seriesDescription"),
        area_name=_first_present(row, "area-name", "areaName", "stateDescription"),
        product_name=_first_present(row, "product-name", "productName"),
        process_name=_first_present(row, "process-name", "processName"),
        sector_description=_first_present(row, "sectorDescription"),
        fuel_type_description=_first_present(row, "fuelTypeDescription"),
        raw=row,
    )


def _value_field_from_row(row: dict[str, Any]) -> str:
    if "value" in row:
        return "value"
    for key in row:
        if key.endswith("-units"):
            value_key = key[: -len("-units")]
            if value_key in row:
                return value_key
    known_metadata = {
        "period",
        "duoarea",
        "area-name",
        "product",
        "product-name",
        "process",
        "process-name",
        "series",
        "series-description",
        "location",
        "stateDescription",
        "sectorid",
        "sectorDescription",
        "fueltypeid",
        "fuelTypeDescription",
    }
    for key in row:
        if key not in known_metadata and not key.endswith("-units"):
            return key
    return "value"


def _validate_series_id(series_id: str) -> str:
    value = series_id.strip().upper()
    if not value:
        raise ValueError("series_id is required")
    return value


def _raise_if_eia_error(data: dict[str, Any]) -> None:
    error = data.get("error")
    if isinstance(error, dict):
        code = _first_present(error, "code")
        message = _first_present(error, "message")
        raise EIAApiError(f"EIA error {code}: {message}")
    if isinstance(error, str) and error.strip():
        raise EIAApiError(f"EIA error: {error.strip()}")
    response = data.get("response", {})
    if isinstance(response, dict) and isinstance(response.get("error"), str) and response["error"].strip():
        raise EIAApiError(f"EIA error: {response['error'].strip()}")


def _first_present(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return str(value).strip()
    return ""


def _safe_error_detail(value: str) -> str:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return value[:300]
    return json.dumps(data, ensure_ascii=False)[:300]
