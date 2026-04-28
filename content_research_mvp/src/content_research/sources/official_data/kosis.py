"""KOSIS OpenAPI adapter."""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from content_research.env import load_dotenv


KOSIS_STATISTICS_LIST_ENDPOINT = "https://kosis.kr/openapi/statisticsList.do"


class KOSISApiError(RuntimeError):
    """Raised when a KOSIS API request fails."""


@dataclass(frozen=True)
class KOSISCredentials:
    api_key: str

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "KOSISCredentials | None":
        load_dotenv(env_path)
        api_key = os.environ.get("KOSIS_API_KEY", "").strip()
        if not api_key:
            return None
        return cls(api_key=api_key)

    def candidates(self) -> tuple[str, ...]:
        candidates = [self.api_key]
        decoded = _base64_decoded_candidate(self.api_key)
        if decoded and decoded not in candidates:
            candidates.append(decoded)
        return tuple(candidates)


@dataclass(frozen=True)
class KOSISStatisticsListItem:
    source_id: str
    view_code: str
    view_name: str
    list_id: str
    list_name: str
    organization_id: str
    table_id: str
    table_name: str
    statistics_id: str
    updated_at: str
    recommended_table: str
    raw: dict[str, Any]
    retrieval_method: str = "kosis_statistics_list"
    body_collection_tier: int = 3
    raw_text_storage: str = "official_data_record"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KOSISStatisticsListResult:
    view_code: str
    parent_id: str
    items: list[KOSISStatisticsListItem]


class KOSISClient:
    def __init__(
        self,
        credentials: KOSISCredentials,
        *,
        endpoint: str = KOSIS_STATISTICS_LIST_ENDPOINT,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.credentials = credentials
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "KOSISClient | None":
        credentials = KOSISCredentials.from_env(env_path)
        if credentials is None:
            return None
        return cls(credentials)

    def statistics_list(
        self,
        *,
        view_code: str = "MT_ZTITLE",
        parent_id: str = "",
        content: str | None = None,
    ) -> KOSISStatisticsListResult:
        if not view_code.strip():
            raise ValueError("view_code is required")

        last_error: KOSISApiError | None = None
        for api_key in self.credentials.candidates():
            try:
                data = self._statistics_list_with_key(
                    api_key=api_key,
                    view_code=view_code,
                    parent_id=parent_id,
                    content=content,
                )
            except KOSISApiError as exc:
                last_error = exc
                if "유효하지않은 인증KEY" in str(exc):
                    continue
                raise
            return KOSISStatisticsListResult(
                view_code=view_code,
                parent_id=parent_id,
                items=[_statistics_list_item_from_row(row) for row in data if isinstance(row, dict)],
            )
        raise last_error or KOSISApiError("KOSIS API request failed.")

    def _statistics_list_with_key(
        self,
        *,
        api_key: str,
        view_code: str,
        parent_id: str,
        content: str | None,
    ) -> list[dict[str, Any]]:
        params = {
            "method": "getList",
            "apiKey": api_key,
            "vwCd": view_code,
            "parentId": parent_id,
            "format": "json",
            "jsonVD": "Y",
        }
        if content:
            params["content"] = content
        data = self._get_json(params)
        if isinstance(data, dict):
            _raise_if_kosis_error(data)
            rows = data.get("data", [])
            if isinstance(rows, list):
                return rows
            raise KOSISApiError("Unexpected KOSIS statisticsList response shape.")
        if not isinstance(data, list):
            raise KOSISApiError("Unexpected KOSIS statisticsList response type.")
        return data

    def _get_json(self, params: dict[str, str]) -> Any:
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
            raise KOSISApiError(f"KOSIS API HTTP {exc.code}: {_safe_error_detail(detail)}") from exc
        except URLError as exc:
            raise KOSISApiError(f"KOSIS API request failed: {exc.reason}") from exc
        return json.loads(body)


def _statistics_list_item_from_row(row: dict[str, Any]) -> KOSISStatisticsListItem:
    return KOSISStatisticsListItem(
        source_id="kosis",
        view_code=_first_present(row, "VW_CD"),
        view_name=_first_present(row, "VW_NM"),
        list_id=_first_present(row, "LIST_ID"),
        list_name=_first_present(row, "LIST_NM"),
        organization_id=_first_present(row, "ORG_ID"),
        table_id=_first_present(row, "TBL_ID"),
        table_name=_first_present(row, "TBL_NM"),
        statistics_id=_first_present(row, "STAT_ID"),
        updated_at=_first_present(row, "SEND_DE"),
        recommended_table=_first_present(row, "REC_TBL_SE"),
        raw=row,
    )


def _first_present(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return str(value).strip()
    return ""


def _raise_if_kosis_error(data: dict[str, Any]) -> None:
    err = str(data.get("err", "")).strip()
    if err:
        message = str(data.get("errMsg", "")).strip()
        raise KOSISApiError(f"KOSIS API error {err}: {message}")


def _base64_decoded_candidate(value: str) -> str:
    padded = value + "=" * ((4 - len(value) % 4) % 4)
    try:
        decoded = base64.b64decode(padded, validate=False).decode("ascii")
    except Exception:
        return ""
    if len(decoded) == 32 and all(char in "0123456789abcdefABCDEF" for char in decoded):
        return decoded
    return ""


def _safe_error_detail(value: str) -> str:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return value[:300]
    return json.dumps(data, ensure_ascii=False)[:300]
