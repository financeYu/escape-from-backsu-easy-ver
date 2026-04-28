"""Hourly source collection process.

The first implementation creates deterministic collection manifests without
performing network requests. API adapters can later replace the per-source
planning result while keeping the same schedule and output contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import time
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo

from content_research.collection.catalog import CollectionSource, DEFAULT_COLLECTION_SOURCES
from content_research.sources.official_data.ecos import ECOSApiError, ECOSClient
from content_research.sources.official_data.eia import EIAApiError, EIAClient
from content_research.sources.official_data.fred import FREDApiError, FREDClient
from content_research.sources.official_data.kosis import KOSISApiError, KOSISClient
from content_research.sources.official_data.opendart import OpenDARTApiError, OpenDARTClient
from content_research.sources.official_data.un_comtrade import UNComtradeApiError, UNComtradeClient
from content_research.sources.news_discovery.naver_news import NaverNewsApiError, NaverNewsClient
from content_research.sources.news_discovery.newsapi import NewsAPIClient, NewsAPIError
from content_research.sources.news_discovery.nytimes import NYTimesApiError, NYTimesClient


NAVER_NEWS_DISPLAY = 10
NAVER_NEWS_SORT = "date"
OPENDART_LOOKBACK_DAYS = 7
KOSIS_ROOT_VIEW_CODE = "MT_ZTITLE"
KOSIS_ROOT_PARENT_ID = ""
ECOS_KEY_STAT_START = 1
ECOS_KEY_STAT_END = 100
ECOS_KEY_STAT_LANGUAGE = "kr"


@dataclass(frozen=True)
class CollectionSourceResult:
    source_id: str
    display_name: str
    adapter: str
    category: str
    access_method: str
    body_collection_tier: int
    status: str
    collected_records: int
    rights_gate_status: str
    message: str
    records_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CollectionRunManifest:
    run_id: str
    mode: str
    timezone: str
    interval_minutes: int
    started_at: str
    finished_at: str
    next_run_at: str
    output_partition: str
    sources_planned: int
    sources_enabled: int
    results: list[CollectionSourceResult]

    def to_jsonl(self) -> str:
        records: list[dict[str, Any]] = [
            {
                "type": "collection_run",
                "run_id": self.run_id,
                "mode": self.mode,
                "timezone": self.timezone,
                "interval_minutes": self.interval_minutes,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "next_run_at": self.next_run_at,
                "output_partition": self.output_partition,
                "sources_planned": self.sources_planned,
                "sources_enabled": self.sources_enabled,
            },
            *({"type": "source_result", "run_id": self.run_id, **result.to_dict()} for result in self.results),
        ]
        return "\n".join(json.dumps(record, ensure_ascii=False) for record in records)

    def to_markdown(self) -> str:
        rows = "\n".join(
            "| {source_id} | {name} | {category} | {tier} | {status} | {records_path} | {message} |".format(
                source_id=result.source_id,
                name=result.display_name,
                category=result.category,
                tier=result.body_collection_tier,
                status=result.status,
                records_path=result.records_path,
                message=result.message.replace("|", "/"),
            )
            for result in self.results
        )
        return f"""# Hourly Collection Run

## Summary

- Run ID: `{self.run_id}`
- Mode: `{self.mode}`
- Started: `{self.started_at}`
- Finished: `{self.finished_at}`
- Next run: `{self.next_run_at}`
- Interval: `{self.interval_minutes}` minutes
- Output partition: `{self.output_partition}`
- Enabled sources: `{self.sources_enabled}` / `{self.sources_planned}`

## Sources

| Source ID | Name | Category | Body Tier | Status | Records | Message |
|---|---|---|---:|---|---|---|
{rows}
"""


class HourlyCollectionProcess:
    def __init__(
        self,
        output_dir: str | Path = "outputs/collections",
        interval_minutes: int = 60,
        timezone_name: str = "Asia/Seoul",
        sources: Iterable[CollectionSource] | None = None,
    ) -> None:
        if interval_minutes <= 0:
            raise ValueError("interval_minutes must be positive")
        self.output_dir = Path(output_dir)
        self.interval_minutes = interval_minutes
        self.timezone_name = timezone_name
        self.timezone = ZoneInfo(timezone_name)
        self.sources = tuple(sources or DEFAULT_COLLECTION_SOURCES)

    def run_once(self, now: datetime | None = None, mode: str = "manual") -> tuple[CollectionRunManifest, Path, Path]:
        started_at = self._normalize_now(now)
        base_run_id = started_at.strftime("%Y%m%dT%H%M%S%f%z")
        partition = started_at.strftime("%Y-%m-%d/%H")
        run_dir = self.output_dir / partition
        run_dir.mkdir(parents=True, exist_ok=True)
        run_id = self._unique_run_id(run_dir, base_run_id)
        records_dir = run_dir / "records" / run_id
        results = [self._collect_source_result(source, records_dir) for source in self.sources]
        finished_at = datetime.now(self.timezone)
        next_run_at = self.next_run_after(started_at)
        manifest = CollectionRunManifest(
            run_id=run_id,
            mode=mode,
            timezone=self.timezone_name,
            interval_minutes=self.interval_minutes,
            started_at=self._iso(started_at),
            finished_at=self._iso(finished_at),
            next_run_at=self._iso(next_run_at),
            output_partition=partition,
            sources_planned=len(self.sources),
            sources_enabled=sum(1 for source in self.sources if source.enabled),
            results=results,
        )
        return self.write_outputs(manifest, run_dir=run_dir)

    def run_forever(
        self,
        max_cycles: int | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> list[CollectionRunManifest]:
        manifests: list[CollectionRunManifest] = []
        cycle = 0
        while max_cycles is None or cycle < max_cycles:
            manifest, _, _ = self.run_once(mode="scheduled")
            manifests.append(manifest)
            cycle += 1
            if max_cycles is not None and cycle >= max_cycles:
                break
            sleep_until = self.next_run_after(datetime.now(self.timezone))
            sleep_seconds = max(0.0, (sleep_until - datetime.now(self.timezone)).total_seconds())
            sleep_fn(sleep_seconds)
        return manifests

    def write_outputs(
        self,
        manifest: CollectionRunManifest,
        *,
        run_dir: Path | None = None,
    ) -> tuple[CollectionRunManifest, Path, Path]:
        run_dir = run_dir or self.output_dir / manifest.output_partition
        run_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = run_dir / f"{manifest.run_id}.jsonl"
        markdown_path = run_dir / f"{manifest.run_id}.md"
        jsonl_path.write_text(manifest.to_jsonl() + "\n", encoding="utf-8")
        markdown_path.write_text(manifest.to_markdown(), encoding="utf-8")
        return manifest, jsonl_path, markdown_path

    @staticmethod
    def _unique_run_id(run_dir: Path, base_run_id: str) -> str:
        run_id = base_run_id
        suffix = 1
        while (run_dir / f"{run_id}.jsonl").exists() or (run_dir / "records" / run_id).exists():
            run_id = f"{base_run_id}-{suffix:03d}"
            suffix += 1
        return run_id

    def next_run_after(self, moment: datetime) -> datetime:
        local = self._normalize_now(moment).replace(second=0, microsecond=0)
        if self.interval_minutes == 60:
            return local.replace(minute=0) + timedelta(hours=1)
        return local + timedelta(minutes=self.interval_minutes)

    def _collect_source_result(self, source: CollectionSource, run_dir: Path) -> CollectionSourceResult:
        if not source.enabled:
            return self._source_result(
                source,
                status="skipped",
                rights_gate_status="not_checked",
                message="Source disabled in catalog.",
            )

        handlers: dict[str, Callable[[CollectionSource, Path], CollectionSourceResult]] = {
            "naver_news": self._collect_naver_news,
            "newsapi": self._collect_newsapi,
            "nytimes": self._collect_nytimes,
            "ecos": self._collect_ecos,
            "kosis": self._collect_kosis,
            "opendart": self._collect_opendart,
            "fred": self._collect_fred,
            "eia": self._collect_eia,
            "un_comtrade": self._collect_un_comtrade,
        }
        handler = handlers.get(source.source_id)
        if handler is not None:
            return handler(source, run_dir)

        rights_gate_status = "metadata_only" if source.default_body_tier == 0 else "body_allowed_by_source_tier"
        return self._source_result(
            source,
            status="planned",
            rights_gate_status=rights_gate_status,
            message="Adapter placeholder planned; no network request executed in MVP scheduler.",
        )

    @staticmethod
    def _source_result(
        source: CollectionSource,
        *,
        status: str,
        rights_gate_status: str,
        message: str,
        collected_records: int = 0,
        records_path: str | Path = "",
    ) -> CollectionSourceResult:
        return CollectionSourceResult(
            source_id=source.source_id,
            display_name=source.display_name,
            adapter=source.adapter,
            category=source.category,
            access_method=source.access_method,
            body_collection_tier=source.default_body_tier,
            status=status,
            collected_records=collected_records,
            rights_gate_status=rights_gate_status,
            message=message,
            records_path=str(records_path) if records_path else "",
        )

    def _missing_credentials_result(
        self,
        source: CollectionSource,
        *,
        rights_gate_status: str,
        required_credentials: str,
    ) -> CollectionSourceResult:
        return self._source_result(
            source,
            status="missing_credentials",
            rights_gate_status=rights_gate_status,
            message=f"{required_credentials} required in environment or .env.",
        )

    def _error_result(
        self,
        source: CollectionSource,
        *,
        rights_gate_status: str,
        exc: Exception,
    ) -> CollectionSourceResult:
        return self._source_result(
            source,
            status="error",
            rights_gate_status=rights_gate_status,
            message=str(exc),
        )

    def _fetched_records_result(
        self,
        source: CollectionSource,
        *,
        status: str,
        rights_gate_status: str,
        message: str,
        records_dir: Path,
        filename: str,
        records: Iterable[Any],
    ) -> CollectionSourceResult:
        items = list(records)
        records_path = self._write_records(records_dir, filename, items)
        return self._source_result(
            source,
            status=status,
            collected_records=len(items),
            rights_gate_status=rights_gate_status,
            message=message,
            records_path=records_path,
        )

    @staticmethod
    def _write_records(records_dir: Path, filename: str, records: Iterable[Any]) -> Path:
        records_dir.mkdir(parents=True, exist_ok=True)
        records_path = records_dir / filename
        lines = [json.dumps(item.to_dict(), ensure_ascii=False) for item in records]
        records_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return records_path

    def _collect_naver_news(self, source: CollectionSource, run_dir: Path) -> CollectionSourceResult:
        client = NaverNewsClient.from_env()
        if client is None:
            return self._missing_credentials_result(
                source,
                rights_gate_status="metadata_only",
                required_credentials="NAVER_CLIENT_ID and NAVER_CLIENT_SECRET are",
            )

        try:
            items = client.collect_queries(display=NAVER_NEWS_DISPLAY, sort=NAVER_NEWS_SORT)
        except NaverNewsApiError as exc:
            return self._error_result(source, rights_gate_status="metadata_only", exc=exc)

        return self._fetched_records_result(
            source,
            status="fetched_metadata",
            rights_gate_status="metadata_only",
            message="Fetched Naver News Search API metadata. Article bodies were not collected.",
            records_dir=run_dir,
            filename="naver_news.jsonl",
            records=items,
        )

    def _collect_newsapi(self, source: CollectionSource, run_dir: Path) -> CollectionSourceResult:
        client = NewsAPIClient.from_env()
        if client is None:
            return self._missing_credentials_result(
                source,
                rights_gate_status="metadata_only",
                required_credentials="NEWSAPI_KEY is",
            )

        try:
            items = client.collect_default()
        except NewsAPIError as exc:
            return self._error_result(source, rights_gate_status="metadata_only", exc=exc)

        return self._fetched_records_result(
            source,
            status="fetched_metadata",
            rights_gate_status="metadata_only",
            message="Fetched NewsAPI.org Everything and Top Headlines metadata. Article bodies were not collected.",
            records_dir=run_dir,
            filename="newsapi.jsonl",
            records=items,
        )

    def _collect_opendart(self, source: CollectionSource, run_dir: Path) -> CollectionSourceResult:
        client = OpenDARTClient.from_env()
        if client is None:
            return self._missing_credentials_result(
                source,
                rights_gate_status="official_disclosure_metadata",
                required_credentials="OPENDART_API_KEY is",
            )

        try:
            result = client.recent_disclosures(
                today=datetime.now(self.timezone).date(),
                lookback_days=OPENDART_LOOKBACK_DAYS,
            )
        except OpenDARTApiError as exc:
            return self._error_result(source, rights_gate_status="official_disclosure_metadata", exc=exc)

        return self._fetched_records_result(
            source,
            status="fetched_disclosures",
            rights_gate_status="official_disclosure_metadata",
            message="Fetched OpenDART disclosure list records for the last 7 days.",
            records_dir=run_dir,
            filename="opendart.jsonl",
            records=result.items,
        )

    def _collect_fred(self, source: CollectionSource, run_dir: Path) -> CollectionSourceResult:
        client = FREDClient.from_env()
        if client is None:
            return self._missing_credentials_result(
                source,
                rights_gate_status="official_data",
                required_credentials="FRED_API_KEY is",
            )

        try:
            items = client.collect_default()
        except FREDApiError as exc:
            return self._error_result(source, rights_gate_status="official_data", exc=exc)

        return self._fetched_records_result(
            source,
            status="fetched_observations",
            rights_gate_status="official_data",
            message="Fetched FRED official time-series observations for default US macro and financial indicators.",
            records_dir=run_dir,
            filename="fred.jsonl",
            records=items,
        )

    def _collect_eia(self, source: CollectionSource, run_dir: Path) -> CollectionSourceResult:
        client = EIAClient.from_env()
        if client is None:
            return self._missing_credentials_result(
                source,
                rights_gate_status="official_data",
                required_credentials="EIA_API_KEY is",
            )

        try:
            items = client.collect_default()
        except EIAApiError as exc:
            return self._error_result(source, rights_gate_status="official_data", exc=exc)

        return self._fetched_records_result(
            source,
            status="fetched_energy_series",
            rights_gate_status="official_data",
            message="Fetched EIA official energy series observations for default oil, gas, electricity, and inventory indicators.",
            records_dir=run_dir,
            filename="eia.jsonl",
            records=items,
        )

    def _collect_un_comtrade(self, source: CollectionSource, run_dir: Path) -> CollectionSourceResult:
        client = UNComtradeClient.from_env()
        if client is None:
            return self._missing_credentials_result(
                source,
                rights_gate_status="official_data",
                required_credentials="UN_COMTRADE_KEY or COMTRADE_API_KEY is",
            )

        try:
            items = client.collect_default()
        except UNComtradeApiError as exc:
            return self._error_result(source, rights_gate_status="official_data", exc=exc)

        return self._fetched_records_result(
            source,
            status="fetched_trade_data",
            rights_gate_status="official_data",
            message="Fetched UN Comtrade annual total import/export records for default major reporters.",
            records_dir=run_dir,
            filename="un_comtrade.jsonl",
            records=items,
        )

    def _collect_kosis(self, source: CollectionSource, run_dir: Path) -> CollectionSourceResult:
        client = KOSISClient.from_env()
        if client is None:
            return self._missing_credentials_result(
                source,
                rights_gate_status="official_data",
                required_credentials="KOSIS_API_KEY is",
            )

        try:
            result = client.statistics_list(view_code=KOSIS_ROOT_VIEW_CODE, parent_id=KOSIS_ROOT_PARENT_ID)
        except KOSISApiError as exc:
            return self._error_result(source, rights_gate_status="official_data", exc=exc)

        return self._fetched_records_result(
            source,
            status="fetched_catalog",
            rights_gate_status="official_data",
            message="Fetched KOSIS statistics list records for MT_ZTITLE root.",
            records_dir=run_dir,
            filename="kosis.jsonl",
            records=result.items,
        )

    def _collect_ecos(self, source: CollectionSource, run_dir: Path) -> CollectionSourceResult:
        client = ECOSClient.from_env()
        if client is None:
            return self._missing_credentials_result(
                source,
                rights_gate_status="official_data",
                required_credentials="ECOS_API_KEY is",
            )

        try:
            result = client.key_statistics(
                start=ECOS_KEY_STAT_START,
                end=ECOS_KEY_STAT_END,
                language=ECOS_KEY_STAT_LANGUAGE,
            )
        except ECOSApiError as exc:
            return self._error_result(source, rights_gate_status="official_data", exc=exc)

        return self._fetched_records_result(
            source,
            status="fetched_statistics",
            rights_gate_status="official_data",
            message="Fetched Bank of Korea ECOS KeyStatisticList records.",
            records_dir=run_dir,
            filename="ecos.jsonl",
            records=result.items,
        )

    def _collect_nytimes(self, source: CollectionSource, run_dir: Path) -> CollectionSourceResult:
        client = NYTimesClient.from_env()
        if client is None:
            return self._missing_credentials_result(
                source,
                rights_gate_status="metadata_only",
                required_credentials="NYTIMES_API_KEY is",
            )

        try:
            items = client.collect_default()
        except NYTimesApiError as exc:
            return self._error_result(source, rights_gate_status="metadata_only", exc=exc)

        return self._fetched_records_result(
            source,
            status="fetched_metadata",
            rights_gate_status="metadata_only",
            message="Fetched NYT Article Search and Top Stories API metadata. Article bodies were not collected.",
            records_dir=run_dir,
            filename="nytimes.jsonl",
            records=items,
        )

    def _normalize_now(self, value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(self.timezone)
        if value.tzinfo is None:
            return value.replace(tzinfo=self.timezone)
        return value.astimezone(self.timezone)

    @staticmethod
    def _iso(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat(timespec="seconds")
