import json

import pytest

from content_research.collection.catalog import CollectionSource
from content_research.collection.process import HourlyCollectionProcess
from content_research.sources.news_discovery import newsapi
from content_research.sources.news_discovery.newsapi import NewsAPIClient, NewsAPICredentials


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_newsapi_everything_parses_metadata(monkeypatch):
    payload = {
        "status": "ok",
        "totalResults": 1,
        "articles": [
            {
                "source": {"id": "reuters", "name": "Reuters"},
                "author": "Test Reporter",
                "title": "Global Economy Story",
                "description": "Short description",
                "url": "https://example.com/economy",
                "urlToImage": "https://example.com/image.jpg",
                "publishedAt": "2026-04-27T02:00:00Z",
                "content": "Truncated snippet [+100 chars]",
            }
        ],
    }

    def fake_urlopen(request, timeout):
        assert "everything" in request.full_url
        assert "q=global+economy" in request.full_url
        assert request.headers["X-api-key"] == "secret"
        return FakeResponse(payload)

    monkeypatch.setattr(newsapi, "urlopen", fake_urlopen)

    client = NewsAPIClient(NewsAPICredentials("secret"))
    result = client.everything("global economy", page_size=1)

    assert result.total_results == 1
    assert result.items[0].title == "Global Economy Story"
    assert result.items[0].collection_api == "everything"
    assert result.items[0].content_snippet == "Truncated snippet [+100 chars]"
    assert result.items[0].body_collection_tier == 0
    assert result.items[0].raw_text_storage == "none"


def test_newsapi_top_headlines_parses_metadata(monkeypatch):
    payload = {
        "status": "ok",
        "totalResults": 1,
        "articles": [
            {
                "source": {"id": "bbc-news", "name": "BBC News"},
                "title": "Business Headline",
                "description": "Headline description",
                "url": "https://example.com/business",
                "publishedAt": "2026-04-27T02:00:00Z",
            }
        ],
    }

    def fake_urlopen(request, timeout):
        assert "top-headlines" in request.full_url
        assert "country=gb" in request.full_url
        assert "category=business" in request.full_url
        return FakeResponse(payload)

    monkeypatch.setattr(newsapi, "urlopen", fake_urlopen)

    client = NewsAPIClient(NewsAPICredentials("secret"))
    result = client.top_headlines(country="gb", category="business", page_size=1)

    assert result.collection_api == "top_headlines"
    assert result.items[0].headline_country == "gb"
    assert result.items[0].headline_category == "business"


def test_collection_process_writes_newsapi_records(monkeypatch, tmp_path):
    item = newsapi.NewsAPIArticleItem(
        source_id="newsapi",
        collection_api="everything",
        query="global economy",
        headline_country="",
        headline_category="",
        source_api_id="reuters",
        source_name="Reuters",
        author="Test Reporter",
        title="NewsAPI Metadata Story",
        description="Description",
        url="https://example.com/newsapi",
        image_url="",
        published_at="2026-04-27T02:00:00Z",
        content_snippet="Snippet",
    )

    class FakeClient:
        def collect_default(self):
            return [item]

    monkeypatch.setattr(newsapi.NewsAPIClient, "from_env", classmethod(lambda cls: FakeClient()))

    source = CollectionSource(
        source_id="newsapi",
        display_name="NewsAPI",
        category="international_news_discovery",
        adapter="news_discovery.newsapi",
        access_method="api",
        default_body_tier=0,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, jsonl_path, _ = process.run_once()

    assert manifest.results[0].status == "fetched_metadata"
    assert manifest.results[0].collected_records == 1
    records_path = tmp_path / manifest.output_partition / "records" / manifest.run_id / "newsapi.jsonl"
    assert records_path.exists()
    assert "NewsAPI Metadata Story" in records_path.read_text(encoding="utf-8")

    manifest_records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    source_result = next(record for record in manifest_records if record["type"] == "source_result")
    assert source_result["records_path"].endswith("newsapi.jsonl")


def test_newsapi_missing_credentials_returns_status(monkeypatch, tmp_path):
    monkeypatch.setattr(newsapi.NewsAPIClient, "from_env", classmethod(lambda cls: None))
    source = CollectionSource(
        source_id="newsapi",
        display_name="NewsAPI",
        category="international_news_discovery",
        adapter="news_discovery.newsapi",
        access_method="api",
        default_body_tier=0,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, _, _ = process.run_once()

    assert manifest.results[0].status == "missing_credentials"
    assert "NEWSAPI_KEY" in manifest.results[0].message


def test_invalid_newsapi_page_size_rejected():
    client = NewsAPIClient(NewsAPICredentials("secret"))

    with pytest.raises(ValueError, match="page_size"):
        client.everything("economy", page_size=101)
