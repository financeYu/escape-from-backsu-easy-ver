"""Metadata-only YouTube adapter interface.

This module intentionally does not implement network calls. Production adapters
should use the YouTube Data API and return metadata only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class YouTubeVideoMetadata:
    video_id: str
    title: str
    channel_id: str
    channel_title: str
    published_at: str
    description_snippet: str = ""
    tags: list[str] = field(default_factory=list)
    duration: str | None = None
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None


class YouTubeMetadataAdapter(Protocol):
    """Mockable interface for YouTube Data API metadata-only collection."""

    def search_videos(self, query: str, *, max_results: int = 10) -> list[YouTubeVideoMetadata]:
        """Return video metadata. Must not scrape HTML, download video, or collect comments."""


class InMemoryYouTubeMetadataAdapter:
    """Test adapter that returns caller-provided metadata."""

    def __init__(self, videos: list[YouTubeVideoMetadata] | None = None) -> None:
        self._videos = videos or []

    def search_videos(self, query: str, *, max_results: int = 10) -> list[YouTubeVideoMetadata]:
        if not query.strip():
            return []
        return self._videos[:max_results]


FORBIDDEN_YOUTUBE_COLLECTION = (
    "youtube.com HTML scraping",
    "video download",
    "unauthorized transcript extraction",
    "bulk comment scraping",
)

