"""NewsAPI.org adapter.

The adapter collects discovery metadata only. NewsAPI's `content` field is
truncated and is treated as a snippet, not article body storage.
"""

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
from content_research.sources.json_api import parse_json_response


NEWSAPI_EVERYTHING_ENDPOINT = "https://newsapi.org/v2/everything"
NEWSAPI_TOP_HEADLINES_ENDPOINT = "https://newsapi.org/v2/top-headlines"

DEFAULT_NEWSAPI_QUERIES: tuple[str, ...] = (
    "global economy",
    "central banks",
    "China economy",
    "artificial intelligence",
    "semiconductors",
    "oil prices",
)
DEFAULT_NEWSAPI_HEADLINES: tuple[tuple[str, str], ...] = (
    ("us", "business"),
    ("us", "technology"),
    ("gb", "business"),
)


class NewsAPIError(RuntimeError):
    """Raised when NewsAPI returns an error or unexpected response."""


@dataclass(frozen=True)
class NewsAPICredentials:
    api_key: str

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "NewsAPICredentials | None":
        load_dotenv(env_path)
        api_key = os.environ.get("NEWSAPI_KEY", "").strip()
        if not api_key:
            return None
        return cls(api_key=api_key)


@dataclass(frozen=True)
class NewsAPIArticleItem:
    source_id: str
    collection_api: str
    query: str
    headline_country: str
    headline_category: str
    source_api_id: str
    source_name: str
    author: str
    title: str
    description: str
    url: str
    image_url: str
    published_at: str
    content_snippet: str
    retrieval_method: str = "newsapi_org"
    body_collection_tier: int = 0
    raw_text_storage: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NewsAPIArticleResult:
    collection_api: str
    total_results: int
    items: list[NewsAPIArticleItem]


class NewsAPIClient:
    def __init__(
        self,
        credentials: NewsAPICredentials,
        *,
        everything_endpoint: str = NEWSAPI_EVERYTHING_ENDPOINT,
        top_headlines_endpoint: str = NEWSAPI_TOP_HEADLINES_ENDPOINT,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.credentials = credentials
        self.everything_endpoint = everything_endpoint
        self.top_headlines_endpoint = top_headlines_endpoint
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "NewsAPIClient | None":
        credentials = NewsAPICredentials.from_env(env_path)
        if credentials is None:
            return None
        return cls(credentials)

    def everything(
        self,
        query: str,
        *,
        language: str = "en",
        sort_by: str = "publishedAt",
        page_size: int = 20,
        page: int = 1,
    ) -> NewsAPIArticleResult:
        if not query.strip():
            raise ValueError("query is required")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")
        if page < 1:
            raise ValueError("page must be positive")
        if sort_by not in {"relevancy", "popularity", "publishedAt"}:
            raise ValueError("sort_by is invalid")

        data = self._get_json(
            self.everything_endpoint,
            {
                "q": query,
                "language": language,
                "sortBy": sort_by,
                "pageSize": str(page_size),
                "page": str(page),
            },
        )
        return self._result_from_response(data, collection_api="everything", query=query)

    def top_headlines(
        self,
        *,
        country: str = "us",
        category: str = "business",
        page_size: int = 20,
        page: int = 1,
    ) -> NewsAPIArticleResult:
        if not country.strip():
            raise ValueError("country is required")
        if not category.strip():
            raise ValueError("category is required")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")
        if page < 1:
            raise ValueError("page must be positive")

        data = self._get_json(
            self.top_headlines_endpoint,
            {
                "country": country,
                "category": category,
                "pageSize": str(page_size),
                "page": str(page),
            },
        )
        return self._result_from_response(
            data,
            collection_api="top_headlines",
            headline_country=country,
            headline_category=category,
        )

    def collect_default(
        self,
        queries: tuple[str, ...] = DEFAULT_NEWSAPI_QUERIES,
        headline_pairs: tuple[tuple[str, str], ...] = DEFAULT_NEWSAPI_HEADLINES,
    ) -> list[NewsAPIArticleItem]:
        deduped: dict[str, NewsAPIArticleItem] = {}
        for query in queries:
            result = self.everything(query, page_size=20)
            for item in result.items:
                if item.url and item.url not in deduped:
                    deduped[item.url] = item
        for country, category in headline_pairs:
            result = self.top_headlines(country=country, category=category, page_size=20)
            for item in result.items:
                if item.url and item.url not in deduped:
                    deduped[item.url] = item
        return list(deduped.values())

    def _get_json(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        request = Request(
            f"{endpoint}?{urlencode(params)}",
            headers={
                "Accept": "application/json",
                "X-Api-Key": self.credentials.api_key,
                "User-Agent": "content-research-mvp/0.1",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise NewsAPIError(f"NewsAPI HTTP {exc.code}: {_safe_error_detail(detail)}") from exc
        except URLError as exc:
            raise NewsAPIError(f"NewsAPI request failed: {exc.reason}") from exc
        data = parse_json_response(body, "NewsAPI", NewsAPIError)
        if not isinstance(data, dict):
            raise NewsAPIError("Unexpected NewsAPI response type.")
        _raise_if_newsapi_error(data)
        return data

    def _result_from_response(
        self,
        data: dict[str, Any],
        *,
        collection_api: str,
        query: str = "",
        headline_country: str = "",
        headline_category: str = "",
    ) -> NewsAPIArticleResult:
        articles = data.get("articles", [])
        if articles is None:
            articles = []
        if not isinstance(articles, list):
            raise NewsAPIError("Unexpected NewsAPI articles response shape.")
        return NewsAPIArticleResult(
            collection_api=collection_api,
            total_results=int(data.get("totalResults", len(articles)) or 0),
            items=[
                _article_item_from_response(
                    article,
                    collection_api=collection_api,
                    query=query,
                    headline_country=headline_country,
                    headline_category=headline_category,
                )
                for article in articles
                if isinstance(article, dict)
            ],
        )


def _article_item_from_response(
    article: dict[str, Any],
    *,
    collection_api: str,
    query: str,
    headline_country: str,
    headline_category: str,
) -> NewsAPIArticleItem:
    source = article.get("source", {})
    if not isinstance(source, dict):
        source = {}
    return NewsAPIArticleItem(
        source_id="newsapi",
        collection_api=collection_api,
        query=query,
        headline_country=headline_country,
        headline_category=headline_category,
        source_api_id=_as_str(source.get("id")),
        source_name=_as_str(source.get("name")),
        author=_as_str(article.get("author")),
        title=_as_str(article.get("title")),
        description=_as_str(article.get("description")),
        url=_as_str(article.get("url")),
        image_url=_as_str(article.get("urlToImage")),
        published_at=_as_str(article.get("publishedAt")),
        content_snippet=_as_str(article.get("content")),
    )


def _raise_if_newsapi_error(data: dict[str, Any]) -> None:
    status = str(data.get("status", "")).strip()
    if status == "error":
        code = str(data.get("code", "")).strip()
        message = str(data.get("message", "")).strip()
        raise NewsAPIError(f"NewsAPI error {code}: {message}")


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
