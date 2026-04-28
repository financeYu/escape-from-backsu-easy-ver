"""Monitoring helpers for content research collection runs."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable


SUCCESS_STATUSES = frozenset(
    {
        "success",
        "fetched_metadata",
        "fetched_observations",
        "fetched_energy_series",
        "fetched_trade_data",
        "fetched_statistics",
        "fetched_catalog",
        "fetched_disclosures",
    }
)

PERMISSION_MARKERS = (
    "permission",
    "forbidden",
    "unauthorized",
    "expired",
    "quota",
    "plan",
    "entitlement",
    "access denied",
)


@dataclass(frozen=True)
class SourceMonitorStatus:
    source_id: str
    status: str
    last_success_at: str | None
    recent_count: int
    error_type: str | None
    warning_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CollectionMonitorReport:
    sources: list[SourceMonitorStatus]

    def to_dict(self) -> dict[str, Any]:
        return {"sources": [source.to_dict() for source in self.sources]}

    def to_markdown(self) -> str:
        rows = "\n".join(
            "| {source_id} | {status} | {last_success_at} | {recent_count} | {error_type} | {warning_reason} |".format(
                source_id=source.source_id,
                status=source.status,
                last_success_at=source.last_success_at or "",
                recent_count=source.recent_count,
                error_type=source.error_type or "",
                warning_reason=(source.warning_reason or "").replace("|", "/"),
            )
            for source in self.sources
        )
        return f"""# Collection Monitor

| Source ID | Status | Last Success | Recent Count | Error Type | Warning |
|---|---|---|---:|---|---|
{rows}
"""


def monitor_jsonl_files(
    paths: Iterable[str | Path],
    *,
    expected_min_records: dict[str, int] | None = None,
    drop_ratio: float = 0.5,
) -> CollectionMonitorReport:
    """Build a monitor report from collection manifest JSONL files."""

    records: list[dict[str, Any]] = []
    for path in paths:
        records.extend(_read_jsonl(path))
    return monitor_records(records, expected_min_records=expected_min_records, drop_ratio=drop_ratio)


def monitor_records(
    records: Iterable[dict[str, Any]],
    *,
    expected_min_records: dict[str, int] | None = None,
    drop_ratio: float = 0.5,
) -> CollectionMonitorReport:
    """Build per-source health status from manifest records."""

    if drop_ratio <= 0 or drop_ratio > 1:
        raise ValueError("drop_ratio must be between 0 and 1")

    expected_min_records = expected_min_records or {}
    all_records = list(records)
    run_times = _collection_run_times(all_records)
    source_records = [_with_run_time(record, run_times) for record in all_records if _is_source_run_record(record)]
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in source_records:
        source_id = _as_str(record.get("source_id"))
        if source_id:
            by_source[source_id].append(record)

    statuses = [
        _monitor_source(source_id, runs, expected_min_records.get(source_id), drop_ratio)
        for source_id, runs in sorted(by_source.items())
    ]
    return CollectionMonitorReport(sources=statuses)


def summarize_report(report: CollectionMonitorReport) -> dict[str, Any]:
    """Return compact aggregate counts for operational dashboards."""

    status_counts = Counter(source.status for source in report.sources)
    return {
        "total_sources": len(report.sources),
        "status_counts": dict(status_counts),
        "credential_or_permission_sources": [
            source.source_id
            for source in report.sources
            if source.error_type in {"missing_credentials", "permission_denied"}
        ],
        "warning_sources": [
            source.source_id
            for source in report.sources
            if source.warning_reason
        ],
    }


def notify_stub(report: CollectionMonitorReport) -> list[str]:
    """Return alert messages without integrating an external notification system."""

    messages: list[str] = []
    for source in report.sources:
        if source.error_type or source.warning_reason:
            detail = source.error_type or source.warning_reason or "check source"
            messages.append(f"{source.source_id}: {detail}")
    return messages


def _monitor_source(
    source_id: str,
    runs: list[dict[str, Any]],
    expected_min_records: int | None,
    drop_ratio: float,
) -> SourceMonitorStatus:
    ordered = sorted(runs, key=_record_time)
    latest = ordered[-1]
    recent_count = int(latest.get("collected_records") or latest.get("recent_count") or 0)
    status = _normalize_status(_as_str(latest.get("status")), recent_count)
    error_type = _error_type(latest, status)
    last_success_at = _last_success_at(ordered)
    warning_reason = _warning_reason(ordered, recent_count, expected_min_records, drop_ratio, status)
    return SourceMonitorStatus(
        source_id=source_id,
        status=status,
        last_success_at=last_success_at,
        recent_count=recent_count,
        error_type=error_type,
        warning_reason=warning_reason,
    )


def _normalize_status(status: str, recent_count: int) -> str:
    if status in SUCCESS_STATUSES:
        return "success" if recent_count > 0 else "empty"
    if status == "error":
        return "source_error"
    if status:
        return status
    return "unknown"


def _error_type(record: dict[str, Any], status: str) -> str | None:
    message = _as_str(record.get("message")).casefold()
    if status == "missing_credentials":
        return "missing_credentials"
    if status == "permission_denied":
        return "permission_denied"
    if any(marker in message for marker in PERMISSION_MARKERS):
        return "permission_denied"
    if "rate limit" in message or "429" in message:
        return "rate_limited"
    if status in {"source_error", "parse_error", "rate_limited"}:
        return status
    return None


def _last_success_at(runs: list[dict[str, Any]]) -> str | None:
    for record in reversed(runs):
        status = _normalize_status(_as_str(record.get("status")), int(record.get("collected_records") or 0))
        if status == "success":
            return _record_time(record)
    return None


def _warning_reason(
    ordered: list[dict[str, Any]],
    recent_count: int,
    expected_min_records: int | None,
    drop_ratio: float,
    status: str,
) -> str | None:
    if expected_min_records is not None and recent_count < expected_min_records:
        return f"recent_count {recent_count} is below expected_min_records {expected_min_records}"
    if status in {"missing_credentials", "permission_denied", "source_error", "parse_error", "rate_limited"}:
        return None

    previous_success_counts = [
        int(record.get("collected_records") or 0)
        for record in ordered[:-1]
        if _normalize_status(_as_str(record.get("status")), int(record.get("collected_records") or 0)) == "success"
    ]
    if not previous_success_counts:
        return None
    baseline = sum(previous_success_counts) / len(previous_success_counts)
    if baseline > 0 and recent_count < baseline * drop_ratio:
        return f"recent_count {recent_count} dropped below {drop_ratio:.0%} of baseline {baseline:.1f}"
    return None


def _record_time(record: dict[str, Any]) -> str:
    return (
        _as_str(record.get("finished_at"))
        or _as_str(record.get("started_at"))
        or _as_str(record.get("_run_finished_at"))
        or _as_str(record.get("last_success_at"))
        or _as_str(record.get("run_id"))
    )


def _collection_run_times(records: list[dict[str, Any]]) -> dict[str, str]:
    run_times: dict[str, str] = {}
    for record in records:
        if record.get("type") != "collection_run":
            continue
        run_id = _as_str(record.get("run_id"))
        finished_at = _as_str(record.get("finished_at")) or _as_str(record.get("started_at"))
        if run_id and finished_at:
            run_times[run_id] = finished_at
    return run_times


def _with_run_time(record: dict[str, Any], run_times: dict[str, str]) -> dict[str, Any]:
    if record.get("finished_at") or record.get("started_at"):
        return record
    run_time = run_times.get(_as_str(record.get("run_id")))
    if not run_time:
        return record
    updated = dict(record)
    updated["_run_finished_at"] = run_time
    return updated


def _is_source_run_record(record: dict[str, Any]) -> bool:
    record_type = _as_str(record.get("type"))
    if record_type:
        return record_type == "source_result"
    if not _as_str(record.get("source_id")):
        return False
    return any(
        key in record
        for key in (
            "status",
            "collected_records",
            "recent_count",
            "expected_min_records",
            "last_success_at",
            "finished_at",
            "started_at",
            "message",
            "error_type",
        )
    )


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
