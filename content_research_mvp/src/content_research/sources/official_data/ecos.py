"""Bank of Korea ECOS Open API adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from content_research.env import load_dotenv
from content_research.sources.json_api import parse_json_response


ECOS_API_BASE_URL = "https://ecos.bok.or.kr/api"


class ECOSApiError(RuntimeError):
    """Raised when an ECOS API request fails."""


@dataclass(frozen=True)
class ECOSCredentials:
    api_key: str

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "ECOSCredentials | None":
        load_dotenv(env_path)
        api_key = os.environ.get("ECOS_API_KEY", "").strip()
        if not api_key:
            return None
        return cls(api_key=api_key)


@dataclass(frozen=True)
class ECOSKeyStatisticItem:
    source_id: str
    statistic_name: str
    data_value: str
    unit_name: str
    cycle: str
    class_name: str
    raw: dict[str, Any]
    retrieval_method: str = "ecos_key_statistic_list"
    body_collection_tier: int = 3
    raw_text_storage: str = "official_data_record"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ECOSKeyStatisticResult:
    list_total_count: int
    items: list[ECOSKeyStatisticItem]


class ECOSClient:
    def __init__(
        self,
        credentials: ECOSCredentials,
        *,
        base_url: str = ECOS_API_BASE_URL,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.credentials = credentials
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "ECOSClient | None":
        credentials = ECOSCredentials.from_env(env_path)
        if credentials is None:
            return None
        return cls(credentials)

    def key_statistics(
        self,
        *,
        start: int = 1,
        end: int = 100,
        language: str = "kr",
    ) -> ECOSKeyStatisticResult:
        if start < 1:
            raise ValueError("start must be positive")
        if end < start:
            raise ValueError("end must be greater than or equal to start")
        if language not in {"kr", "en"}:
            raise ValueError("language must be 'kr' or 'en'")

        data = self._get_json(f"KeyStatisticList/json/{language}/{start}/{end}")
        payload = data.get("KeyStatisticList", {}) if isinstance(data, dict) else {}
        if not isinstance(payload, dict):
            raise ECOSApiError("Unexpected ECOS KeyStatisticList response shape.")
        _raise_if_ecos_error(payload)
        rows = payload.get("row", [])
        if isinstance(rows, dict):
            rows = [rows]
        items = [
            _key_statistic_item_from_row(row)
            for row in rows
            if isinstance(row, dict)
        ]
        return ECOSKeyStatisticResult(
            list_total_count=int(payload.get("list_total_count", len(items)) or 0),
            items=items,
        )

    def _get_json(self, path: str) -> dict[str, Any]:
        service, rest = path.split("/", 1)
        endpoint = f"{self.base_url}/{service}/{self.credentials.api_key}/{rest}"
        request = Request(
            endpoint,
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
            raise ECOSApiError(f"ECOS API HTTP {exc.code}: {_safe_error_detail(detail)}") from exc
        except URLError as exc:
            raise ECOSApiError(f"ECOS API request failed: {exc.reason}") from exc
        data = parse_json_response(body, "ECOS API", ECOSApiError)
        if isinstance(data, dict) and "RESULT" in data:
            _raise_if_ecos_error(data)
        return data


def _key_statistic_item_from_row(row: dict[str, Any]) -> ECOSKeyStatisticItem:
    return ECOSKeyStatisticItem(
        source_id="ecos",
        statistic_name=_first_present(row, "KEYSTAT_NAME", "STAT_NAME", "STATISTICS_NAME"),
        data_value=_first_present(row, "DATA_VALUE", "VALUE"),
        unit_name=_first_present(row, "UNIT_NAME", "UNIT"),
        cycle=_first_present(row, "CYCLE"),
        class_name=_first_present(row, "CLASS_NAME", "CLASS"),
        raw=row,
    )


def _first_present(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return str(value).strip()
    return ""


def _raise_if_ecos_error(payload: dict[str, Any]) -> None:
    result = payload.get("RESULT")
    if not isinstance(result, dict):
        return
    code = str(result.get("CODE", "")).strip()
    if code and code not in {"INFO-000"}:
        message = str(result.get("MESSAGE", "")).strip()
        raise ECOSApiError(f"ECOS API error {code}: {message}")


def _safe_error_detail(value: str) -> str:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return value[:300]
    return json.dumps(data, ensure_ascii=False)[:300]
