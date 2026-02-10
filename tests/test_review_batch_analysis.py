from fastapi.testclient import TestClient

from app.adapters.mock import MockMarketAdapter, MockSourceAdapter
from app.main import app
from app.services import batch as batch_service


def test_reject_reason_summary_endpoint() -> None:
    with TestClient(app) as client:
        source = client.post(
            "/v1/source-items",
            json={
                "source_site": "test",
                "source_item_id": "src-reject-1",
                "category": "audio",
                "title": "Sony ABC-100 Speaker",
                "brand": "Sony",
                "model_number": "ABC-100",
                "jan": "",
                "condition": "new",
                "price_jpy": 9000,
                "shipping_jpy": 0,
                "weight_g": 400,
            },
        )
        source_id = source.json()["id"]

        client.post(
            "/v1/market-items",
            json={
                "marketplace": "ebay",
                "market_item_id": "mkt-reject-1",
                "category": "audio",
                "title": "Case Cover for Sony ABC-100",
                "brand": "",
                "model_number": "",
                "gtin": "",
                "condition": "new",
                "price_usd": 12,
                "shipping_usd": 4,
                "price_confidence": "semi_trusted",
            },
        )

        client.post("/v1/pipeline/run", json={"source_item_id": source_id, "only_small_items": True})

        summary = client.get("/v1/analysis/reject-reasons?limit=100")
        assert summary.status_code == 200
        data = summary.json()
        assert data["total_rejects"] >= 1
        assert len(data["reasons"]) >= 1


def test_review_queue_and_decision() -> None:
    with TestClient(app) as client:
        source = client.post(
            "/v1/source-items",
            json={
                "source_site": "test",
                "source_item_id": "src-review-1",
                "category": "audio",
                "title": "Sony ABC-100 Wireless Speaker",
                "brand": "Sony",
                "model_number": "ABC-100",
                "jan": "",
                "condition": "new",
                "price_jpy": 3000,
                "shipping_jpy": 0,
                "weight_g": 400,
            },
        )
        source_id = source.json()["id"]

        client.post(
            "/v1/market-items",
            json={
                "marketplace": "ebay",
                "market_item_id": "mkt-review-1",
                "category": "audio",
                "title": "ABC-100 Model XZ2024 Genuine",
                "brand": "Sony",
                "model_number": "ABC-100",
                "gtin": "",
                "condition": "new",
                "price_usd": 75,
                "shipping_usd": 10,
                "price_confidence": "semi_trusted",
            },
        )

        run = client.post("/v1/pipeline/run", json={"source_item_id": source_id, "only_small_items": True})
        assert run.status_code == 200

        queue = client.get("/v1/review/queue?limit=20")
        assert queue.status_code == 200
        items = queue.json()
        assert len(items) >= 1
        assert "source_link" in items[0]
        assert "market_link" in items[0]
        assert "source_item_external_id" in items[0]
        assert "market_item_external_id" in items[0]
        opp_id = items[0]["opportunity_id"]

        decision = client.post(
            f"/v1/review/{opp_id}",
            json={"outcome": "approve", "reviewer": "test", "note": "looks same"},
        )
        assert decision.status_code == 200

        queue_after = client.get("/v1/review/queue?limit=20")
        assert queue_after.status_code == 200
        assert all(item["opportunity_id"] != opp_id for item in queue_after.json())


def test_batch_job_create_and_run_with_mock_adapters(monkeypatch) -> None:
    monkeypatch.setattr(batch_service, "YahooShoppingAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(batch_service, "RakutenIchibaAdapter", lambda: MockSourceAdapter())
    monkeypatch.setattr(batch_service, "EbayBrowseAdapter", lambda: MockMarketAdapter())

    with TestClient(app) as client:
        create = client.post(
            "/v1/batch/jobs",
            json={
                "name": "daily-audio-test",
                "enabled": True,
                "source_site": "yahoo",
                "market_source": "ebay",
                "query": "sony speaker",
                "category": "audio",
                "source_limit": 1,
                "market_limit": 2,
                "run_pipeline_top_n": 1,
                "only_small_items": True,
                "interval_minutes": 60,
            },
        )
        assert create.status_code == 200
        job_id = create.json()["id"]

        run = client.post(f"/v1/batch/jobs/{job_id}/run")
        assert run.status_code == 200
        assert run.json()["status"] in {"success", "failed"}

        runs = client.get(f"/v1/batch/runs?job_id={job_id}&limit=10")
        assert runs.status_code == 200
        assert len(runs.json()) >= 1


def test_review_queue_excludes_cursor_fixture_like_records_by_default() -> None:
    with TestClient(app) as client:
        source = client.post(
            "/v1/source-items",
            json={
                "source_site": "rakuten-ichiba",
                "source_item_id": "rakuten-ichiba:src-cursor-range-10",
                "category": "audio",
                "title": "Sony ABC-100 Wireless Speaker",
                "brand": "Sony",
                "model_number": "ABC-100",
                "jan": "",
                "condition": "new",
                "price_jpy": 3000,
                "shipping_jpy": 0,
                "weight_g": 400,
            },
        )
        source_id = source.json()["id"]

        client.post(
            "/v1/market-items",
            json={
                "marketplace": "ebay",
                "market_item_id": "ebay:mkt-cursor-0-10",
                "category": "audio",
                "title": "ABC-100 Model XZ2024 Genuine",
                "brand": "Sony",
                "model_number": "ABC-100",
                "gtin": "",
                "condition": "new",
                "price_usd": 75,
                "shipping_usd": 10,
                "price_confidence": "semi_trusted",
            },
        )

        run = client.post("/v1/pipeline/run", json={"source_item_id": source_id, "only_small_items": True})
        assert run.status_code == 200

        queue_default = client.get("/v1/review/queue?limit=20")
        assert queue_default.status_code == 200
        assert queue_default.json() == []

        queue_with_mock = client.get("/v1/review/queue?limit=20&include_mock=true")
        assert queue_with_mock.status_code == 200
        assert len(queue_with_mock.json()) >= 1
