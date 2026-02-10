import csv
import json
from collections import Counter
import io
import re
from urllib.parse import quote, quote_plus

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.ebay import EbayBrowseAdapter
from app.adapters.errors import ExternalApiError
from app.adapters.mock import MockMarketAdapter
from app.adapters.rakuten import RakutenIchibaAdapter
from app.adapters.yahoo import YahooShoppingAdapter
from app.core.config import get_settings
from app.db.models import BatchJob, BatchRun, MarketItem, Opportunity, ReviewDecision, SourceItem
from app.db.session import get_db
from app.schemas import (
    ApiUsageItemResponse,
    ApiUsageResponse,
    BatchJobCreate,
    BatchJobRead,
    BatchRunRead,
    CategorySuggestionItemResponse,
    CategorySuggestionResponse,
    ComplianceReasonSummaryResponse,
    FxRateStatusResponse,
    LiveTrialRequest,
    LiveTrialResponse,
    MarketItemCreate,
    MarketItemRead,
    OpportunityRead,
    PipelineRunRequest,
    PipelineRunResponse,
    RejectReasonItem,
    RejectReasonSummaryResponse,
    ReasonCountItem,
    ReviewDecisionRead,
    ReviewDecisionRequest,
    ReviewQueueItem,
    ScanSummaryResponse,
    SourcePipelineSummary,
    SourceItemCreate,
    SourceItemRead,
    ThresholdSettingsResponse,
    TrialScanStateResetRequest,
    TrialScanStateResetResponse,
)
from app.services.analytics import summarize_compliance_reasons, summarize_reject_reasons
from app.services.api_usage import WINDOW_MINUTES, build_usage_snapshot
from app.services.batch import create_batch_job, run_batch_job
from app.services.categories import suggest_categories
from app.services.pipeline import run_pipeline
from app.services.fx_rate import get_usd_jpy_status, refresh_usd_jpy_rate_now
from app.services.review import get_review_queue, submit_review_decision
from app.services.scan_summary import backfill_scan_summary_from_history, get_scan_summary
from app.services.trial import build_scan_query_key, reset_live_trial_scan_state, run_live_trial
from app.services.rules import resolve_min_margin_rate

router = APIRouter()


def _extract_external_id(composite_id: str) -> str:
    raw = (composite_id or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if ":" in raw:
        return raw.split(":", 1)[1]
    return raw


def _extract_ebay_item_id(raw_id: str) -> str:
    if not raw_id:
        return ""
    if raw_id.isdigit():
        return raw_id
    # Browse API itemId is often: v1|123456789012|0
    match = re.search(r"\|(\d{8,20})\|", raw_id)
    if match:
        return match.group(1)
    return ""


def _is_fixture_like_id(value: str) -> bool:
    normalized = (value or "").lower()
    markers = (
        "src-cursor-",
        "mkt-cursor-",
        "mock-source:",
        "mock-market:",
    )
    return any(marker in normalized for marker in markers)


def _is_fixture_like_opportunity(opp: Opportunity) -> bool:
    source_site = (opp.source_item.source_site or "").lower()
    market_site = (opp.market_item.marketplace or "").lower()
    if source_site.startswith("mock"):
        return True
    if market_site.startswith("mock"):
        return True
    if _is_fixture_like_id(opp.source_item.source_item_id):
        return True
    if _is_fixture_like_id(opp.market_item.market_item_id):
        return True
    return False


def _build_source_link(source_item: SourceItem) -> str:
    site = (source_item.source_site or "").lower()
    external_id = _extract_external_id(source_item.source_item_id or "")
    query = quote_plus(source_item.title or external_id or "")
    if external_id.startswith("http://") or external_id.startswith("https://"):
        return external_id
    if "yahoo" in site:
        direct = _build_yahoo_item_link(external_id)
        if direct:
            return direct
        return f"https://shopping.yahoo.co.jp/search?p={query}"
    if "rakuten" in site:
        direct = _build_rakuten_item_link(external_id)
        if direct:
            return direct
        return f"https://search.rakuten.co.jp/search/mall/{query}/"
    if "mercari" in site:
        return f"https://jp.mercari.com/search?keyword={query}"
    if "mock" in site:
        return f"https://shopping.yahoo.co.jp/search?p={query}"
    return ""


def _build_market_link(market_item: MarketItem) -> str:
    site = (market_item.marketplace or "").lower()
    external_id = _extract_external_id((market_item.market_item_id or "").strip())
    query = quote_plus(market_item.title or external_id)
    if "ebay" in site:
        if external_id.startswith("http://") or external_id.startswith("https://"):
            return external_id
        ebay_item_id = _extract_ebay_item_id(external_id)
        if ebay_item_id:
            return f"https://www.ebay.com/itm/{ebay_item_id}"
        return f"https://www.ebay.com/sch/i.html?_nkw={query}"
    return ""


def _build_rakuten_item_link(external_id: str) -> str:
    if ":" not in external_id:
        return ""
    shop, item = external_id.split(":", 1)
    if not shop or not item:
        return ""
    if "/" in shop or "/" in item:
        return ""
    return f"https://item.rakuten.co.jp/{quote(shop)}/{quote(item)}/"


def _build_yahoo_item_link(external_id: str) -> str:
    if ":" not in external_id:
        return ""
    store, item = external_id.split(":", 1)
    if not store or not item:
        return ""
    if "/" in store or "/" in item:
        return ""
    return f"https://store.shopping.yahoo.co.jp/{quote(store)}/{quote(item)}.html"


def _extract_threshold_overrides(payload) -> dict[str, float]:
    thresholds = getattr(payload, "thresholds", None)
    if thresholds is None:
        return {}
    values = thresholds.model_dump(exclude_none=True)
    return {str(key): float(value) for key, value in values.items()}


def _extract_trace_float(decision_trace: str, key: str, fallback: float = 0.0) -> float:
    try:
        payload = json.loads(decision_trace or "{}")
    except json.JSONDecodeError:
        return float(fallback)
    value = payload.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return float(fallback)
    return float(fallback)


def _csv_response(filename: str, headers: list[str], rows: list[list[str]]) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    data = buffer.getvalue()
    buffer.close()
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/v1/source-items", response_model=SourceItemRead)
def create_source_item(payload: SourceItemCreate, db: Session = Depends(get_db)) -> SourceItem:
    item = SourceItem(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="source_item_id already exists") from exc
    db.refresh(item)
    return item


@router.get("/v1/source-items", response_model=list[SourceItemRead])
def list_source_items(db: Session = Depends(get_db)) -> list[SourceItem]:
    return db.query(SourceItem).order_by(SourceItem.id.desc()).all()


@router.post("/v1/market-items", response_model=MarketItemRead)
def create_market_item(payload: MarketItemCreate, db: Session = Depends(get_db)) -> MarketItem:
    item = MarketItem(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="market_item_id already exists") from exc
    db.refresh(item)
    return item


@router.get("/v1/market-items", response_model=list[MarketItemRead])
def list_market_items(db: Session = Depends(get_db)) -> list[MarketItem]:
    return db.query(MarketItem).order_by(MarketItem.id.desc()).all()


@router.post("/v1/pipeline/run", response_model=PipelineRunResponse)
def run_pipeline_route(payload: PipelineRunRequest, db: Session = Depends(get_db)) -> PipelineRunResponse:
    source_item = db.get(SourceItem, payload.source_item_id)
    if not source_item:
        raise HTTPException(status_code=404, detail="source item not found")

    opportunities = run_pipeline(
        db=db,
        source_item=source_item,
        category=payload.category,
        only_small_items=payload.only_small_items,
        threshold_overrides=_extract_threshold_overrides(payload),
    )

    counts = Counter(o.decision for o in opportunities)
    return PipelineRunResponse(
        source_item_id=source_item.id,
        created_opportunities=len(opportunities),
        auto_accept_count=counts.get("auto_accept", 0),
        human_review_count=counts.get("human_review", 0),
        reject_count=counts.get("reject", 0),
        opportunities=opportunities,
    )


@router.get("/v1/opportunities", response_model=list[OpportunityRead])
def list_opportunities(
    decision: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[Opportunity]:
    query = db.query(Opportunity).order_by(Opportunity.id.desc())
    if decision:
        query = query.filter(Opportunity.decision == decision)
    return query.limit(limit).all()


@router.get("/v1/analysis/reject-reasons", response_model=RejectReasonSummaryResponse)
def get_reject_reason_summary(
    limit: int = Query(default=1000, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> RejectReasonSummaryResponse:
    total, reason_counts = summarize_reject_reasons(db, limit=limit)
    return RejectReasonSummaryResponse(
        total_rejects=total,
        reasons=[RejectReasonItem(reason=reason, count=count) for reason, count in reason_counts],
    )


@router.get("/v1/analysis/compliance-risks", response_model=ComplianceReasonSummaryResponse)
def get_compliance_risk_summary(
    limit: int = Query(default=1000, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> ComplianceReasonSummaryResponse:
    total, reason_counts = summarize_compliance_reasons(db, limit=limit)
    return ComplianceReasonSummaryResponse(
        total_flagged=total,
        reasons=[RejectReasonItem(reason=reason, count=count) for reason, count in reason_counts],
    )


@router.get("/v1/review/queue", response_model=list[ReviewQueueItem])
def list_review_queue(
    limit: int = Query(default=100, ge=1, le=500),
    include_mock: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[ReviewQueueItem]:
    fetch_limit = limit if include_mock else min(500, max(limit * 5, limit))
    opportunities = get_review_queue(db, limit=fetch_limit)
    if not include_mock:
        opportunities = [opp for opp in opportunities if not _is_fixture_like_opportunity(opp)][:limit]
    return [
        ReviewQueueItem(
            opportunity_id=opp.id,
            source_title=opp.source_item.title,
            market_title=opp.market_item.title,
            source_site=opp.source_item.source_site,
            source_item_external_id=opp.source_item.source_item_id,
            source_category=opp.source_item.category,
            source_condition=opp.source_item.condition,
            source_price_jpy=opp.source_item.price_jpy,
            source_shipping_jpy=opp.source_item.shipping_jpy,
            market_site=opp.market_item.marketplace,
            market_item_external_id=opp.market_item.market_item_id,
            market_category=opp.market_item.category,
            market_condition=opp.market_item.condition,
            market_price_usd=opp.market_item.price_usd,
            market_shipping_usd=opp.market_item.shipping_usd,
            market_revenue_jpy=_extract_trace_float(opp.decision_trace, "expected_revenue_jpy", 0.0),
            source_link=_build_source_link(opp.source_item),
            market_link=_build_market_link(opp.market_item),
            match_score=opp.match_score,
            accessory_score=opp.accessory_score,
            expected_profit_jpy=opp.expected_profit_jpy,
            expected_margin_rate=opp.expected_margin_rate,
            decision_trace=opp.decision_trace,
            created_at=opp.created_at,
        )
        for opp in opportunities
    ]


@router.post("/v1/review/{opportunity_id}", response_model=ReviewDecisionRead)
def post_review_decision(
    opportunity_id: int,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> ReviewDecision:
    try:
        decision = submit_review_decision(
            db=db,
            opportunity_id=opportunity_id,
            outcome=payload.outcome,
            reviewer=payload.reviewer,
            note=payload.note,
        )
    except ValueError as exc:
        if str(exc) == "opportunity_not_found":
            raise HTTPException(status_code=404, detail="opportunity_not_found") from exc
        if str(exc) == "already_reviewed":
            raise HTTPException(status_code=409, detail="already_reviewed") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return decision


@router.post("/v1/trial/live", response_model=LiveTrialResponse)
def run_live_trial_route(payload: LiveTrialRequest, db: Session = Depends(get_db)) -> LiveTrialResponse:
    try:
        source_adapter = YahooShoppingAdapter() if payload.source_site == "yahoo" else RakutenIchibaAdapter()
        market_adapter = EbayBrowseAdapter() if payload.market_source == "ebay" else MockMarketAdapter()
        result = run_live_trial(
            db=db,
            source_adapter=source_adapter,
            market_adapter=market_adapter,
            source_site=payload.source_site,
            market_source=payload.market_source,
            query=payload.query,
            category=payload.category,
            source_limit=payload.source_limit,
            market_limit=payload.market_limit,
            run_pipeline_top_n=payload.run_pipeline_top_n,
            scan_cooldown_minutes=payload.scan_cooldown_minutes,
            only_small_items=False,
            listing_condition_filter=payload.item_condition,
            threshold_overrides=_extract_threshold_overrides(payload),
        )
    except ExternalApiError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return LiveTrialResponse(
        query=result.query,
        category=result.category,
        source_site=result.source_site,
        market_source=payload.market_source,
        imported_source_items=result.imported_source_items,
        imported_market_items=result.imported_market_items,
        processed_source_items=result.processed_source_items,
        skipped_recent_source_items=result.skipped_recent_source_items,
        source_cursor=result.source_cursor,
        market_cursor=result.market_cursor,
        scan_cooldown_minutes=result.scan_cooldown_minutes,
        run_total_rejects=result.run_total_rejects,
        run_total_compliance_flagged=result.run_total_compliance_flagged,
        run_reject_reasons=[
            ReasonCountItem(reason=reason, count=count) for reason, count in result.run_reject_reasons
        ],
        run_compliance_reasons=[
            ReasonCountItem(reason=reason, count=count) for reason, count in result.run_compliance_reasons
        ],
        source_runs=[
            SourcePipelineSummary(
                source_item_id=item.source_item_id,
                created_opportunities=item.created_opportunities,
                auto_accept_count=item.auto_accept_count,
                human_review_count=item.human_review_count,
                reject_count=item.reject_count,
            )
            for item in result.results
        ],
    )


@router.post("/v1/trial/reset-state", response_model=TrialScanStateResetResponse)
def reset_live_trial_state_route(
    payload: TrialScanStateResetRequest,
    db: Session = Depends(get_db),
) -> TrialScanStateResetResponse:
    state = reset_live_trial_scan_state(
        db=db,
        source_site=payload.source_site,
        market_source=payload.market_source,
        query=payload.query,
        category=payload.category,
        listing_condition_filter=payload.item_condition,
    )
    return TrialScanStateResetResponse(
        source_site=state.source_site,
        market_source=state.market_source,
        query=state.query,
        category=state.category,
        source_cursor=state.source_cursor,
        market_cursor=state.market_cursor,
    )


@router.get("/v1/trial/summary", response_model=ScanSummaryResponse)
def get_trial_summary_route(
    source_site: str = Query(..., min_length=1),
    market_source: str = Query(..., min_length=1),
    query: str = Query(..., min_length=1),
    category: str = Query(..., min_length=1),
    item_condition: str = Query(default="any"),
    db: Session = Depends(get_db),
) -> ScanSummaryResponse:
    query_key = build_scan_query_key(query=query, listing_condition_filter=item_condition)
    summary = get_scan_summary(
        db=db,
        source_site=source_site,
        market_source=market_source,
        query=query_key,
        category=category,
    )
    if summary is None:
        summary = backfill_scan_summary_from_history(
            db=db,
            source_site=source_site,
            market_source=market_source,
            query=query_key,
            category=category,
        )
        if summary is None:
            return ScanSummaryResponse(
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
                pair_total=0,
                reject_reasons=[],
                compliance_reasons=[],
                last_run_at=None,
            )

    return ScanSummaryResponse(
        source_site=summary.source_site,
        market_source=summary.market_source,
        query=query,
        category=summary.category,
        total_runs=summary.total_runs,
        total_source_items_imported=summary.total_source_items_imported,
        total_market_items_imported=summary.total_market_items_imported,
        total_source_items_processed=summary.total_source_items_processed,
        pair_auto_accept_total=summary.pair_auto_accept_total,
        pair_human_review_total=summary.pair_human_review_total,
        pair_reject_total=summary.pair_reject_total,
        pair_total=summary.pair_auto_accept_total + summary.pair_human_review_total + summary.pair_reject_total,
        reject_reasons=[ReasonCountItem(reason=reason, count=count) for reason, count in summary.pair_reject_reasons],
        compliance_reasons=[
            ReasonCountItem(reason=reason, count=count) for reason, count in summary.pair_compliance_reasons
        ],
        last_run_at=summary.last_run_at,
    )


@router.get("/v1/analysis/api-usage", response_model=ApiUsageResponse)
def get_api_usage() -> ApiUsageResponse:
    items = build_usage_snapshot(get_settings())
    return ApiUsageResponse(
        window_minutes=WINDOW_MINUTES,
        items=[
            ApiUsageItemResponse(
                provider=item.provider,
                calls_last_hour=item.calls_last_hour,
                hourly_budget=item.hourly_budget,
                usage_rate_percent=item.usage_rate_percent,
                remaining_calls=item.remaining_calls,
                usage_basis=item.usage_basis,
                limit_window=item.limit_window,
                note=item.note,
            )
            for item in items
        ],
    )


@router.get("/v1/system/fx-rate", response_model=FxRateStatusResponse)
def get_fx_rate_status(db: Session = Depends(get_db)) -> FxRateStatusResponse:
    status = get_usd_jpy_status(db)
    return FxRateStatusResponse(
        pair=status.pair,
        rate=status.rate,
        source=status.source,
        fetched_at=status.fetched_at,
        next_refresh_at=status.next_refresh_at,
        last_error=status.last_error,
        auto_update_enabled=get_settings().fx_auto_update_enabled,
    )


@router.get("/v1/system/thresholds", response_model=ThresholdSettingsResponse)
def get_threshold_settings(category: str | None = Query(default=None)) -> ThresholdSettingsResponse:
    settings = get_settings()
    category_value = (category or "").strip()
    resolved_margin_rate = resolve_min_margin_rate(category_value, settings) if category_value else settings.min_expected_margin_rate
    return ThresholdSettingsResponse(
        category=category_value or None,
        min_auto_accept_score=settings.min_auto_accept_score,
        min_human_review_score=settings.min_human_review_score,
        min_title_similarity_auto_accept=settings.min_title_similarity_auto_accept,
        min_title_similarity_human_review=settings.min_title_similarity_human_review,
        min_expected_profit_jpy=settings.min_expected_profit_jpy,
        min_expected_margin_rate=resolved_margin_rate,
        accessory_reject_score=settings.accessory_reject_score,
    )


@router.post("/v1/system/fx-rate/refresh", response_model=FxRateStatusResponse)
def refresh_fx_rate_status(db: Session = Depends(get_db)) -> FxRateStatusResponse:
    try:
        status = refresh_usd_jpy_rate_now(db)
    except ExternalApiError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FxRateStatusResponse(
        pair=status.pair,
        rate=status.rate,
        source=status.source,
        fetched_at=status.fetched_at,
        next_refresh_at=status.next_refresh_at,
        last_error=status.last_error,
        auto_update_enabled=get_settings().fx_auto_update_enabled,
    )


@router.get("/v1/export/opportunities.csv")
def export_opportunities_csv(
    limit: int = Query(default=2000, ge=1, le=10000),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    opportunities = db.query(Opportunity).order_by(Opportunity.id.desc()).limit(limit).all()
    rows: list[list[str]] = []
    for opp in opportunities:
        rows.append(
            [
                str(opp.id),
                opp.created_at.isoformat(),
                opp.decision,
                f"{opp.match_score:.6f}",
                f"{opp.accessory_score:.6f}",
                f"{opp.expected_profit_jpy:.2f}",
                f"{opp.expected_margin_rate:.6f}",
                opp.source_item.source_site,
                opp.source_item.source_item_id,
                opp.source_item.title,
                opp.market_item.marketplace,
                opp.market_item.market_item_id,
                opp.market_item.title,
                opp.decision_trace,
            ]
        )
    return _csv_response(
        filename="opportunities.csv",
        headers=[
            "opportunity_id",
            "created_at",
            "decision",
            "match_score",
            "accessory_score",
            "expected_profit_jpy",
            "expected_margin_rate",
            "source_site",
            "source_item_id",
            "source_title",
            "market_site",
            "market_item_id",
            "market_title",
            "decision_trace",
        ],
        rows=rows,
    )


@router.get("/v1/export/reviews.csv")
def export_reviews_csv(
    limit: int = Query(default=2000, ge=1, le=10000),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    reviews = db.query(ReviewDecision).order_by(ReviewDecision.id.desc()).limit(limit).all()
    rows: list[list[str]] = []
    for review in reviews:
        opp = db.get(Opportunity, review.opportunity_id)
        source_id = ""
        source_title = ""
        market_id = ""
        market_title = ""
        if opp:
            source_id = opp.source_item.source_item_id
            source_title = opp.source_item.title
            market_id = opp.market_item.market_item_id
            market_title = opp.market_item.title
        rows.append(
            [
                str(review.id),
                str(review.opportunity_id),
                review.created_at.isoformat(),
                review.outcome,
                review.reviewer,
                review.note,
                source_id,
                source_title,
                market_id,
                market_title,
            ]
        )
    return _csv_response(
        filename="reviews.csv",
        headers=[
            "review_id",
            "opportunity_id",
            "created_at",
            "outcome",
            "reviewer",
            "note",
            "source_item_id",
            "source_title",
            "market_item_id",
            "market_title",
        ],
        rows=rows,
    )


@router.get("/v1/export/api-usage.csv")
def export_api_usage_csv() -> StreamingResponse:
    items = build_usage_snapshot(get_settings())
    rows = [
        [
            item.provider,
            str(item.calls_last_hour),
            "" if item.hourly_budget is None else str(item.hourly_budget),
            "" if item.usage_rate_percent is None else f"{item.usage_rate_percent:.4f}",
            "" if item.remaining_calls is None else str(item.remaining_calls),
            item.usage_basis,
            item.limit_window,
            item.note,
        ]
        for item in items
    ]
    return _csv_response(
        filename="api_usage.csv",
        headers=[
            "provider",
            "calls_last_hour",
            "hourly_budget",
            "usage_rate_percent",
            "remaining_calls",
            "usage_basis",
            "limit_window",
            "note",
        ],
        rows=rows,
    )


@router.get("/v1/categories/suggestions", response_model=CategorySuggestionResponse)
def get_category_suggestions(
    source_site: str = Query(default="yahoo"),
    market_source: str = Query(default="ebay"),
    query_text: str = Query(default="", alias="query"),
    selected_category: str = Query(default=""),
    search_text: str = Query(default="", alias="q"),
    limit: int = Query(default=50, ge=1, le=200),
) -> CategorySuggestionResponse:
    items = suggest_categories(
        source_site=source_site,
        market_source=market_source,
        query_text=query_text,
        selected_category=selected_category,
        search_text=search_text,
        limit=limit,
    )
    return CategorySuggestionResponse(
        total=len(items),
        items=[
            CategorySuggestionItemResponse(
                key=item.key,
                internal_category=item.internal_category,
                label_ja=item.label_ja,
                source_hint=item.source_hint,
                market_hint=item.market_hint,
                aliases=list(item.aliases),
                score=item.score,
            )
            for item in items
        ],
    )


@router.post("/v1/batch/jobs", response_model=BatchJobRead)
def create_batch_job_route(payload: BatchJobCreate, db: Session = Depends(get_db)) -> BatchJob:
    try:
        return create_batch_job(db, **payload.model_dump())
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="batch_job_name_already_exists") from exc


@router.get("/v1/batch/jobs", response_model=list[BatchJobRead])
def list_batch_jobs(db: Session = Depends(get_db)) -> list[BatchJob]:
    return db.query(BatchJob).order_by(BatchJob.id.desc()).all()


@router.post("/v1/batch/jobs/{job_id}/run", response_model=BatchRunRead)
def run_batch_job_now(job_id: int, db: Session = Depends(get_db)) -> BatchRun:
    job = db.get(BatchJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="batch_job_not_found")
    return run_batch_job(db, job)


@router.get("/v1/batch/runs", response_model=list[BatchRunRead])
def list_batch_runs(
    job_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[BatchRun]:
    query = db.query(BatchRun).order_by(BatchRun.id.desc())
    if job_id is not None:
        query = query.filter(BatchRun.job_id == job_id)
    return query.limit(limit).all()


@router.get("/review", response_class=HTMLResponse)
def review_page() -> HTMLResponse:
    html = """
<!doctype html>
<html lang=\"ja\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Human Review Queue</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; margin: 24px; }
    h1 { margin-bottom: 16px; }
    .row { border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
    .meta { color: #444; font-size: 13px; }
    button { margin-right: 8px; }
    textarea { width: 100%; min-height: 56px; margin-top: 8px; }
  </style>
</head>
<body>
  <h1>Human Review Queue</h1>
  <div id=\"list\"></div>
  <script>
    async function loadQueue() {
      const res = await fetch('/v1/review/queue?limit=50');
      const items = await res.json();
      const list = document.getElementById('list');
      list.innerHTML = '';
      for (const item of items) {
        const el = document.createElement('div');
        el.className = 'row';
        el.innerHTML = `
          <div><strong>Source:</strong> ${item.source_title}</div>
          <div><strong>Market:</strong> ${item.market_title}</div>
          <div class=\"meta\">opportunity_id=${item.opportunity_id} | match=${item.match_score.toFixed(2)} | accessory=${item.accessory_score.toFixed(2)} | profit=${Math.round(item.expected_profit_jpy)} JPY | margin=${(item.expected_margin_rate*100).toFixed(1)}%</div>
          <textarea id=\"note-${item.opportunity_id}\" placeholder=\"review note\"></textarea>
          <div>
            <button onclick=\"submitDecision(${item.opportunity_id}, 'approve')\">Approve</button>
            <button onclick=\"submitDecision(${item.opportunity_id}, 'reject')\">Reject</button>
          </div>
        `;
        list.appendChild(el);
      }
    }

    async function submitDecision(id, outcome) {
      const noteEl = document.getElementById(`note-${id}`);
      const note = noteEl ? noteEl.value : '';
      const res = await fetch(`/v1/review/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ outcome, reviewer: 'ui', note })
      });
      if (!res.ok) {
        alert('failed: ' + (await res.text()));
      }
      await loadQueue();
    }

    loadQueue();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)
