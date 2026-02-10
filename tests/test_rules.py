from fastapi.testclient import TestClient

from app.core import config
from app.main import app
from app.services.rules import resolve_min_margin_rate


def test_category_margin_override_parser(monkeypatch) -> None:
    monkeypatch.setenv("MIN_EXPECTED_MARGIN_RATE", "0.10")
    monkeypatch.setenv("CATEGORY_MIN_MARGIN_OVERRIDES", "audio:0.12,camera:0.15,bad:abc")
    config.get_settings.cache_clear()

    try:
        settings = config.get_settings()
        assert resolve_min_margin_rate("audio", settings) == 0.12
        assert resolve_min_margin_rate("camera", settings) == 0.15
        assert resolve_min_margin_rate("other", settings) == 0.10
    finally:
        config.get_settings.cache_clear()


def test_pipeline_uses_category_margin_override(monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCE_MODE", "off")
    monkeypatch.setenv("MIN_EXPECTED_MARGIN_RATE", "0.20")
    monkeypatch.setenv("CATEGORY_MIN_MARGIN_OVERRIDES", "audio:0.05")
    monkeypatch.setenv("MIN_EXPECTED_PROFIT_JPY", "0")
    config.get_settings.cache_clear()

    try:
        with TestClient(app) as client:
            source = client.post(
                "/v1/source-items",
                json={
                    "source_site": "yahoo-shopping",
                    "source_item_id": "src-rules-1",
                    "category": "audio",
                    "title": "Sony ABC-100 Bluetooth Speaker New",
                    "brand": "Sony",
                    "model_number": "ABC-100",
                    "jan": "4900000000001",
                    "condition": "new",
                    "price_jpy": 12000,
                    "shipping_jpy": 0,
                    "weight_g": 300,
                },
            )
            source_id = source.json()["id"]

            client.post(
                "/v1/market-items",
                json={
                    "marketplace": "ebay",
                    "market_item_id": "mkt-rules-1",
                    "category": "audio",
                    "title": "Sony ABC-100 Bluetooth Speaker New in Box",
                    "brand": "Sony",
                    "model_number": "ABC-100",
                    "gtin": "4900000000001",
                    "condition": "new",
                    "price_usd": 120,
                    "shipping_usd": 10,
                    "price_confidence": "trusted",
                },
            )

            run = client.post("/v1/pipeline/run", json={"source_item_id": source_id, "only_small_items": True})
            assert run.status_code == 200
            body = run.json()
            assert body["auto_accept_count"] == 1
            trace = body["opportunities"][0]["decision_trace"]
            assert '"min_margin_rate": 0.05' in trace
    finally:
        config.get_settings.cache_clear()
