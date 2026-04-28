"""Naver News Search API adapter.

This adapter collects metadata only. Article body collection remains behind the
copyright gate and is not performed here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
import html
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from content_research.env import load_dotenv
from content_research.sources.json_api import parse_json_response


NAVER_NEWS_ENDPOINT = "https://openapi.naver.com/v1/search/news.json"
DEFAULT_NAVER_NEWS_QUERIES: tuple[str, ...] = (
    "국제 경제",
    "미국 금리",
    "중국 경제",
    "환율",
    "물가",
    "중앙은행",
    "반도체",
    "AI",
    "원유",
    "공급망",
    "한국 경제",
)


class NaverNewsApiError(RuntimeError):
    """Raised when the Naver News API returns an error response."""


@dataclass(frozen=True)
class NaverNewsCredentials:
    client_id: str
    client_secret: str

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "NaverNewsCredentials | None":
        load_dotenv(env_path)
        client_id = os.environ.get("NAVER_CLIENT_ID", "").strip()
        client_secret = os.environ.get("NAVER_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            return None
        return cls(client_id=client_id, client_secret=client_secret)


@dataclass(frozen=True)
class NaverNewsItem:
    source_id: str
    query: str
    title: str
    link: str
    original_link: str
    description: str
    published_at: str
    raw_pub_date: str
    retrieval_method: str = "naver_news_search_api"
    body_collection_tier: int = 0
    raw_text_storage: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NaverNewsSearchResult:
    query: str
    total: int
    start: int
    display: int
    items: list[NaverNewsItem]


class NaverNewsClient:
    def __init__(
        self,
        credentials: NaverNewsCredentials,
        *,
        endpoint: str = NAVER_NEWS_ENDPOINT,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.credentials = credentials
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "NaverNewsClient | None":
        credentials = NaverNewsCredentials.from_env(env_path)
        if credentials is None:
            return None
        return cls(credentials)

    def search(
        self,
        query: str,
        *,
        display: int = 10,
        start: int = 1,
        sort: str = "date",
    ) -> NaverNewsSearchResult:
        if not query.strip():
            raise ValueError("query is required")
        if display < 1 or display > 100:
            raise ValueError("display must be between 1 and 100")
        if start < 1 or start > 1000:
            raise ValueError("start must be between 1 and 1000")
        if sort not in {"sim", "date"}:
            raise ValueError("sort must be 'sim' or 'date'")

        payload = {
            "query": query,
            "display": str(display),
            "start": str(start),
            "sort": sort,
        }
        request = Request(
            f"{self.endpoint}?{urlencode(payload)}",
            headers={
                "X-Naver-Client-Id": self.credentials.client_id,
                "X-Naver-Client-Secret": self.credentials.client_secret,
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
            raise NaverNewsApiError(f"Naver API HTTP {exc.code}: {_safe_error_detail(detail)}") from exc
        except URLError as exc:
            raise NaverNewsApiError(f"Naver API request failed: {exc.reason}") from exc

        data = parse_json_response(body, "Naver API", NaverNewsApiError)
        items = [
            _item_from_api(query, item)
            for item in data.get("items", [])
            if isinstance(item, dict)
        ]
        return NaverNewsSearchResult(
            query=query,
            total=int(data.get("total", 0)),
            start=int(data.get("start", start)),
            display=int(data.get("display", len(items))),
            items=items,
        )

    def collect_queries(
        self,
        queries: tuple[str, ...] = DEFAULT_NAVER_NEWS_QUERIES,
        *,
        display: int = 10,
        sort: str = "date",
    ) -> list[NaverNewsItem]:
        deduped: dict[str, NaverNewsItem] = {}
        for query in queries:
            result = self.search(query, display=display, sort=sort)
            for item in result.items:
                key = item.original_link or item.link
                if key and key not in deduped:
                    deduped[key] = item
        return list(deduped.values())


def _item_from_api(query: str, item: dict[str, Any]) -> NaverNewsItem:
    raw_pub_date = str(item.get("pubDate", ""))
    return NaverNewsItem(
        source_id="naver_news",
        query=query,
        title=_clean_naver_html(str(item.get("title", ""))),
        link=str(item.get("link", "")),
        original_link=str(item.get("originallink", "")),
        description=_clean_naver_html(str(item.get("description", ""))),
        published_at=_parse_pub_date(raw_pub_date),
        raw_pub_date=raw_pub_date,
    )


def _clean_naver_html(value: str) -> str:
    without_tags = re.sub(r"</?b>", "", value)
    return html.unescape(without_tags).strip()


def _parse_pub_date(value: str) -> str:
    if not value.strip():
        return ""
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError):
        return value


def _safe_error_detail(value: str) -> str:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return value[:300]
    return json.dumps(data, ensure_ascii=False)[:300]
