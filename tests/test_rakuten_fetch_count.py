from __future__ import annotations

from typing import Any

import pytest

from app.adapters.errors import ExternalApiError
from app.adapters.rakuten import RakutenIchibaAdapter


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any],
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeRakutenClient:
    def __init__(self, calls: list[tuple[int, int]], total_items: int = 240) -> None:
        self.calls = calls
        self.total_items = total_items

    def __enter__(self) -> _FakeRakutenClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> _FakeResponse:
        assert params is not None
        page = int(params["page"])
        hits = int(params["hits"])
        self.calls.append((page, hits))

        start = (page - 1) * hits
        end = min(start + hits, self.total_items)
        items = []
        for i in range(start, end):
            items.append(
                {
                    "Item": {
                        "itemName": f"Item {i}",
                        "itemCode": f"CODE-{i}",
                        "itemPrice": 1000 + i,
                        "postageFlag": "0",
                    }
                }
            )
        return _FakeResponse(200, {"Items": items})


class _FakeRakutenRateLimitClient:
    def __init__(self) -> None:
        self.calls = 0

    def __enter__(self) -> _FakeRakutenRateLimitClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> _FakeResponse:
        self.calls += 1
        if self.calls == 1:
            return _FakeResponse(
                429,
                {},
                text='{ "statusCode": 429, "message": "Rate limit is exceeded. Try again in 1 seconds." }',
                headers={"Retry-After": "1"},
            )
        items = [{"Item": {"itemName": "Item 1", "itemCode": "CODE-1", "itemPrice": 1001, "postageFlag": "0"}}]
        return _FakeResponse(200, {"Items": items})


class _FakeRakutenAlways429Client:
    def __init__(self) -> None:
        self.calls = 0

    def __enter__(self) -> _FakeRakutenAlways429Client:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> _FakeResponse:
        self.calls += 1
        return _FakeResponse(
            429,
            {},
            text='{ "statusCode": 429, "message": "Rate limit is exceeded. Try again in 1 seconds." }',
            headers={"Retry-After": "1"},
        )


class _FakeRakutenDuplicateClient:
    def __init__(self, calls: list[tuple[int, int]]) -> None:
        self.calls = calls

    def __enter__(self) -> _FakeRakutenDuplicateClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> _FakeResponse:
        assert params is not None
        page = int(params["page"])
        hits = int(params["hits"])
        self.calls.append((page, hits))

        items: list[dict[str, Any]] = []
        if page == 1:
            for i in range(hits):
                dup_id = i // 2
                items.append(
                    {
                        "Item": {
                            "itemName": f"Item {dup_id}",
                            "itemCode": f"CODE-{dup_id}",
                            "itemPrice": 1000 + dup_id,
                            "postageFlag": "0",
                        }
                    }
                )
        else:
            for i in range(hits):
                idx = (page - 1) * hits + i
                items.append(
                    {
                        "Item": {
                            "itemName": f"Item {idx}",
                            "itemCode": f"CODE-{idx}",
                            "itemPrice": 1000 + idx,
                            "postageFlag": "0",
                        }
                    }
                )
        return _FakeResponse(200, {"Items": items})


def test_rakuten_fetch_returns_exact_limit_with_multi_page(monkeypatch) -> None:
    monkeypatch.setenv("RAKUTEN_APP_ID", "123456789012345678901")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "")
    monkeypatch.setenv("RAKUTEN_MIN_INTERVAL_SECONDS", "0")
    from app.core import config

    config.get_settings.cache_clear()
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "app.adapters.rakuten.httpx.Client",
        lambda timeout: _FakeRakutenClient(calls=calls, total_items=240),
    )

    adapter = RakutenIchibaAdapter()
    records = adapter.fetch(query="sony", category="audio", limit=100, cursor=0)

    assert len(records) == 100
    assert records[0].external_id == "CODE-0"
    assert records[-1].external_id == "CODE-99"
    assert calls == [(1, 30), (2, 30), (3, 30), (4, 30)]


def test_rakuten_fetch_honors_offset_cursor_exactly(monkeypatch) -> None:
    monkeypatch.setenv("RAKUTEN_APP_ID", "123456789012345678901")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "")
    monkeypatch.setenv("RAKUTEN_MIN_INTERVAL_SECONDS", "0")
    from app.core import config

    config.get_settings.cache_clear()
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "app.adapters.rakuten.httpx.Client",
        lambda timeout: _FakeRakutenClient(calls=calls, total_items=240),
    )

    adapter = RakutenIchibaAdapter()
    records = adapter.fetch(query="sony", category="audio", limit=40, cursor=35)

    assert len(records) == 40
    assert records[0].external_id == "CODE-35"
    assert records[-1].external_id == "CODE-74"
    assert calls == [(2, 30), (3, 30)]


def test_rakuten_fetch_tops_up_after_duplicate_items(monkeypatch) -> None:
    monkeypatch.setenv("RAKUTEN_APP_ID", "123456789012345678901")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "")
    monkeypatch.setenv("RAKUTEN_MIN_INTERVAL_SECONDS", "0")
    from app.core import config

    config.get_settings.cache_clear()
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "app.adapters.rakuten.httpx.Client",
        lambda timeout: _FakeRakutenDuplicateClient(calls=calls),
    )

    adapter = RakutenIchibaAdapter()
    records = adapter.fetch(query="sony", category="audio", limit=20, cursor=0)

    assert len(records) == 20
    assert len({r.external_id for r in records}) == 20
    assert calls == [(1, 30), (2, 30)]


def test_rakuten_fetch_caps_page_under_100(monkeypatch) -> None:
    monkeypatch.setenv("RAKUTEN_APP_ID", "123456789012345678901")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "")
    monkeypatch.setenv("RAKUTEN_MIN_INTERVAL_SECONDS", "0")
    from app.core import config

    config.get_settings.cache_clear()
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "app.adapters.rakuten.httpx.Client",
        lambda timeout: _FakeRakutenClient(calls=calls, total_items=4000),
    )

    adapter = RakutenIchibaAdapter()
    records = adapter.fetch(query="sony", category="audio", limit=10, cursor=5000)

    assert len(records) == 10
    assert calls[0][0] == 99
    assert all(page < 100 for page, _ in calls)


def test_rakuten_fetch_retries_once_after_429_and_succeeds(monkeypatch) -> None:
    monkeypatch.setenv("RAKUTEN_APP_ID", "123456789012345678901")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "")
    monkeypatch.setenv("RAKUTEN_MIN_INTERVAL_SECONDS", "0")
    from app.core import config

    config.get_settings.cache_clear()
    fake_client = _FakeRakutenRateLimitClient()
    monkeypatch.setattr("app.adapters.rakuten.httpx.Client", lambda timeout: fake_client)
    sleeps: list[float] = []
    monkeypatch.setattr("app.adapters.rakuten.time.sleep", lambda sec: sleeps.append(float(sec)))

    adapter = RakutenIchibaAdapter()
    records = adapter.fetch(query="sony", category="audio", limit=1, cursor=0)

    assert len(records) == 1
    assert fake_client.calls == 2
    assert sleeps == [1.0]


def test_rakuten_fetch_raises_after_retry_exhaustion(monkeypatch) -> None:
    monkeypatch.setenv("RAKUTEN_APP_ID", "123456789012345678901")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "")
    monkeypatch.setenv("RAKUTEN_MIN_INTERVAL_SECONDS", "0")
    from app.core import config

    config.get_settings.cache_clear()
    fake_client = _FakeRakutenAlways429Client()
    monkeypatch.setattr("app.adapters.rakuten.httpx.Client", lambda timeout: fake_client)
    monkeypatch.setattr("app.adapters.rakuten.time.sleep", lambda sec: None)

    adapter = RakutenIchibaAdapter()
    with pytest.raises(ExternalApiError) as exc:
        adapter.fetch(query="sony", category="audio", limit=1, cursor=0)
    assert "Rakuten API error: 429" in str(exc.value)
    assert fake_client.calls == 4
