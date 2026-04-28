"""OpenDART disclosure search adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from content_research.env import load_dotenv
from content_research.sources.json_api import parse_json_response


OPENDART_DISCLOSURE_LIST_ENDPOINT = "https://opendart.fss.or.kr/api/list.json"


class OpenDARTApiError(RuntimeError):
    """Raised when OpenDART returns an error or unexpected response."""


@dataclass(frozen=True)
class OpenDARTCredentials:
    api_key: str

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "OpenDARTCredentials | None":
        load_dotenv(env_path)
        api_key = os.environ.get("OPENDART_API_KEY", "").strip()
        if not api_key:
            return None
        return cls(api_key=api_key)


@dataclass(frozen=True)
class OpenDARTDisclosureItem:
    source_id: str
    corp_code: str
    corp_name: str
    stock_code: str
    corp_cls: str
    report_name: str
    receipt_no: str
    filing_date: str
    submitter: str
    remarks: str
    raw: dict[str, Any]
    retrieval_method: str = "opendart_disclosure_list"
    body_collection_tier: int = 3
    raw_text_storage: str = "official_disclosure_metadata"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OpenDARTDisclosureListResult:
    status: str
    message: str
    page_no: int
    page_count: int
    total_count: int
    items: list[OpenDARTDisclosureItem]


class OpenDARTClient:
    def __init__(
        self,
        credentials: OpenDARTCredentials,
        *,
        endpoint: str = OPENDART_DISCLOSURE_LIST_ENDPOINT,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.credentials = credentials
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "OpenDARTClient | None":
        credentials = OpenDARTCredentials.from_env(env_path)
        if credentials is None:
            return None
        return cls(credentials)

    def disclosure_list(
        self,
        *,
        begin_date: str,
        end_date: str,
        page_no: int = 1,
        page_count: int = 100,
        corporation_class: str | None = None,
    ) -> OpenDARTDisclosureListResult:
        _validate_yyyymmdd(begin_date, "begin_date")
        _validate_yyyymmdd(end_date, "end_date")
        if page_no < 1:
            raise ValueError("page_no must be positive")
        if page_count < 1 or page_count > 100:
            raise ValueError("page_count must be between 1 and 100")

        params = {
            "crtfc_key": self.credentials.api_key,
            "bgn_de": begin_date,
            "end_de": end_date,
            "page_no": str(page_no),
            "page_count": str(page_count),
        }
        if corporation_class:
            params["corp_cls"] = corporation_class

        data = self._get_json(params)
        _raise_if_opendart_error(data)
        rows = data.get("list", [])
        if rows is None:
            rows = []
        if not isinstance(rows, list):
            raise OpenDARTApiError("Unexpected OpenDART list response shape.")
        return OpenDARTDisclosureListResult(
            status=str(data.get("status", "")),
            message=str(data.get("message", "")),
            page_no=int(data.get("page_no", page_no) or page_no),
            page_count=int(data.get("page_count", page_count) or page_count),
            total_count=int(data.get("total_count", len(rows)) or 0),
            items=[_disclosure_item_from_row(row) for row in rows if isinstance(row, dict)],
        )

    def recent_disclosures(
        self,
        *,
        today: date | None = None,
        lookback_days: int = 7,
        page_count: int = 100,
    ) -> OpenDARTDisclosureListResult:
        if lookback_days < 0:
            raise ValueError("lookback_days must be non-negative")
        today = today or date.today()
        begin = today - timedelta(days=lookback_days)
        return self.disclosure_list(
            begin_date=begin.strftime("%Y%m%d"),
            end_date=today.strftime("%Y%m%d"),
            page_count=page_count,
        )

    def _get_json(self, params: dict[str, str]) -> dict[str, Any]:
        request = Request(
            f"{self.endpoint}?{urlencode(params)}",
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
            raise OpenDARTApiError(f"OpenDART API HTTP {exc.code}: {_safe_error_detail(detail)}") from exc
        except URLError as exc:
            raise OpenDARTApiError(f"OpenDART API request failed: {exc.reason}") from exc
        data = parse_json_response(body, "OpenDART API", OpenDARTApiError)
        if not isinstance(data, dict):
            raise OpenDARTApiError("Unexpected OpenDART response type.")
        return data


def _disclosure_item_from_row(row: dict[str, Any]) -> OpenDARTDisclosureItem:
    return OpenDARTDisclosureItem(
        source_id="opendart",
        corp_code=_first_present(row, "corp_code"),
        corp_name=_first_present(row, "corp_name"),
        stock_code=_first_present(row, "stock_code"),
        corp_cls=_first_present(row, "corp_cls"),
        report_name=_first_present(row, "report_nm"),
        receipt_no=_first_present(row, "rcept_no"),
        filing_date=_first_present(row, "rcept_dt"),
        submitter=_first_present(row, "flr_nm"),
        remarks=_first_present(row, "rm"),
        raw=row,
    )


def _first_present(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return str(value).strip()
    return ""


def _raise_if_opendart_error(data: dict[str, Any]) -> None:
    status = str(data.get("status", "")).strip()
    if status and status not in {"000", "013"}:
        message = str(data.get("message", "")).strip()
        raise OpenDARTApiError(f"OpenDART API error {status}: {message}")


def _validate_yyyymmdd(value: str, name: str) -> None:
    if len(value) != 8 or not value.isdigit():
        raise ValueError(f"{name} must be YYYYMMDD")


def _safe_error_detail(value: str) -> str:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return value[:300]
    return json.dumps(data, ensure_ascii=False)[:300]
