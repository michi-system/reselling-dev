import json

from app.db.models import MarketItem, SourceItem
from app.db.session import SessionLocal
from app.services.pipeline import run_pipeline


def _create_source(db, condition: str) -> SourceItem:
    source = SourceItem(
        source_site="yahoo-shopping",
        source_item_id=f"src-{condition}",
        category="audio",
        title=f"Sony WF-1000XM5 {condition}",
        brand="Sony",
        model_number="WF-1000XM5",
        jan="4548736143470",
        condition=condition,
        price_jpy=12000,
        shipping_jpy=0,
        weight_g=300,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def _create_market(db, condition: str, suffix: str = "") -> MarketItem:
    market = MarketItem(
        marketplace="ebay",
        market_item_id=f"mkt-{condition}{suffix}",
        category="audio",
        title=f"Sony WF-1000XM5 {condition} in box",
        brand="Sony",
        model_number="WF-1000XM5",
        gtin="4548736143470",
        condition=condition,
        price_usd=220,
        shipping_usd=10,
        price_confidence="trusted",
    )
    db.add(market)
    db.commit()
    db.refresh(market)
    return market


def test_condition_pair_mismatch_is_rejected() -> None:
    db = SessionLocal()
    source = _create_source(db, "new")
    _create_market(db, "used")

    opportunities = run_pipeline(
        db=db,
        source_item=source,
        category="audio",
        only_small_items=False,
        listing_condition_filter="any",
    )

    assert len(opportunities) == 1
    assert opportunities[0].decision == "reject"
    trace = json.loads(opportunities[0].decision_trace)
    assert trace["reject_reason"] == "condition_pair_mismatch"
    db.close()


def test_requested_condition_blocks_non_matching_source() -> None:
    db = SessionLocal()
    source = _create_source(db, "used")
    _create_market(db, "used", "-2")

    opportunities = run_pipeline(
        db=db,
        source_item=source,
        category="audio",
        only_small_items=False,
        listing_condition_filter="new",
    )

    assert len(opportunities) == 1
    assert opportunities[0].decision == "reject"
    trace = json.loads(opportunities[0].decision_trace)
    assert trace["reject_reason"] == "source_condition_filter_mismatch"
    db.close()


def test_requested_condition_allows_matching_pair() -> None:
    db = SessionLocal()
    source = _create_source(db, "used")
    _create_market(db, "used", "-3")

    opportunities = run_pipeline(
        db=db,
        source_item=source,
        category="audio",
        only_small_items=False,
        listing_condition_filter="used",
    )

    assert len(opportunities) == 1
    assert opportunities[0].decision in {"human_review", "auto_accept"}
    db.close()
