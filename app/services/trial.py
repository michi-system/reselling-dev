from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.base import ListingRecord, MarketAdapter, SourceAdapter
from app.core.config import get_settings
from app.db.models import MarketItem, Opportunity, ScanState, SourceItem, SourceScanHistory
from app.services.pipeline import run_pipeline
from app.services.scan_summary import upsert_scan_summary_totals

CURSOR_DONE = -1
RAKUTEN_MAX_OFFSET_EXCLUSIVE = 99 * 30
EBAY_MAX_OFFSET_EXCLUSIVE = 10000


@dataclass
class SourceRunResult:
    source_item_id: int
    created_opportunities: int
    auto_accept_count: int
    human_review_count: int
    reject_count: int


@dataclass
class LiveTrialResult:
    query: str
    category: str
    source_site: str
    imported_source_items: int
    imported_market_items: int
    processed_source_items: int
    skipped_recent_source_items: int
    source_cursor: int
    market_cursor: int
    scan_cooldown_minutes: int
    run_total_rejects: int
    run_total_compliance_flagged: int
    run_reject_reasons: list[tuple[str, int]]
    run_compliance_reasons: list[tuple[str, int]]
    results: list[SourceRunResult]


def normalize_live_trial_limits(
    source_site: str,
    source_limit: int,
    market_limit: int,
    run_pipeline_top_n: int,
) -> tuple[int, int, int]:
    source_max = 100

    normalized_source_limit = max(1, min(int(source_limit), source_max))
    # Keep source/market counts synchronized for simpler operation.
    # Caller-provided market_limit is ignored in live trial flow.
    normalized_market_limit = normalized_source_limit
    # Keep "取得/判定" concepts in UI, but operationally process all fetched source items.
    # This prevents fetch-only backlog when a smaller top_n is passed from caller.
    normalized_top_n = normalized_source_limit

    return normalized_source_limit, normalized_market_limit, normalized_top_n


def normalize_scan_cooldown_minutes(scan_cooldown_minutes: int) -> int:
    return max(1, min(int(scan_cooldown_minutes), 1440))


def build_scan_query_key(query: str, listing_condition_filter: str) -> str:
    normalized = (listing_condition_filter or "any").strip().lower()
    if normalized not in {"new", "used"}:
        return query
    return f"{query} [condition:{normalized}]"


def run_live_trial(
    db: Session,
    source_adapter: SourceAdapter,
    market_adapter: MarketAdapter,
    source_site: str,
    market_source: str,
    query: str,
    category: str,
    source_limit: int = 5,
    market_limit: int = 40,
    run_pipeline_top_n: int = 3,
    only_small_items: bool = True,
    listing_condition_filter: str = "any",
    threshold_overrides: dict[str, float] | None = None,
    scan_cooldown_minutes: int | None = None,
) -> LiveTrialResult:
    settings = get_settings()
    if scan_cooldown_minutes is None:
        scan_cooldown_minutes = settings.scan_cooldown_minutes
    scan_cooldown_minutes = normalize_scan_cooldown_minutes(scan_cooldown_minutes)

    source_limit, market_limit, run_pipeline_top_n = normalize_live_trial_limits(
        source_site=source_site,
        source_limit=source_limit,
        market_limit=market_limit,
        run_pipeline_top_n=run_pipeline_top_n,
    )
    scan_query_key = build_scan_query_key(query=query, listing_condition_filter=listing_condition_filter)

    state = _get_or_create_scan_state(
        db=db,
        source_site=source_site,
        market_source=market_source,
        query=scan_query_key,
        category=category,
    )
    state.source_cursor = _normalize_source_cursor(
        source_site=source_site,
        source_cursor=state.source_cursor,
        source_limit=source_limit,
    )
    state.market_cursor = _align_market_cursor(state.market_cursor, market_limit, market_source)

    # If source-side scan is already complete, stop immediately.
    # Market-only fetch is not useful because no source item remains for comparison.
    if state.source_cursor == CURSOR_DONE:
        if state.market_cursor != CURSOR_DONE:
            state.market_cursor = CURSOR_DONE
            db.commit()
            db.refresh(state)
        return LiveTrialResult(
            query=query,
            category=category,
            source_site=source_site,
            imported_source_items=0,
            imported_market_items=0,
            processed_source_items=0,
            skipped_recent_source_items=0,
            source_cursor=state.source_cursor,
            market_cursor=state.market_cursor,
            scan_cooldown_minutes=scan_cooldown_minutes,
            run_total_rejects=0,
            run_total_compliance_flagged=0,
            run_reject_reasons=[],
            run_compliance_reasons=[],
            results=[],
        )

    if state.source_cursor == CURSOR_DONE and state.market_cursor == CURSOR_DONE:
        return LiveTrialResult(
            query=query,
            category=category,
            source_site=source_site,
            imported_source_items=0,
            imported_market_items=0,
            processed_source_items=0,
            skipped_recent_source_items=0,
            source_cursor=state.source_cursor,
            market_cursor=state.market_cursor,
            scan_cooldown_minutes=scan_cooldown_minutes,
            run_total_rejects=0,
            run_total_compliance_flagged=0,
            run_reject_reasons=[],
            run_compliance_reasons=[],
            results=[],
        )

    source_records: list[ListingRecord] = []
    if state.source_cursor != CURSOR_DONE:
        source_records = source_adapter.fetch(
            query=query,
            category=category,
            limit=source_limit,
            cursor=state.source_cursor,
        )

    aligned_market_cursor = state.market_cursor
    market_records: list[ListingRecord] = []
    if aligned_market_cursor != CURSOR_DONE:
        market_records = market_adapter.fetch(
            query=query,
            category=category,
            limit=market_limit,
            cursor=aligned_market_cursor,
        )

    source_items = _upsert_source_items(db, source_records) if source_records else []
    current_market_items = _upsert_market_items(db, market_records) if market_records else []
    current_market_item_ids = [item.id for item in current_market_items]

    now = datetime.now(UTC)
    eligible_source_items, skipped_recent_count = _filter_recently_scanned_sources(
        db=db,
        source_items=source_items,
        source_site=source_site,
        query=scan_query_key,
        category=category,
        cooldown_minutes=scan_cooldown_minutes,
        now=now,
    )

    results: list[SourceRunResult] = []
    run_reject_counter: Counter[str] = Counter()
    run_compliance_counter: Counter[str] = Counter()
    run_total_rejects = 0
    run_total_compliance_flagged = 0
    run_pair_auto_accept = 0
    run_pair_human_review = 0
    run_pair_reject = 0
    run_pair_reject_reason_counter: Counter[str] = Counter()
    run_pair_compliance_counter: Counter[str] = Counter()
    process_items = eligible_source_items[: max(1, run_pipeline_top_n)]
    for source in process_items:
        opportunities = run_pipeline(
            db,
            source_item=source,
            category=category,
            only_small_items=only_small_items,
            listing_condition_filter=listing_condition_filter,
            threshold_overrides=threshold_overrides,
            market_item_ids=current_market_item_ids,
        )
        counts = {"auto_accept": 0, "human_review": 0, "reject": 0}
        source_reject_reason = ""
        source_compliance_reasons: set[str] = set()
        for opp in opportunities:
            counts[opp.decision] = counts.get(opp.decision, 0) + 1
            trace = _parse_trace(opp.decision_trace)
            if opp.decision == "reject":
                run_pair_reject += 1
                run_pair_reject_reason_counter[_extract_reject_reason(trace)] += 1
            elif opp.decision == "human_review":
                run_pair_human_review += 1
            elif opp.decision == "auto_accept":
                run_pair_auto_accept += 1
            compliance_reasons = _extract_compliance_reasons(trace)
            if compliance_reasons:
                for reason in compliance_reasons:
                    run_pair_compliance_counter[reason] += 1
                for reason in compliance_reasons:
                    source_compliance_reasons.add(reason)
            if opp.decision == "reject" and not source_reject_reason:
                source_reject_reason = _extract_reject_reason(trace)

        is_source_reject = counts.get("auto_accept", 0) == 0 and counts.get("human_review", 0) == 0
        if is_source_reject:
            run_total_rejects += 1
            run_reject_counter[source_reject_reason or "unknown"] += 1
        if source_compliance_reasons:
            run_total_compliance_flagged += 1
            for reason in source_compliance_reasons:
                run_compliance_counter[reason] += 1

        results.append(
            SourceRunResult(
                source_item_id=source.id,
                created_opportunities=len(opportunities),
                auto_accept_count=counts.get("auto_accept", 0),
                human_review_count=counts.get("human_review", 0),
                reject_count=counts.get("reject", 0),
            )
        )
        _upsert_source_scan_history(
            db=db,
            source_item_id=source.id,
                source_site=source_site,
                query=scan_query_key,
                category=category,
                scanned_at=now,
            auto_accept_count=counts.get("auto_accept", 0),
            human_review_count=counts.get("human_review", 0),
            reject_count=counts.get("reject", 0),
        )

    upsert_scan_summary_totals(
        db=db,
        source_site=source_site,
        market_source=market_source,
        query=scan_query_key,
        category=category,
        imported_source_items=len(source_items),
        imported_market_items=len(market_records),
        processed_source_items=len(process_items),
        pair_auto_accept=run_pair_auto_accept,
        pair_human_review=run_pair_human_review,
        pair_reject=run_pair_reject,
        pair_reject_reasons=run_pair_reject_reason_counter,
        pair_compliance_reasons=run_pair_compliance_counter,
        run_at=now,
    )

    state.source_cursor = _next_source_cursor(
        source_site=source_site,
        current_cursor=state.source_cursor,
        source_limit=source_limit,
        fetched_count=len(source_records),
    )
    state.market_cursor = _next_market_cursor(
        market_source=market_source,
        current_cursor=aligned_market_cursor,
        market_limit=market_limit,
        fetched_count=len(market_records),
    )
    db.commit()
    db.refresh(state)

    return LiveTrialResult(
        query=query,
        category=category,
        source_site=source_site,
        imported_source_items=len(source_items),
        imported_market_items=len(market_records),
        processed_source_items=len(process_items),
        skipped_recent_source_items=skipped_recent_count,
        source_cursor=state.source_cursor,
        market_cursor=state.market_cursor,
        scan_cooldown_minutes=scan_cooldown_minutes,
        run_total_rejects=run_total_rejects,
        run_total_compliance_flagged=run_total_compliance_flagged,
        run_reject_reasons=run_reject_counter.most_common(),
        run_compliance_reasons=run_compliance_counter.most_common(),
        results=results,
    )


def reset_live_trial_scan_state(
    db: Session,
    source_site: str,
    market_source: str,
    query: str,
    category: str,
    listing_condition_filter: str = "any",
) -> ScanState:
    scan_query_key = build_scan_query_key(query=query, listing_condition_filter=listing_condition_filter)
    state = _get_or_create_scan_state(
        db=db,
        source_site=source_site,
        market_source=market_source,
        query=scan_query_key,
        category=category,
    )
    state.source_cursor = 0
    state.market_cursor = 0
    db.commit()
    db.refresh(state)
    return state


def _get_or_create_scan_state(
    db: Session,
    source_site: str,
    market_source: str,
    query: str,
    category: str,
) -> ScanState:
    state = db.scalar(
        select(ScanState).where(
            ScanState.source_site == source_site,
            ScanState.market_source == market_source,
            ScanState.query == query,
            ScanState.category == category,
        )
    )
    if state is None:
        state = ScanState(
            source_site=source_site,
            market_source=market_source,
            query=query,
            category=category,
            source_cursor=0,
            market_cursor=0,
        )
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def _next_source_cursor(source_site: str, current_cursor: int, source_limit: int, fetched_count: int) -> int:
    if current_cursor == CURSOR_DONE:
        return CURSOR_DONE
    if fetched_count < source_limit:
        return CURSOR_DONE

    safe_current = max(0, int(current_cursor))
    safe_limit = max(1, int(source_limit))
    next_cursor = safe_current + safe_limit
    if (source_site or "").strip().lower() == "rakuten":
        if next_cursor >= RAKUTEN_MAX_OFFSET_EXCLUSIVE:
            return CURSOR_DONE
        return next_cursor
    return next_cursor


def _next_market_cursor(market_source: str, current_cursor: int, market_limit: int, fetched_count: int) -> int:
    if current_cursor == CURSOR_DONE:
        return CURSOR_DONE
    if fetched_count < market_limit:
        return CURSOR_DONE
    safe_current = max(0, int(current_cursor))
    safe_limit = max(1, int(market_limit))
    next_cursor = safe_current + safe_limit
    if (market_source or "").strip().lower() == "ebay":
        max_aligned = (EBAY_MAX_OFFSET_EXCLUSIVE // safe_limit) * safe_limit
        if next_cursor > max_aligned:
            return CURSOR_DONE
    return next_cursor


def _align_market_cursor(current_cursor: int, market_limit: int, market_source: str) -> int:
    if int(current_cursor) < 0:
        return CURSOR_DONE
    safe_limit = max(1, int(market_limit))
    safe_cursor = max(0, int(current_cursor))
    aligned = (safe_cursor // safe_limit) * safe_limit
    if (market_source or "").strip().lower() == "ebay":
        max_aligned = (EBAY_MAX_OFFSET_EXCLUSIVE // safe_limit) * safe_limit
        if aligned > max_aligned:
            return CURSOR_DONE
    return aligned


def _normalize_source_cursor(source_site: str, source_cursor: int, source_limit: int) -> int:
    if int(source_cursor) < 0:
        return CURSOR_DONE
    normalized_source_site = (source_site or "").strip().lower()
    safe_cursor = max(0, int(source_cursor))
    safe_limit = max(1, int(source_limit))
    if normalized_source_site != "rakuten":
        return safe_cursor

    # Backward compatibility:
    # old Rakuten cursor stored page index (1,2,3...). new semantics stores offset count.
    # Old implementation was capped to 30 records/page, so convert page index -> offset by 30.
    # Convert only when cursor does not match the current offset stride.
    if 1 <= safe_cursor <= 99 and safe_cursor % safe_limit != 0:
        safe_cursor = safe_cursor * 30
    return _normalize_rakuten_cursor(safe_cursor)


def _normalize_rakuten_cursor(source_cursor: int) -> int:
    if int(source_cursor) < 0:
        return CURSOR_DONE
    # Rakuten Ichiba API: page must be under 100 (offset 0..2969).
    safe_cursor = max(0, int(source_cursor))
    if safe_cursor >= RAKUTEN_MAX_OFFSET_EXCLUSIVE:
        return CURSOR_DONE
    return safe_cursor


def _filter_recently_scanned_sources(
    db: Session,
    source_items: list[SourceItem],
    source_site: str,
    query: str,
    category: str,
    cooldown_minutes: int,
    now: datetime,
) -> tuple[list[SourceItem], int]:
    if not source_items:
        return [], 0

    source_ids = [item.id for item in source_items]
    rows = list(
        db.scalars(
            select(SourceScanHistory).where(
                SourceScanHistory.source_item_id.in_(source_ids),
                SourceScanHistory.source_site == source_site,
                SourceScanHistory.query == query,
                SourceScanHistory.category == category,
            )
        )
    )
    history_by_source_id = {row.source_item_id: row for row in rows}
    threshold = now - timedelta(minutes=cooldown_minutes)

    eligible: list[SourceItem] = []
    skipped = 0
    for item in source_items:
        row = history_by_source_id.get(item.id)
        scanned_at = _as_utc(row.scanned_at) if row else None
        # Skip recent items only when previous scan produced no positive outcomes.
        if row and scanned_at and scanned_at > threshold and row.auto_accept_count == 0 and row.human_review_count == 0:
            skipped += 1
            continue
        eligible.append(item)
    return eligible, skipped


def _as_utc(value: datetime) -> datetime:
    # SQLite may deserialize timezone-aware values as naive datetimes.
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_trace(decision_trace: str) -> dict[str, object]:
    try:
        parsed = json.loads(decision_trace or "{}")
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
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


def _upsert_source_scan_history(
    db: Session,
    source_item_id: int,
    source_site: str,
    query: str,
    category: str,
    scanned_at: datetime,
    auto_accept_count: int,
    human_review_count: int,
    reject_count: int,
) -> None:
    row = db.scalar(
        select(SourceScanHistory).where(
            SourceScanHistory.source_item_id == source_item_id,
            SourceScanHistory.source_site == source_site,
            SourceScanHistory.query == query,
            SourceScanHistory.category == category,
        )
    )
    if row is None:
        row = SourceScanHistory(
            source_item_id=source_item_id,
            source_site=source_site,
            query=query,
            category=category,
        )
        db.add(row)

    row.scanned_at = scanned_at
    row.auto_accept_count = auto_accept_count
    row.human_review_count = human_review_count
    row.reject_count = reject_count


def _upsert_source_items(db: Session, records: list[ListingRecord]) -> list[SourceItem]:
    unique_records: dict[str, ListingRecord] = {}
    for record in records:
        unique_records[f"{record.site}:{record.external_id}"] = record

    items_map: dict[str, SourceItem] = {}
    for record in unique_records.values():
        item_id = f"{record.site}:{record.external_id}"
        item = db.scalar(select(SourceItem).where(SourceItem.source_item_id == item_id))
        if item is None:
            item = SourceItem(source_item_id=item_id, source_site=record.site)
            db.add(item)

        item.category = record.category
        item.title = record.title
        item.brand = record.brand
        item.model_number = record.model_number
        item.jan = record.code
        item.condition = (record.condition or "unknown").lower()
        item.price_jpy = float(record.price)
        item.shipping_jpy = float(record.shipping)
        item.weight_g = int(record.weight_g or 0)

        items_map[item_id] = item

    db.commit()
    items = list(items_map.values())
    for item in items:
        db.refresh(item)
    return items


def _upsert_market_items(db: Session, records: list[ListingRecord]) -> list[MarketItem]:
    unique_records: dict[str, ListingRecord] = {}
    for record in records:
        unique_records[f"{record.site}:{record.external_id}"] = record

    items_map: dict[str, MarketItem] = {}
    for record in unique_records.values():
        item_id = f"{record.site}:{record.external_id}"
        item = db.scalar(select(MarketItem).where(MarketItem.market_item_id == item_id))
        if item is None:
            item = MarketItem(market_item_id=item_id, marketplace=record.site)
            db.add(item)

        item.category = record.category
        item.title = record.title
        item.brand = record.brand
        item.model_number = record.model_number
        item.gtin = record.code
        item.condition = (record.condition or "unknown").lower()
        item.price_usd = float(record.price)
        item.shipping_usd = float(record.shipping)
        item.price_confidence = record.price_confidence or "semi_trusted"

        items_map[item_id] = item

    db.commit()
    items = list(items_map.values())
    for item in items:
        db.refresh(item)
    return items


def latest_opportunities_for_source(db: Session, source_item_id: int, limit: int = 20) -> list[Opportunity]:
    stmt = (
        select(Opportunity)
        .where(Opportunity.source_item_id == source_item_id)
        .order_by(Opportunity.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))
