"""Pure visit-log decisions, kept free of Home Assistant imports so tests can load them."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# Records fetched per poll. More visits than this between two polls are lost.
VISIT_HISTORY_SIZE = 20


@dataclass(frozen=True, slots=True)
class VisitBatch:
    """Visits to report, oldest first, and the cursor to store afterwards."""

    visits: list[dict[str, Any]]
    last_record_id: int | None


def new_visits(records: list[dict[str, Any]] | None, last_record_id: int | None) -> VisitBatch:
    """Pick the records newer than the stored cursor.

    `records` is the API's newest-first list, or None when the fetch failed. Record
    ids only grow, so they work as a cursor. With no stored cursor (first setup),
    existing records are history and nothing is reported, so adding the integration
    doesn't replay old visits. An empty first fetch (a freshly paired box) starts the
    cursor at 0, so the box's first record is reported.
    """
    if records is None:
        return VisitBatch(visits=[], last_record_id=last_record_id)
    ids = [record["recordId"] for record in records if isinstance(record.get("recordId"), int)]
    if not ids:
        return VisitBatch(visits=[], last_record_id=0 if last_record_id is None else last_record_id)
    newest = max(ids)
    if last_record_id is None:
        return VisitBatch(visits=[], last_record_id=newest)
    fresh = [record for record in records if isinstance(record.get("recordId"), int) and record["recordId"] > last_record_id]
    return VisitBatch(visits=sorted(fresh, key=lambda record: record["recordId"]), last_record_id=max(newest, last_record_id))


@dataclass(frozen=True, slots=True)
class DayTotals:
    """A cat's visits and time in the box so far today, in the account's local day."""

    visits: int
    seconds: float


def today_totals(entries: list[dict[str, Any]] | None) -> DayTotals | None:
    """Sum the per-visit entries of the day statistic (periodType 1); None if the fetch failed.

    The app reads these, not the cat profile's `number` and `costTime`, which go stale.
    """
    if entries is None:
        return None
    return DayTotals(
        visits=sum(int(entry.get("number") or 0) for entry in entries),
        seconds=float(sum(float(entry.get("costTime") or 0) for entry in entries)),
    )


def visit_event_data(serial: str, box_name: str | None, record: dict[str, Any]) -> dict[str, Any]:
    """Build the `ubpet_visit` event payload from one cat record.

    Uses `eventTime` (epoch ms). The record's `timeStr` is in China time.
    Unidentified visits carry `catInfoId` 0, which maps to `cat_id` None.
    """
    event_time = record.get("eventTime")
    return {
        "serial_number": serial,
        "box": box_name,
        "record_id": record.get("recordId"),
        "cat_id": record.get("catInfoId") or None,
        "cat": record.get("catNickname"),
        "weight_kg": record.get("weight"),
        "duration_s": record.get("costTime"),
        "event_type": record.get("eventType"),
        "time": datetime.fromtimestamp(event_time / 1000, UTC).isoformat() if isinstance(event_time, int) else None,
    }
