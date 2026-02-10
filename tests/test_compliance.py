from fastapi.testclient import TestClient

from app.core import config
from app.main import app


def test_strict_mode_blocks_auto_accept(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_MODE", "strict")
    monkeypatch.setenv("BLOCK_AUTO_ACCEPT_CROSS_MARKET", "true")
    config.get_settings.cache_clear()

    try:
        with TestClient(app) as client:
            source = client.post(
                "/v1/source-items",
                json={
                    "source_site": "yahoo-shopping",
                    "source_item_id": "src-compliance-1",
                    "category": "audio",
                    "title": "Sony ABC-100 Bluetooth Speaker New",
                    "brand": "Sony",
                    "model_number": "ABC-100",
                    "jan": "4900000000001",
                    "condition": "new",
                    "price_jpy": 8000,
                    "shipping_jpy": 500,
                    "weight_g": 400,
                },
            )
            source_id = source.json()["id"]

            client.post(
                "/v1/market-items",
                json={
                    "marketplace": "ebay",
                    "market_item_id": "mkt-compliance-1",
                    "category": "audio",
                    "title": "Sony ABC-100 Bluetooth Speaker New in Box",
                    "brand": "Sony",
                    "model_number": "ABC-100",
                    "gtin": "4900000000001",
                    "condition": "new",
                    "price_usd": 189,
                    "shipping_usd": 18,
                    "price_confidence": "trusted",
                },
            )

            run = client.post("/v1/pipeline/run", json={"source_item_id": source_id, "only_small_items": True})
            assert run.status_code == 200
            body = run.json()
            assert body["auto_accept_count"] == 0
            assert body["human_review_count"] == 1

            compliance_summary = client.get("/v1/analysis/compliance-risks?limit=100")
            assert compliance_summary.status_code == 200
            summary = compliance_summary.json()
            assert summary["total_flagged"] >= 1
            assert any(item["reason"] == "cross_market_to_ebay" for item in summary["reasons"])
    finally:
        config.get_settings.cache_clear()
