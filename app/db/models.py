from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SourceItem(Base):
    __tablename__ = "source_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_site: Mapped[str] = mapped_column(String(32), index=True)
    source_item_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    brand: Mapped[str] = mapped_column(String(128), default="")
    model_number: Mapped[str] = mapped_column(String(128), default="")
    jan: Mapped[str] = mapped_column(String(32), default="")
    condition: Mapped[str] = mapped_column(String(32), default="unknown")
    price_jpy: Mapped[float] = mapped_column(Float)
    shipping_jpy: Mapped[float] = mapped_column(Float, default=0)
    weight_g: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="source_item")


class MarketItem(Base):
    __tablename__ = "market_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    marketplace: Mapped[str] = mapped_column(String(32), index=True)
    market_item_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    brand: Mapped[str] = mapped_column(String(128), default="")
    model_number: Mapped[str] = mapped_column(String(128), default="")
    gtin: Mapped[str] = mapped_column(String(32), default="")
    condition: Mapped[str] = mapped_column(String(32), default="unknown")
    price_usd: Mapped[float] = mapped_column(Float)
    shipping_usd: Mapped[float] = mapped_column(Float, default=0)
    price_confidence: Mapped[str] = mapped_column(String(16), default="semi_trusted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="market_item")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_item_id: Mapped[int] = mapped_column(ForeignKey("source_items.id"), index=True)
    market_item_id: Mapped[int] = mapped_column(ForeignKey("market_items.id"), index=True)

    match_score: Mapped[float] = mapped_column(Float)
    accessory_score: Mapped[float] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String(24), index=True)
    decision_trace: Mapped[str] = mapped_column(Text)
    rule_version: Mapped[str] = mapped_column(String(32), default="rules-v1")

    expected_profit_jpy: Mapped[float] = mapped_column(Float)
    expected_margin_rate: Mapped[float] = mapped_column(Float)
    storage_score: Mapped[float] = mapped_column(Float)
    shipping_score: Mapped[float] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    source_item: Mapped[SourceItem] = relationship(back_populates="opportunities")
    market_item: Mapped[MarketItem] = relationship(back_populates="opportunities")
    review_decisions: Mapped[list["ReviewDecision"]] = relationship(back_populates="opportunity")


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), unique=True, index=True)
    reviewer: Mapped[str] = mapped_column(String(128), default="manual")
    outcome: Mapped[str] = mapped_column(String(24), index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    opportunity: Mapped[Opportunity] = relationship(back_populates="review_decisions")


class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1, index=True)
    source_site: Mapped[str] = mapped_column(String(16), default="yahoo")
    market_source: Mapped[str] = mapped_column(String(16), default="ebay")
    query: Mapped[str] = mapped_column(String(128), index=True)
    category: Mapped[str] = mapped_column(String(128), index=True)
    source_limit: Mapped[int] = mapped_column(Integer, default=5)
    market_limit: Mapped[int] = mapped_column(Integer, default=40)
    run_pipeline_top_n: Mapped[int] = mapped_column(Integer, default=3)
    only_small_items: Mapped[int] = mapped_column(Integer, default=1)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    runs: Mapped[list["BatchRun"]] = relationship(back_populates="job")


class BatchRun(Base):
    __tablename__ = "batch_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("batch_jobs.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped[BatchJob] = relationship(back_populates="runs")


class ScanState(Base):
    __tablename__ = "scan_states"
    __table_args__ = (
        UniqueConstraint("source_site", "market_source", "query", "category", name="uq_scan_state_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_site: Mapped[str] = mapped_column(String(32), index=True)
    market_source: Mapped[str] = mapped_column(String(32), index=True)
    query: Mapped[str] = mapped_column(String(256), index=True)
    category: Mapped[str] = mapped_column(String(128), index=True)
    source_cursor: Mapped[int] = mapped_column(Integer, default=0)
    market_cursor: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ScanSummary(Base):
    __tablename__ = "scan_summaries"
    __table_args__ = (
        UniqueConstraint("source_site", "market_source", "query", "category", name="uq_scan_summary_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_site: Mapped[str] = mapped_column(String(32), index=True)
    market_source: Mapped[str] = mapped_column(String(32), index=True)
    query: Mapped[str] = mapped_column(String(256), index=True)
    category: Mapped[str] = mapped_column(String(128), index=True)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    total_source_items_imported: Mapped[int] = mapped_column(Integer, default=0)
    total_market_items_imported: Mapped[int] = mapped_column(Integer, default=0)
    total_source_items_processed: Mapped[int] = mapped_column(Integer, default=0)
    pair_auto_accept_total: Mapped[int] = mapped_column(Integer, default=0)
    pair_human_review_total: Mapped[int] = mapped_column(Integer, default=0)
    pair_reject_total: Mapped[int] = mapped_column(Integer, default=0)
    pair_reject_reasons_json: Mapped[str] = mapped_column(Text, default="{}")
    pair_compliance_reasons_json: Mapped[str] = mapped_column(Text, default="{}")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class SourceScanHistory(Base):
    __tablename__ = "source_scan_histories"
    __table_args__ = (
        UniqueConstraint("source_item_id", "source_site", "query", "category", name="uq_source_scan_history_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_item_id: Mapped[int] = mapped_column(ForeignKey("source_items.id"), index=True)
    source_site: Mapped[str] = mapped_column(String(32), index=True)
    query: Mapped[str] = mapped_column(String(256), index=True)
    category: Mapped[str] = mapped_column(String(128), index=True)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    auto_accept_count: Mapped[int] = mapped_column(Integer, default=0)
    human_review_count: Mapped[int] = mapped_column(Integer, default=0)
    reject_count: Mapped[int] = mapped_column(Integer, default=0)


class ApiUsageEvent(Base):
    __tablename__ = "api_usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    called_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)


class FxRateState(Base):
    __tablename__ = "fx_rate_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pair: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    rate: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(256), default="config")
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    next_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
