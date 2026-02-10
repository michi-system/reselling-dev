from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.adapters.mock import MockMarketAdapter, MockSourceAdapter
from app.api import routes
from app.db.models import MarketItem, Opportunity, ScanState, ScanSummary, SourceItem, SourceScanHistory
from app.db.session import SessionLocal
from app.main import app
from app.services.api_usage import record_api_call


def test_live_trial_route_with_mocked_adapters(monkeypatch) -> None:
    monkeypatch.setattr(routes, "YahooShoppingAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(routes, "RakutenIchibaAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(routes, "EbayBrowseAdapter", lambda: MockMarketAdapter())

    with TestClient(app) as client:
        response = client.post(
            "/v1/trial/live",
            json={
                "source_site": "yahoo",
                "query": "Bluetooth Speaker",
                "category": "audio",
                "source_limit": 1,
                "market_limit": 2,
                "run_pipeline_top_n": 1,
                "only_small_items": True,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["imported_source_items"] == 1
    assert body["imported_market_items"] == 1
    assert body["processed_source_items"] == 1
    assert body["market_source"] == "ebay"
    assert body["skipped_recent_source_items"] == 0
    assert body["scan_cooldown_minutes"] >= 1
    assert len(body["source_runs"]) == 1
    assert body["source_runs"][0]["auto_accept_count"] == 0
    assert body["source_runs"][0]["human_review_count"] == 1


def test_live_trial_route_applies_threshold_overrides(monkeypatch) -> None:
    monkeypatch.setattr(routes, "YahooShoppingAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(routes, "RakutenIchibaAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(routes, "EbayBrowseAdapter", lambda: MockMarketAdapter())

    with TestClient(app) as client:
        response = client.post(
            "/v1/trial/live",
            json={
                "source_site": "yahoo",
                "query": "Bluetooth Speaker",
                "category": "audio",
                "item_condition": "new",
                "source_limit": 1,
                "market_limit": 1,
                "run_pipeline_top_n": 1,
                "thresholds": {
                    "min_auto_accept_score": 1.0,
                    "min_human_review_score": 1.0,
                    "min_expected_profit_jpy": 99999999,
                },
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body["source_runs"]) == 1
    assert body["source_runs"][0]["auto_accept_count"] == 0
    assert body["source_runs"][0]["human_review_count"] == 0
    assert body["source_runs"][0]["reject_count"] == 1


def test_threshold_settings_endpoint_returns_current_values() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/system/thresholds?category=audio")
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "audio"
    assert 0 <= body["min_auto_accept_score"] <= 1
    assert 0 <= body["min_human_review_score"] <= 1
    assert 0 <= body["min_expected_margin_rate"] <= 1


def test_live_trial_route_accepts_large_source_limit_by_normalizing(monkeypatch) -> None:
    monkeypatch.setattr(routes, "YahooShoppingAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(routes, "RakutenIchibaAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(routes, "EbayBrowseAdapter", lambda: MockMarketAdapter())

    with TestClient(app) as client:
        response = client.post(
            "/v1/trial/live",
            json={
                "source_site": "rakuten",
                "query": "Bluetooth Speaker",
                "category": "audio",
                "source_limit": 999,
                "market_limit": 999,
                "run_pipeline_top_n": 999,
                "only_small_items": True,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["imported_source_items"] >= 1


def test_api_usage_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(routes, "YahooShoppingAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(routes, "RakutenIchibaAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(routes, "EbayBrowseAdapter", lambda: MockMarketAdapter())

    with TestClient(app) as client:
        run = client.post(
            "/v1/trial/live",
            json={
                "source_site": "yahoo",
                "query": "Bluetooth Speaker",
                "category": "audio",
                "source_limit": 1,
                "market_limit": 2,
                "run_pipeline_top_n": 1,
                "scan_cooldown_minutes": 60,
                "only_small_items": True,
            },
        )
        assert run.status_code == 200

        usage = client.get("/v1/analysis/api-usage")
        assert usage.status_code == 200
        body = usage.json()
        assert body["window_minutes"] == 60
        assert len(body["items"]) == 3


def test_api_usage_endpoint_reflects_persisted_events() -> None:
    record_api_call("yahoo")
    record_api_call("yahoo")
    record_api_call("ebay")

    with TestClient(app) as client:
        usage = client.get("/v1/analysis/api-usage")
        assert usage.status_code == 200
        body = usage.json()

    by_provider = {item["provider"]: item for item in body["items"]}
    assert by_provider["yahoo"]["calls_last_hour"] == 2
    assert by_provider["ebay"]["calls_last_hour"] == 1


def test_trial_summary_accumulates_pair_counts_for_same_condition(monkeypatch) -> None:
    monkeypatch.setattr(routes, "YahooShoppingAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(routes, "RakutenIchibaAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(routes, "EbayBrowseAdapter", lambda: MockMarketAdapter())

    with TestClient(app) as client:
        payload = {
            "source_site": "yahoo",
            "market_source": "ebay",
            "query": "Bluetooth Speaker",
            "category": "audio",
            "source_limit": 1,
            "market_limit": 1,
            "run_pipeline_top_n": 1,
            "only_small_items": True,
        }
        first = client.post("/v1/trial/live", json=payload)
        assert first.status_code == 200
        second = client.post("/v1/trial/live", json=payload)
        assert second.status_code == 200

        summary = client.get(
            "/v1/trial/summary",
            params={
                "source_site": "yahoo",
                "market_source": "ebay",
                "query": "Bluetooth Speaker",
                "category": "audio",
            },
        )
        assert summary.status_code == 200
        data = summary.json()
        assert data["total_runs"] == 2
        assert data["total_source_items_imported"] == 2
        assert data["total_market_items_imported"] == 2
        assert data["total_source_items_processed"] == 2
        assert data["pair_total"] == 2
        assert data["pair_human_review_total"] == 2
        assert data["pair_auto_accept_total"] == 0
        assert data["pair_reject_total"] == 0


def test_trial_summary_isolated_by_item_condition(monkeypatch) -> None:
    monkeypatch.setattr(routes, "YahooShoppingAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(routes, "RakutenIchibaAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(routes, "EbayBrowseAdapter", lambda: MockMarketAdapter())

    with TestClient(app) as client:
        payload = {
            "source_site": "yahoo",
            "market_source": "ebay",
            "query": "Bluetooth Speaker",
            "category": "audio",
            "item_condition": "new",
            "source_limit": 1,
            "market_limit": 1,
            "run_pipeline_top_n": 1,
        }
        run = client.post("/v1/trial/live", json=payload)
        assert run.status_code == 200

        summary_new = client.get(
            "/v1/trial/summary",
            params={
                "source_site": "yahoo",
                "market_source": "ebay",
                "query": "Bluetooth Speaker",
                "category": "audio",
                "item_condition": "new",
            },
        )
        assert summary_new.status_code == 200
        assert summary_new.json()["total_runs"] == 1

        summary_used = client.get(
            "/v1/trial/summary",
            params={
                "source_site": "yahoo",
                "market_source": "ebay",
                "query": "Bluetooth Speaker",
                "category": "audio",
                "item_condition": "used",
            },
        )
        assert summary_used.status_code == 200
        assert summary_used.json()["total_runs"] == 0


def test_trial_summary_resets_after_day_boundary(monkeypatch) -> None:
    monkeypatch.setenv("SCAN_SUMMARY_RESET_TIMEZONE", "Asia/Tokyo")
    from app.core import config

    config.get_settings.cache_clear()
    db = SessionLocal()
    db.add(
        ScanSummary(
            source_site="yahoo",
            market_source="ebay",
            query="Sony Speaker",
            category="audio",
            total_runs=3,
            total_source_items_processed=50,
            pair_auto_accept_total=2,
            pair_human_review_total=3,
            pair_reject_total=45,
            pair_reject_reasons_json='{"profit_below_threshold": 45}',
            pair_compliance_reasons_json='{"cross_market_to_ebay": 50}',
            last_run_at=datetime.now(UTC) - timedelta(days=1, minutes=1),
        )
    )
    db.commit()
    db.close()

    with TestClient(app) as client:
        summary = client.get(
            "/v1/trial/summary",
            params={
                "source_site": "yahoo",
                "market_source": "ebay",
                "query": "Sony Speaker",
                "category": "audio",
            },
        )

    assert summary.status_code == 200
    data = summary.json()
    assert data["total_runs"] == 0
    assert data["total_source_items_imported"] == 0
    assert data["total_market_items_imported"] == 0
    assert data["total_source_items_processed"] == 0
    assert data["pair_total"] == 0
    assert data["pair_auto_accept_total"] == 0
    assert data["pair_human_review_total"] == 0
    assert data["pair_reject_total"] == 0
    assert data["reject_reasons"] == []


def test_trial_summary_repairs_missing_import_totals_from_history() -> None:
    now = datetime.now(UTC)
    db = SessionLocal()
    src1 = SourceItem(
        source_site="yahoo",
        source_item_id="y-src-1",
        category="audio",
        title="item-1",
        price_jpy=1000,
    )
    src2 = SourceItem(
        source_site="yahoo",
        source_item_id="y-src-2",
        category="audio",
        title="item-2",
        price_jpy=1200,
    )
    mk1 = MarketItem(marketplace="ebay", market_item_id="m-1", category="audio", title="m1", price_usd=10)
    mk2 = MarketItem(marketplace="ebay", market_item_id="m-2", category="audio", title="m2", price_usd=11)
    db.add_all([src1, src2, mk1, mk2])
    db.flush()
    db.add_all(
        [
            SourceScanHistory(
                source_item_id=src1.id,
                source_site="yahoo",
                query="WF-1000XM5",
                category="audio",
                scanned_at=now,
                reject_count=1,
            ),
            SourceScanHistory(
                source_item_id=src2.id,
                source_site="yahoo",
                query="WF-1000XM5",
                category="audio",
                scanned_at=now,
                reject_count=1,
            ),
            Opportunity(
                source_item_id=src1.id,
                market_item_id=mk1.id,
                match_score=0.5,
                accessory_score=0.8,
                decision="reject",
                decision_trace='{"reject_reason":"unknown"}',
                expected_profit_jpy=-100,
                expected_margin_rate=-0.1,
                storage_score=0.5,
                shipping_score=0.5,
            ),
            Opportunity(
                source_item_id=src2.id,
                market_item_id=mk2.id,
                match_score=0.6,
                accessory_score=0.8,
                decision="reject",
                decision_trace='{"reject_reason":"unknown"}',
                expected_profit_jpy=-50,
                expected_margin_rate=-0.05,
                storage_score=0.5,
                shipping_score=0.5,
            ),
            ScanSummary(
                source_site="yahoo",
                market_source="ebay",
                query="WF-1000XM5",
                category="audio",
                total_runs=3,
                total_source_items_imported=0,
                total_market_items_imported=0,
                total_source_items_processed=507,
                pair_auto_accept_total=0,
                pair_human_review_total=0,
                pair_reject_total=507,
                pair_reject_reasons_json='{"unknown": 507}',
                pair_compliance_reasons_json="{}",
                last_run_at=now,
            ),
        ]
    )
    db.commit()
    db.close()

    with TestClient(app) as client:
        summary = client.get(
            "/v1/trial/summary",
            params={
                "source_site": "yahoo",
                "market_source": "ebay",
                "query": "WF-1000XM5",
                "category": "audio",
            },
        )

    assert summary.status_code == 200
    data = summary.json()
    assert data["total_source_items_imported"] == 2
    assert data["total_market_items_imported"] == 2
    assert data["total_source_items_processed"] == 507


def test_trial_reset_state_route_sets_cursors_to_zero() -> None:
    db = SessionLocal()
    db.add(
        ScanState(
            source_site="yahoo",
            market_source="ebay",
            query="Sony Speaker",
            category="audio",
            source_cursor=-1,
            market_cursor=300,
        )
    )
    db.commit()
    db.close()

    with TestClient(app) as client:
        response = client.post(
            "/v1/trial/reset-state",
            json={
                "source_site": "yahoo",
                "market_source": "ebay",
                "query": "Sony Speaker",
                "category": "audio",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["source_cursor"] == 0
    assert data["market_cursor"] == 0
