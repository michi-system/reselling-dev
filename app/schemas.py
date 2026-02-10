from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceItemCreate(BaseModel):
    source_site: str
    source_item_id: str
    category: str
    title: str
    brand: str = ""
    model_number: str = ""
    jan: str = ""
    condition: str = "unknown"
    price_jpy: float
    shipping_jpy: float = 0
    weight_g: int = 0


class SourceItemRead(SourceItemCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketItemCreate(BaseModel):
    marketplace: str = "ebay"
    market_item_id: str
    category: str
    title: str
    brand: str = ""
    model_number: str = ""
    gtin: str = ""
    condition: str = "unknown"
    price_usd: float
    shipping_usd: float = 0
    price_confidence: str = Field(default="semi_trusted")


class MarketItemRead(MarketItemCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PipelineRunRequest(BaseModel):
    source_item_id: int
    category: str | None = None
    only_small_items: bool = True
    thresholds: "DecisionThresholdOverrides | None" = None


class DecisionThresholdOverrides(BaseModel):
    min_auto_accept_score: float | None = Field(default=None, ge=0.0, le=1.0)
    min_human_review_score: float | None = Field(default=None, ge=0.0, le=1.0)
    min_title_similarity_auto_accept: float | None = Field(default=None, ge=0.0, le=1.0)
    min_title_similarity_human_review: float | None = Field(default=None, ge=0.0, le=1.0)
    min_expected_profit_jpy: float | None = Field(default=None, ge=-1000000.0, le=100000000.0)
    min_expected_margin_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    accessory_reject_score: float | None = Field(default=None, ge=0.0, le=1.0)


class OpportunityRead(BaseModel):
    id: int
    source_item_id: int
    market_item_id: int
    match_score: float
    accessory_score: float
    decision: str
    decision_trace: str
    expected_profit_jpy: float
    expected_margin_rate: float
    storage_score: float
    shipping_score: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PipelineRunResponse(BaseModel):
    source_item_id: int
    created_opportunities: int
    auto_accept_count: int
    human_review_count: int
    reject_count: int
    opportunities: list[OpportunityRead]


class LiveTrialRequest(BaseModel):
    source_site: Literal["yahoo", "rakuten"]
    market_source: Literal["ebay", "mock"] = "ebay"
    query: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=1, max_length=120)
    item_condition: Literal["any", "new", "used"] = "any"
    thresholds: DecisionThresholdOverrides | None = None
    source_limit: int = Field(default=5, ge=1, le=1000)
    market_limit: int = Field(default=40, ge=1, le=1000)
    run_pipeline_top_n: int = Field(default=3, ge=1, le=1000)
    scan_cooldown_minutes: int = Field(default=60, ge=1, le=1440)
    only_small_items: bool | None = None


class TrialScanStateResetRequest(BaseModel):
    source_site: Literal["yahoo", "rakuten"]
    market_source: Literal["ebay", "mock"] = "ebay"
    query: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=1, max_length=120)
    item_condition: Literal["any", "new", "used"] = "any"


class SourcePipelineSummary(BaseModel):
    source_item_id: int
    created_opportunities: int
    auto_accept_count: int
    human_review_count: int
    reject_count: int


class ReasonCountItem(BaseModel):
    reason: str
    count: int


class LiveTrialResponse(BaseModel):
    query: str
    category: str
    source_site: str
    market_source: str
    imported_source_items: int
    imported_market_items: int
    processed_source_items: int
    skipped_recent_source_items: int
    source_cursor: int
    market_cursor: int
    scan_cooldown_minutes: int
    run_total_rejects: int
    run_total_compliance_flagged: int
    run_reject_reasons: list[ReasonCountItem]
    run_compliance_reasons: list[ReasonCountItem]
    source_runs: list[SourcePipelineSummary]


class TrialScanStateResetResponse(BaseModel):
    source_site: str
    market_source: str
    query: str
    category: str
    source_cursor: int
    market_cursor: int


class ScanSummaryResponse(BaseModel):
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
    pair_total: int
    reject_reasons: list[ReasonCountItem]
    compliance_reasons: list[ReasonCountItem]
    last_run_at: datetime | None


class ApiUsageItemResponse(BaseModel):
    provider: str
    calls_last_hour: int
    hourly_budget: int | None
    usage_rate_percent: float | None
    remaining_calls: int | None
    usage_basis: str
    limit_window: str
    note: str


class ApiUsageResponse(BaseModel):
    window_minutes: int
    items: list[ApiUsageItemResponse]


class FxRateStatusResponse(BaseModel):
    pair: str
    rate: float
    source: str
    fetched_at: datetime | None
    next_refresh_at: datetime | None
    last_error: str
    auto_update_enabled: bool


class ThresholdSettingsResponse(BaseModel):
    category: str | None
    min_auto_accept_score: float
    min_human_review_score: float
    min_title_similarity_auto_accept: float
    min_title_similarity_human_review: float
    min_expected_profit_jpy: float
    min_expected_margin_rate: float
    accessory_reject_score: float


class CategorySuggestionItemResponse(BaseModel):
    key: str
    internal_category: str
    label_ja: str
    source_hint: str
    market_hint: str
    aliases: list[str]
    score: float


class CategorySuggestionResponse(BaseModel):
    total: int
    items: list[CategorySuggestionItemResponse]


class RejectReasonItem(BaseModel):
    reason: str
    count: int


class RejectReasonSummaryResponse(BaseModel):
    total_rejects: int
    reasons: list[RejectReasonItem]


class ComplianceReasonSummaryResponse(BaseModel):
    total_flagged: int
    reasons: list[RejectReasonItem]


class ReviewQueueItem(BaseModel):
    opportunity_id: int
    source_title: str
    market_title: str
    source_site: str
    source_item_external_id: str
    source_category: str
    source_condition: str
    source_price_jpy: float
    source_shipping_jpy: float
    market_site: str
    market_item_external_id: str
    market_category: str
    market_condition: str
    market_price_usd: float
    market_shipping_usd: float
    market_revenue_jpy: float
    source_link: str
    market_link: str
    match_score: float
    accessory_score: float
    expected_profit_jpy: float
    expected_margin_rate: float
    decision_trace: str
    created_at: datetime


class ReviewDecisionRequest(BaseModel):
    outcome: Literal["approve", "reject"]
    reviewer: str = "manual"
    note: str = ""


class ReviewDecisionRead(BaseModel):
    id: int
    opportunity_id: int
    reviewer: str
    outcome: str
    note: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchJobCreate(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    enabled: bool = True
    source_site: Literal["yahoo", "rakuten"]
    market_source: Literal["ebay", "mock"] = "ebay"
    query: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=1, max_length=120)
    source_limit: int = Field(default=5, ge=1, le=1000)
    market_limit: int = Field(default=40, ge=1, le=1000)
    run_pipeline_top_n: int = Field(default=3, ge=1, le=1000)
    only_small_items: bool = True
    interval_minutes: int = Field(default=1440, ge=5, le=10080)


class BatchJobRead(BatchJobCreate):
    id: int
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchRunRead(BaseModel):
    id: int
    job_id: int
    status: str
    message: str
    summary_json: str
    started_at: datetime
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
