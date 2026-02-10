from fastapi.testclient import TestClient

from app.main import app


def test_pipeline_minimum_usable() -> None:
    with TestClient(app) as client:
        source_payload = {
            "source_site": "yahoo-shopping",
            "source_item_id": "ys-test-1",
            "category": "audio",
            "title": "Sony ABC-100 Bluetooth Speaker New",
            "brand": "Sony",
            "model_number": "ABC-100",
            "jan": "4900000000001",
            "condition": "new",
            "price_jpy": 8800,
            "shipping_jpy": 600,
            "weight_g": 460,
        }
        res = client.post("/v1/source-items", json=source_payload)
        assert res.status_code == 200
        source_item_id = res.json()["id"]

        good_market_payload = {
            "marketplace": "ebay",
            "market_item_id": "eb-test-good-1",
            "category": "audio",
            "title": "Sony ABC-100 Bluetooth Speaker New in Box",
            "brand": "Sony",
            "model_number": "ABC-100",
            "gtin": "4900000000001",
            "condition": "new",
            "price_usd": 189,
            "shipping_usd": 18,
            "price_confidence": "trusted",
        }
        res = client.post("/v1/market-items", json=good_market_payload)
        assert res.status_code == 200

        bad_market_payload = {
            "marketplace": "ebay",
            "market_item_id": "eb-test-bad-1",
            "category": "audio",
            "title": "Speaker Case Cover for Sony ABC-100",
            "brand": "",
            "model_number": "",
            "gtin": "",
            "condition": "new",
            "price_usd": 11,
            "shipping_usd": 4,
            "price_confidence": "semi_trusted",
        }
        res = client.post("/v1/market-items", json=bad_market_payload)
        assert res.status_code == 200

        run_res = client.post(
            "/v1/pipeline/run",
            json={"source_item_id": source_item_id, "only_small_items": True},
        )
        assert run_res.status_code == 200
        data = run_res.json()
        assert data["created_opportunities"] == 2
        assert data["auto_accept_count"] == 1
        assert data["reject_count"] == 1

        list_res = client.get("/v1/opportunities")
        assert list_res.status_code == 200
        opportunities = list_res.json()
        assert len(opportunities) >= 2
