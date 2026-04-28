"""News discovery adapters."""

from content_research.sources.news_discovery.naver_news import NaverNewsClient
from content_research.sources.news_discovery.newsapi import NewsAPIClient
from content_research.sources.news_discovery.nytimes import NYTimesClient

__all__ = ["NaverNewsClient", "NewsAPIClient", "NYTimesClient"]
