from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.db.models import FxRateState
from app.db.session import SessionLocal
from app.main import app
from app.services.fx_rate import get_current_usd_jpy_rate, maybe_refresh_usd_jpy_rate


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any], text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeFxClient:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.calls = 0

    def __enter__(self) -> _FakeFxClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str) -> _FakeResponse:
        self.calls += 1
        return _FakeResponse(self.status_code, self.payload, text="error")


def test_maybe_refresh_initializes_state_without_external_call(monkeypatch) -> None:
    monkeypatch.setenv("FX_USD_JPY", "151.25")
    monkeypatch.setenv("FX_UPDATE_INTERVAL_MINUTES", "60")
    from app.core import config

    config.get_settings.cache_clear()

    fake_client = _FakeFxClient(payload={"rates": {"JPY": 170.0}})
    monkeypatch.setattr("app.services.fx_rate.httpx.Client", lambda timeout: fake_client)

    db = SessionLocal()
    status = maybe_refresh_usd_jpy_rate(db)
    db.close()

    assert status.rate == 151.25
    assert status.fetched_at is None
    assert status.next_refresh_at is not None
    assert fake_client.calls == 0


def test_maybe_refresh_fetches_when_due(monkeypatch) -> None:
    monkeypatch.setenv("FX_USD_JPY", "150")
    monkeypatch.setenv("FX_RATE_PROVIDER_URL", "https://example.com/fx")
    monkeypatch.setenv("FX_UPDATE_INTERVAL_MINUTES", "60")
    from app.core import config

    config.get_settings.cache_clear()

    db = SessionLocal()
    db.add(
        FxRateState(
            pair="USDJPY",
            rate=150.0,
            source="config",
            fetched_at=None,
            next_refresh_at=datetime.now(UTC) - timedelta(minutes=1),
            last_error="",
        )
    )
    db.commit()

    fake_client = _FakeFxClient(payload={"rates": {"JPY": 147.8}})
    monkeypatch.setattr("app.services.fx_rate.httpx.Client", lambda timeout: fake_client)

    status = maybe_refresh_usd_jpy_rate(db)
    db.close()

    assert status.rate == 147.8
    assert status.source == "example.com"
    assert status.fetched_at is not None
    assert fake_client.calls == 1


def test_get_current_usd_jpy_rate_uses_latest_db_state() -> None:
    db = SessionLocal()
    db.add(
        FxRateState(
            pair="USDJPY",
            rate=149.1,
            source="db-test",
            fetched_at=datetime.now(UTC),
            next_refresh_at=datetime.now(UTC) + timedelta(minutes=60),
            last_error="",
        )
    )
    db.commit()
    db.close()

    assert get_current_usd_jpy_rate() == 149.1


def test_fx_rate_status_and_refresh_routes(monkeypatch) -> None:
    monkeypatch.setenv("FX_RATE_PROVIDER_URL", "https://fx.example.com/latest")
    from app.core import config

    config.get_settings.cache_clear()
    fake_client = _FakeFxClient(payload={"rates": {"JPY": 146.2}})
    monkeypatch.setattr("app.services.fx_rate.httpx.Client", lambda timeout: fake_client)

    with TestClient(app) as client:
        status = client.get("/v1/system/fx-rate")
        assert status.status_code == 200
        payload = status.json()
        assert payload["pair"] == "USDJPY"
        assert "rate" in payload

        refresh = client.post("/v1/system/fx-rate/refresh")
        assert refresh.status_code == 200
        refreshed = refresh.json()
        assert refreshed["rate"] == 146.2
        assert refreshed["source"] == "fx.example.com"

