from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.ebay import EbayBrowseAdapter
from app.adapters.errors import ExternalApiError
from app.adapters.mock import MockMarketAdapter
from app.adapters.rakuten import RakutenIchibaAdapter
from app.adapters.yahoo import YahooShoppingAdapter
from app.db.models import BatchJob, BatchRun
from app.services.trial import run_live_trial


def create_batch_job(db: Session, **kwargs) -> BatchJob:
    now = datetime.now(UTC)
    interval_minutes = int(kwargs.get("interval_minutes", 1440))

    job = BatchJob(
        name=kwargs["name"],
        enabled=1 if kwargs.get("enabled", True) else 0,
        source_site=kwargs["source_site"],
        market_source=kwargs.get("market_source", "ebay"),
        query=kwargs["query"],
        category=kwargs["category"],
        source_limit=int(kwargs.get("source_limit", 5)),
        market_limit=int(kwargs.get("market_limit", 40)),
        run_pipeline_top_n=int(kwargs.get("run_pipeline_top_n", 3)),
        only_small_items=1 if kwargs.get("only_small_items", True) else 0,
        interval_minutes=interval_minutes,
        last_run_at=None,
        next_run_at=now + timedelta(minutes=interval_minutes),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_batch_job(db: Session, job: BatchJob) -> BatchRun:
    started = datetime.now(UTC)
    run = BatchRun(job_id=job.id, status="running", message="", summary_json="{}", started_at=started)
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        source_adapter = YahooShoppingAdapter() if job.source_site == "yahoo" else RakutenIchibaAdapter()
        market_adapter = EbayBrowseAdapter() if job.market_source == "ebay" else MockMarketAdapter()

        result = run_live_trial(
            db=db,
            source_adapter=source_adapter,
            market_adapter=market_adapter,
            source_site=job.source_site,
            market_source=job.market_source,
            query=job.query,
            category=job.category,
            source_limit=job.source_limit,
            market_limit=job.market_limit,
            run_pipeline_top_n=job.run_pipeline_top_n,
            only_small_items=bool(job.only_small_items),
        )

        run.status = "success"
        run.summary_json = json.dumps(
            {
                "source_site": result.source_site,
                "query": result.query,
                "category": result.category,
                "imported_source_items": result.imported_source_items,
                "imported_market_items": result.imported_market_items,
                "processed_source_items": result.processed_source_items,
            },
            ensure_ascii=False,
        )
        run.message = "ok"
    except ExternalApiError as exc:
        run.status = "failed"
        run.message = str(exc)
        run.summary_json = json.dumps({"error": str(exc)}, ensure_ascii=False)
    finally:
        now = datetime.now(UTC)
        run.finished_at = now
        job.last_run_at = now
        job.next_run_at = now + timedelta(minutes=job.interval_minutes)
        db.commit()
        db.refresh(run)

    return run


def list_due_jobs(db: Session, now: datetime | None = None) -> list[BatchJob]:
    current = now or datetime.now(UTC)
    stmt = (
        select(BatchJob)
        .where(BatchJob.enabled == 1)
        .where(BatchJob.next_run_at.is_not(None))
        .where(BatchJob.next_run_at <= current)
        .order_by(BatchJob.next_run_at.asc())
    )
    return list(db.scalars(stmt))
