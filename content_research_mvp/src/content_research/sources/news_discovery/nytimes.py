"""New York Times API adapter.

The adapter collects article metadata from the official NYT Article Search and
Top Stories APIs. It does not fetch or store full article bodies.
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


NYTIMES_ARTICLE_SEARCH_ENDPOINT = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
NYTIMES_TOP_STORIES_ENDPOINT = "https://api.nytimes.com/svc/topstories/v2"

DEFAULT_NYTIMES_QUERIES: tuple[str, ...] = (
    "global economy",
    "central banks",
    "China economy",
    "artificial intelligence",
    "semiconductors",
)
DEFAULT_NYTIMES_TOP_STORY_SECTIONS: tuple[str, ...] = ("world", "business", "technology")


class NYTimesApiError(RuntimeError):
    """Raised when a NYT API request fails."""


@dataclass(frozen=True)
class NYTimesCredentials:
    api_key: str

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "NYTimesCredentials | None":
        load_dotenv(env_path)
        api_key = os.environ.get("NYTIMES_API_KEY", "").strip()
        if not api_key:
            return None
        return cls(api_key=api_key)


@dataclass(frozen=True)
class NYTimesArticleItem:
    source_id: str
    collection_api: str
    title: str
    url: str
    published_at: str
    section: str
    subsection: str
    byline: str
    abstract: str
    snippet: str
    lead_paragraph: str
    query: str = ""
    top_story_section: str = ""
    document_id: str = ""
    material_type: str = ""
    retrieval_method: str = "nytimes_api"
    body_collection_tier: int = 0
    raw_text_storage: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NYTimesArticleSearchResult:
    query: str
    hits: int
    page: int
    items: list[NYTimesArticleItem]


@dataclass(frozen=True)
class NYTimesTopStoriesResult:
    section: str
    items: list[NYTimesArticleItem]


class NYTimesClient:
    def __init__(
        self,
        credentials: NYTimesCredentials,
        *,
        article_search_endpoint: str = NYTIMES_ARTICLE_SEARCH_ENDPOINT,
        top_stories_endpoint: str = NYTIMES_TOP_STORIES_ENDPOINT,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.credentials = credentials
        self.article_search_endpoint = article_search_endpoint
        self.top_stories_endpoint = top_stories_endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "NYTimesClient | None":
        credentials = NYTimesCredentials.from_env(env_path)
        if credentials is None:
            return None
        return cls(credentials)

    def search_articles(
        self,
        query: str,
        *,
        page: int = 0,
        sort: str = "newest",
        fields: tuple[str, ...] = (
            "web_url",
            "snippet",
            "lead_paragraph",
            "abstract",
            "source",
            "headline",
            "keywords",
            "pub_date",
            "document_type",
            "news_desk",
            "section_name",
            "subsection_name",
            "byline",
            "type_of_material",
            "_id",
        ),
    ) -> NYTimesArticleSearchResult:
        if not query.strip():
            raise ValueError("query is required")
        if page < 0 or page > 10:
            raise ValueError("page must be between 0 and 10")
        if sort not in {"newest", "oldest"}:
            raise ValueError("sort must be 'newest' or 'oldest'")

        params = {
            "q": query,
            "page": str(page),
            "sort": sort,
            "fl": ",".join(fields),
            "api-key": self.credentials.api_key,
        }
        data = self._get_json(self.article_search_endpoint, params)
        response = data.get("response", {}) if isinstance(data, dict) else {}
        docs = response.get("docs", []) if isinstance(response, dict) else []
        meta = response.get("meta", {}) if isinstance(response, dict) else {}
        items = [
            _article_item_from_search_doc(query, doc)
            for doc in docs
            if isinstance(doc, dict)
        ]
        return NYTimesArticleSearchResult(
            query=query,
            hits=int(meta.get("hits", 0) or 0),
            page=page,
            items=items,
        )

    def top_stories(self, section: str = "world") -> NYTimesTopStoriesResult:
        if not section.strip():
            raise ValueError("section is required")
        endpoint = f"{self.top_stories_endpoint}/{section}.json"
        data = self._get_json(endpoint, {"api-key": self.credentials.api_key})
        results = data.get("results", []) if isinstance(data, dict) else []
        items = [
            _article_item_from_top_story(section, item)
            for item in results
            if isinstance(item, dict)
        ]
        return NYTimesTopStoriesResult(section=section, items=items)

    def collect_default(
        self,
        queries: tuple[str, ...] = DEFAULT_NYTIMES_QUERIES,
        top_story_sections: tuple[str, ...] = DEFAULT_NYTIMES_TOP_STORY_SECTIONS,
    ) -> list[NYTimesArticleItem]:
        deduped: dict[str, NYTimesArticleItem] = {}
        for query in queries:
            result = self.search_articles(query, page=0, sort="newest")
            for item in result.items:
                if item.url and item.url not in deduped:
                    deduped[item.url] = item
        for section in top_story_sections:
            result = self.top_stories(section)
            for item in result.items:
                if item.url and item.url not in deduped:
                    deduped[item.url] = item
        return list(deduped.values())

    def _get_json(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        request = Request(
            f"{endpoint}?{urlencode(params)}",
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
            raise NYTimesApiError(f"NYT API HTTP {exc.code}: {_safe_error_detail(detail)}") from exc
        except URLError as exc:
            raise NYTimesApiError(f"NYT API request failed: {exc.reason}") from exc
        return parse_json_response(body, "NYT API", NYTimesApiError)


def _article_item_from_search_doc(query: str, doc: dict[str, Any]) -> NYTimesArticleItem:
    headline = doc.get("headline", {})
    byline = doc.get("byline", {})
    return NYTimesArticleItem(
        source_id="nytimes",
        collection_api="article_search",
        query=query,
        title=_as_str(headline.get("main") if isinstance(headline, dict) else ""),
        url=_as_str(doc.get("web_url")),
        published_at=_as_str(doc.get("pub_date")),
        section=_as_str(doc.get("section_name")),
        subsection=_as_str(doc.get("subsection_name")),
        byline=_as_str(byline.get("original") if isinstance(byline, dict) else ""),
        abstract=_as_str(doc.get("abstract")),
        snippet=_as_str(doc.get("snippet")),
        lead_paragraph=_as_str(doc.get("lead_paragraph")),
        document_id=_as_str(doc.get("_id")),
        material_type=_as_str(doc.get("type_of_material")),
    )


def _article_item_from_top_story(section: str, item: dict[str, Any]) -> NYTimesArticleItem:
    return NYTimesArticleItem(
        source_id="nytimes",
        collection_api="top_stories",
        top_story_section=section,
        title=_as_str(item.get("title")),
        url=_as_str(item.get("url")),
        published_at=_as_str(item.get("published_date")),
        section=_as_str(item.get("section")),
        subsection=_as_str(item.get("subsection")),
        byline=_as_str(item.get("byline")),
        abstract=_as_str(item.get("abstract")),
        snippet="",
        lead_paragraph="",
        material_type=_as_str(item.get("material_type_facet")),
    )


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
