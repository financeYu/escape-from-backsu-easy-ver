"""UN Comtrade official trade data adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from content_research.env import load_dotenv
from content_research.sources.json_api import parse_json_response


UN_COMTRADE_DATA_ENDPOINT = "https://comtradeapi.un.org/data/v1/get/C/A/HS"

DEFAULT_UN_COMTRADE_REPORTERS: tuple[str, ...] = (
    "410",  # Republic of Korea
    "842",  # United States
    "156",  # China
    "392",  # Japan
    "276",  # Germany
)
DEFAULT_UN_COMTRADE_FLOWS: tuple[str, ...] = ("X", "M")


class UNComtradeApiError(RuntimeError):
    """Raised when UN Comtrade returns an error or unexpected response."""


@dataclass(frozen=True)
class UNComtradeCredentials:
    api_key: str

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "UNComtradeCredentials | None":
        load_dotenv(env_path)
        api_key = os.environ.get("UN_COMTRADE_KEY", "").strip() or os.environ.get("COMTRADE_API_KEY", "").strip()
        if not api_key:
            return None
        return cls(api_key=api_key)


@dataclass(frozen=True)
class UNComtradeTradeItem:
    source_id: str
    type_code: str
    frequency_code: str
    classification_code: str
    period: str
    reporter_code: str
    reporter_name: str
    partner_code: str
    partner_name: str
    flow_code: str
    flow_name: str
    commodity_code: str
    commodity_name: str
    primary_value: str
    net_weight: str
    quantity: str
    quantity_unit: str
    is_aggregate: str
    raw: dict[str, Any]
    retrieval_method: str = "un_comtrade_api"
    body_collection_tier: int = 3
    raw_text_storage: str = "official_data_record"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UNComtradeDataResult:
    count: int
    items: list[UNComtradeTradeItem]


class UNComtradeClient:
    def __init__(
        self,
        credentials: UNComtradeCredentials,
        *,
        endpoint: str = UN_COMTRADE_DATA_ENDPOINT,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.credentials = credentials
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "UNComtradeClient | None":
        credentials = UNComtradeCredentials.from_env(env_path)
        if credentials is None:
            return None
        return cls(credentials)

    def trade_data(
        self,
        *,
        reporter_code: str,
        partner_code: str = "0",
        partner2_code: str = "0",
        commodity_code: str = "TOTAL",
        flow_code: str = "X",
        customs_code: str = "C00",
        mode_of_transport_code: str = "0",
        period: str,
        max_records: int = 500,
    ) -> UNComtradeDataResult:
        reporter_code = _validate_numeric_code(reporter_code, "reporter_code")
        partner_code = _validate_numeric_code(partner_code, "partner_code")
        partner2_code = _validate_numeric_code(partner2_code, "partner2_code")
        commodity_code = _validate_code(commodity_code, "commodity_code")
        flow_code = _validate_code(flow_code, "flow_code").upper()
        customs_code = _validate_code(customs_code, "customs_code")
        mode_of_transport_code = _validate_numeric_code(mode_of_transport_code, "mode_of_transport_code")
        period = _validate_period(period)
        if max_records < 1 or max_records > 100000:
            raise ValueError("max_records must be between 1 and 100000")

        data = self._get_json(
            {
                "reporterCode": reporter_code,
                "partnerCode": partner_code,
                "partner2Code": partner2_code,
                "cmdCode": commodity_code,
                "flowCode": flow_code,
                "customsCode": customs_code,
                "motCode": mode_of_transport_code,
                "period": period,
                "maxRecords": str(max_records),
                "includeDesc": "true",
                "format": "json",
            }
        )
        rows = data.get("data", [])
        if rows is None:
            rows = []
        if not isinstance(rows, list):
            raise UNComtradeApiError("Unexpected UN Comtrade data response shape.")
        filtered_rows = [
            row
            for row in rows
            if isinstance(row, dict)
            and _row_matches_total_filters(
                row,
                partner2_code=partner2_code,
                customs_code=customs_code,
                mode_of_transport_code=mode_of_transport_code,
            )
        ]
        return UNComtradeDataResult(
            count=len(filtered_rows),
            items=[_trade_item_from_row(row) for row in filtered_rows],
        )

    def collect_default(
        self,
        *,
        period: str | None = None,
        reporters: tuple[str, ...] = DEFAULT_UN_COMTRADE_REPORTERS,
        flows: tuple[str, ...] = DEFAULT_UN_COMTRADE_FLOWS,
    ) -> list[UNComtradeTradeItem]:
        period = period or str(date.today().year - 2)
        items: list[UNComtradeTradeItem] = []
        for reporter_code in reporters:
            for flow_code in flows:
                result = self.trade_data(reporter_code=reporter_code, flow_code=flow_code, period=period)
                items.extend(result.items)
        return items

    def _get_json(self, params: dict[str, str]) -> dict[str, Any]:
        request = Request(
            f"{self.endpoint}?{urlencode(params)}",
            headers={
                "Accept": "application/json",
                "Ocp-Apim-Subscription-Key": self.credentials.api_key,
                "User-Agent": "content-research-mvp/0.1",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise UNComtradeApiError(f"UN Comtrade HTTP {exc.code}: {_safe_error_detail(detail)}") from exc
        except URLError as exc:
            raise UNComtradeApiError(f"UN Comtrade request failed: {exc.reason}") from exc
        data = parse_json_response(body, "UN Comtrade API", UNComtradeApiError)
        if not isinstance(data, dict):
            raise UNComtradeApiError("Unexpected UN Comtrade response type.")
        _raise_if_comtrade_error(data)
        return data


def _trade_item_from_row(row: dict[str, Any]) -> UNComtradeTradeItem:
    return UNComtradeTradeItem(
        source_id="un_comtrade",
        type_code=_first_present(row, "typeCode"),
        frequency_code=_first_present(row, "freqCode"),
        classification_code=_first_present(row, "clCode", "classificationCode"),
        period=_first_present(row, "period", "refYear"),
        reporter_code=_first_present(row, "reporterCode"),
        reporter_name=_first_present(row, "reporterDesc", "reporterISO"),
        partner_code=_first_present(row, "partnerCode"),
        partner_name=_first_present(row, "partnerDesc", "partnerISO"),
        flow_code=_first_present(row, "flowCode"),
        flow_name=_first_present(row, "flowDesc"),
        commodity_code=_first_present(row, "cmdCode"),
        commodity_name=_first_present(row, "cmdDesc"),
        primary_value=_first_present(row, "primaryValue"),
        net_weight=_first_present(row, "netWgt", "netWeight"),
        quantity=_first_present(row, "qty"),
        quantity_unit=_first_present(row, "qtyUnitAbbr", "qtyUnitCode"),
        is_aggregate=_first_present(row, "isAggregate"),
        raw=row,
    )


def _raise_if_comtrade_error(data: dict[str, Any]) -> None:
    error = data.get("error")
    if isinstance(error, dict):
        code = _first_present(error, "code", "statusCode")
        message = _first_present(error, "message", "details")
        raise UNComtradeApiError(f"UN Comtrade error {code}: {message}")
    if isinstance(error, str) and error.strip():
        raise UNComtradeApiError(f"UN Comtrade error: {error.strip()}")


def _row_matches_total_filters(
    row: dict[str, Any],
    *,
    partner2_code: str,
    customs_code: str,
    mode_of_transport_code: str,
) -> bool:
    row_partner2_code = _first_present(row, "partner2Code")
    row_customs_code = _first_present(row, "customsCode")
    row_mode_of_transport_code = _first_present(row, "motCode")
    return (
        (not row_partner2_code or row_partner2_code == partner2_code)
        and (not row_customs_code or row_customs_code == customs_code)
        and (not row_mode_of_transport_code or row_mode_of_transport_code == mode_of_transport_code)
    )


def _validate_period(value: str) -> str:
    period = value.strip()
    if len(period) != 4 or not period.isdigit():
        raise ValueError("period must be YYYY")
    return period


def _validate_numeric_code(value: str, name: str) -> str:
    code = value.strip()
    if not code.isdigit():
        raise ValueError(f"{name} must be numeric")
    return code


def _validate_code(value: str, name: str) -> str:
    code = value.strip()
    if not code:
        raise ValueError(f"{name} is required")
    return code


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
