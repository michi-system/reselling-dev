from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Opportunity, ScanSummary, SourceScanHistory


@dataclass
class ScanSummarySnapshot:
    source_site: str
    market_source: str
    query: str
    category: str
    total_runs: int
    total_source_items_imported: int
    total_market_items_imported: int
    total_source_items_processed: int
    pair_auto_accept_total: int
    pair_human_review_total: int
    pair_reject_total: int
    pair_reject_reasons: list[tuple[str, int]]
    pair_compliance_reasons: list[tuple[str, int]]
    last_run_at: datetime | None


def upsert_scan_summary_totals(
    db: Session,
    source_site: str,
    market_source: str,
    query: str,
    category: str,
    imported_source_items: int,
    imported_market_items: int,
    processed_source_items: int,
    pair_auto_accept: int,
    pair_human_review: int,
    pair_reject: int,
    pair_reject_reasons: Counter[str],
    pair_compliance_reasons: Counter[str],
    run_at: datetime,
) -> ScanSummary:
    run_at_utc = _as_utc(run_at)
    row = _get_or_create_row(
        db=db,
        source_site=source_site,
        market_source=market_source,
        query=query,
        category=category,
    )
    if _needs_daily_reset(row.last_run_at, run_at_utc):
        _reset_row_counters(row)

    row.total_runs += 1
    row.total_source_items_imported += max(0, int(imported_source_items))
    row.total_market_items_imported += max(0, int(imported_market_items))
    row.total_source_items_processed += max(0, int(processed_source_items))
    row.pair_auto_accept_total += max(0, int(pair_auto_accept))
    row.pair_human_review_total += max(0, int(pair_human_review))
    row.pair_reject_total += max(0, int(pair_reject))

    reject_counter = _load_counter(row.pair_reject_reasons_json)
    reject_counter.update(pair_reject_reasons)
    row.pair_reject_reasons_json = json.dumps(dict(reject_counter), ensure_ascii=False)

    compliance_counter = _load_counter(row.pair_compliance_reasons_json)
    compliance_counter.update(pair_compliance_reasons)
    row.pair_compliance_reasons_json = json.dumps(dict(compliance_counter), ensure_ascii=False)

    row.last_run_at = run_at_utc
    db.flush()
    return row


def get_scan_summary(
    db: Session,
    source_site: str,
    market_source: str,
    query: str,
    category: str,
) -> ScanSummarySnapshot | None:
    now_utc = datetime.now(UTC)
    row = db.scalar(
        select(ScanSummary).where(
            ScanSummary.source_site == source_site,
            ScanSummary.market_source == market_source,
            ScanSummary.query == query,
            ScanSummary.category == category,
        )
    )
    if row is None:
        return None
    if _needs_daily_reset(row.last_run_at, now_utc):
        _reset_row_counters(row)
        row.last_run_at = None
        db.commit()
        db.refresh(row)
    _repair_missing_import_totals(db=db, row=row, now_utc=now_utc)

    reject_counter = _load_counter(row.pair_reject_reasons_json)
    compliance_counter = _load_counter(row.pair_compliance_reasons_json)
    return ScanSummarySnapshot(
        source_site=row.source_site,
        market_source=row.market_source,
        query=row.query,
        category=row.category,
        total_runs=int(row.total_runs),
        total_source_items_imported=int(row.total_source_items_imported),
        total_market_items_imported=int(row.total_market_items_imported),
        total_source_items_processed=int(row.total_source_items_processed),
        pair_auto_accept_total=int(row.pair_auto_accept_total),
        pair_human_review_total=int(row.pair_human_review_total),
        pair_reject_total=int(row.pair_reject_total),
        pair_reject_reasons=reject_counter.most_common(),
        pair_compliance_reasons=compliance_counter.most_common(),
        last_run_at=row.last_run_at,
    )


def backfill_scan_summary_from_history(
    db: Session,
    source_site: str,
    market_source: str,
    query: str,
    category: str,
) -> ScanSummarySnapshot | None:
    now_utc = datetime.now(UTC)
    raw_rows = list(
        db.scalars(
            select(SourceScanHistory).where(
                SourceScanHistory.source_site == source_site,
                SourceScanHistory.query == query,
                SourceScanHistory.category == category,
            )
        )
    )
    history_rows = [
        row
        for row in raw_rows
        if _is_same_reset_day(_as_utc(row.scanned_at), now_utc)
    ]
    if not history_rows:
        return None

    pair_auto = 0
    pair_human = 0
    pair_reject = 0
    source_ids: list[int] = []
    last_run_at: datetime | None = None
    for row in history_rows:
        source_ids.append(int(row.source_item_id))
        pair_auto += int(row.auto_accept_count or 0)
        pair_human += int(row.human_review_count or 0)
        pair_reject += int(row.reject_count or 0)
        scanned_at = _as_utc(row.scanned_at)
        if last_run_at is None or scanned_at > last_run_at:
            last_run_at = scanned_at

    reject_counter: Counter[str] = Counter()
    compliance_counter: Counter[str] = Counter()
    if source_ids:
        opps = list(db.scalars(select(Opportunity).where(Opportunity.source_item_id.in_(source_ids))))
        unique_market_ids = {int(opp.market_item_id) for opp in opps}
        for opp in opps:
            trace = _parse_trace(opp.decision_trace)
            if opp.decision == "reject":
                reject_counter[_extract_reject_reason(trace)] += 1
            for reason in _extract_compliance_reasons(trace):
                compliance_counter[reason] += 1
    else:
        unique_market_ids = set()

    row = _get_or_create_row(
        db=db,
        source_site=source_site,
        market_source=market_source,
        query=query,
        category=category,
    )
    if _needs_daily_reset(row.last_run_at, now_utc):
        _reset_row_counters(row)
    row.total_runs = max(1, int(row.total_runs))
    row.total_source_items_imported = len(history_rows)
    row.total_market_items_imported = len(unique_market_ids)
    row.total_source_items_processed = len(history_rows)
    row.pair_auto_accept_total = pair_auto
    row.pair_human_review_total = pair_human
    row.pair_reject_total = pair_reject
    row.pair_reject_reasons_json = json.dumps(dict(reject_counter), ensure_ascii=False)
    row.pair_compliance_reasons_json = json.dumps(dict(compliance_counter), ensure_ascii=False)
    row.last_run_at = last_run_at
    db.commit()

    return get_scan_summary(
        db=db,
        source_site=source_site,
        market_source=market_source,
        query=query,
        category=category,
    )


def _get_or_create_row(
    db: Session,
    source_site: str,
    market_source: str,
    query: str,
    category: str,
) -> ScanSummary:
    row = db.scalar(
        select(ScanSummary).where(
            ScanSummary.source_site == source_site,
            ScanSummary.market_source == market_source,
            ScanSummary.query == query,
            ScanSummary.category == category,
        )
    )
    if row is not None:
        return row

    row = ScanSummary(
        source_site=source_site,
        market_source=market_source,
        query=query,
        category=category,
        total_runs=0,
        total_source_items_imported=0,
        total_market_items_imported=0,
        total_source_items_processed=0,
        pair_auto_accept_total=0,
        pair_human_review_total=0,
        pair_reject_total=0,
        pair_reject_reasons_json="{}",
        pair_compliance_reasons_json="{}",
        last_run_at=None,
    )
    db.add(row)
    db.flush()
    return row


def _load_counter(value: str) -> Counter[str]:
    text = (value or "").strip()
    if not text:
        return Counter()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return Counter()
    if not isinstance(data, dict):
        return Counter()

    counter: Counter[str] = Counter()
    for key, count in data.items():
        name = str(key).strip()
        if not name:
            continue
        try:
            parsed = int(count)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            counter[name] = parsed
    return counter


def _repair_missing_import_totals(db: Session, row: ScanSummary, now_utc: datetime) -> None:
    needs_source = int(row.total_source_items_imported or 0) <= 0
    needs_market = int(row.total_market_items_imported or 0) <= 0
    if (not needs_source and not needs_market) or int(row.total_source_items_processed or 0) <= 0:
        return

    history_rows = list(
        db.scalars(
            select(SourceScanHistory).where(
                SourceScanHistory.source_site == row.source_site,
                SourceScanHistory.query == row.query,
                SourceScanHistory.category == row.category,
            )
        )
    )
    day_rows = [h for h in history_rows if _is_same_reset_day(_as_utc(h.scanned_at), now_utc)]
    source_ids = {int(h.source_item_id) for h in day_rows}

    if needs_source:
        if source_ids:
            row.total_source_items_imported = max(int(row.total_source_items_imported or 0), len(source_ids))
        else:
            # Older rows may have only processed totals populated.
            row.total_source_items_imported = max(
                int(row.total_source_items_imported or 0),
                int(row.total_source_items_processed or 0),
            )

    if needs_market and source_ids:
        market_ids = set(
            db.scalars(
                select(Opportunity.market_item_id).where(Opportunity.source_item_id.in_(list(source_ids)))
            )
        )
        row.total_market_items_imported = max(int(row.total_market_items_imported or 0), len(market_ids))

    db.flush()


def _reset_row_counters(row: ScanSummary) -> None:
    row.total_runs = 0
    row.total_source_items_imported = 0
    row.total_market_items_imported = 0
    row.total_source_items_processed = 0
    row.pair_auto_accept_total = 0
    row.pair_human_review_total = 0
    row.pair_reject_total = 0
    row.pair_reject_reasons_json = "{}"
    row.pair_compliance_reasons_json = "{}"


def _needs_daily_reset(last_run_at: datetime | None, now_utc: datetime) -> bool:
    if last_run_at is None:
        return False
    return _day_key(_as_utc(last_run_at)) != _day_key(_as_utc(now_utc))


def _is_same_reset_day(dt_utc: datetime, now_utc: datetime) -> bool:
    return _day_key(dt_utc) == _day_key(now_utc)


def _day_key(dt_utc: datetime) -> str:
    tz = _resolve_reset_tz()
    return _as_utc(dt_utc).astimezone(tz).date().isoformat()


def _resolve_reset_tz() -> ZoneInfo:
    name = (get_settings().scan_summary_reset_timezone or "").strip() or "Asia/Tokyo"
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def _parse_trace(decision_trace: str) -> dict[str, object]:
    try:
        trace = json.loads(decision_trace or "{}")
    except json.JSONDecodeError:
        return {}
    if isinstance(trace, dict):
        return trace
    return {}


def _extract_reject_reason(trace: dict[str, object]) -> str:
    reason = str(trace.get("reject_reason", "")).strip()
    if reason:
        return reason
    accessory_reasons = trace.get("accessory_reasons")
    if isinstance(accessory_reasons, list) and accessory_reasons:
        return "accessory_rule"
    return "unknown"


def _extract_compliance_reasons(trace: dict[str, object]) -> list[str]:
    reasons = trace.get("compliance_reasons", [])
    if not isinstance(reasons, list):
        return []
    normalized: list[str] = []
    for reason in reasons:
        value = str(reason).strip()
        if value:
            normalized.append(value)
    return normalized


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
