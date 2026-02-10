from __future__ import annotations

from typing import Any

from app.adapters.yahoo import YahooShoppingAdapter


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any], text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeYahooClient:
    def __init__(self, pages: dict[int, list[dict[str, Any]]], calls: list[tuple[int, int]]) -> None:
        self.pages = pages
        self.calls = calls

    def __enter__(self) -> _FakeYahooClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str, params: dict[str, Any] | None = None) -> _FakeResponse:
        assert params is not None
        start = int(params.get("start", 1))
        results = int(params.get("results", 0))
        self.calls.append((start, results))
        return _FakeResponse(200, {"hits": self.pages.get(start, [])})


def _hit(idx: int) -> dict[str, Any]:
    return {
        "name": f"Item {idx}",
        "url": f"https://store.shopping.yahoo.co.jp/test-shop/item-{idx}.html",
        "code": f"test-shop:item-{idx}",
        "brand": {"name": "Sony"},
        "janCode": "",
        "price": 1000 + idx,
        "shipping": {"price": 0},
    }


def test_yahoo_fetch_tops_up_to_exact_limit_with_multi_page_and_dedup(monkeypatch) -> None:
    monkeypatch.setenv("YAHOO_CLIENT_ID", "test-app-id")
    monkeypatch.setenv("YAHOO_MIN_INTERVAL_SECONDS", "0")
    from app.core import config

    config.get_settings.cache_clear()
    calls: list[tuple[int, int]] = []
    pages = {
        1: [_hit(1), _hit(1), _hit(2), _hit(2), _hit(3)],
        6: [_hit(4), _hit(5), _hit(6), _hit(7), _hit(8)],
    }
    monkeypatch.setattr("app.adapters.yahoo.httpx.Client", lambda timeout: _FakeYahooClient(pages=pages, calls=calls))

    adapter = YahooShoppingAdapter()
    records = adapter.fetch(query="sony", category="audio", limit=5, cursor=0)

    assert len(records) == 5
    assert [r.external_id for r in records] == [
        "https://store.shopping.yahoo.co.jp/test-shop/item-1.html",
        "https://store.shopping.yahoo.co.jp/test-shop/item-2.html",
        "https://store.shopping.yahoo.co.jp/test-shop/item-3.html",
        "https://store.shopping.yahoo.co.jp/test-shop/item-4.html",
        "https://store.shopping.yahoo.co.jp/test-shop/item-5.html",
    ]
    assert calls == [(1, 5), (6, 5)]


def test_yahoo_fetch_honors_cursor_start_position(monkeypatch) -> None:
    monkeypatch.setenv("YAHOO_CLIENT_ID", "test-app-id")
    monkeypatch.setenv("YAHOO_MIN_INTERVAL_SECONDS", "0")
    from app.core import config

    config.get_settings.cache_clear()
    calls: list[tuple[int, int]] = []
    pages = {
        11: [_hit(11), _hit(12), _hit(13), _hit(14)],
    }
    monkeypatch.setattr("app.adapters.yahoo.httpx.Client", lambda timeout: _FakeYahooClient(pages=pages, calls=calls))

    adapter = YahooShoppingAdapter()
    records = adapter.fetch(query="sony", category="audio", limit=4, cursor=10)

    assert len(records) == 4
    assert records[0].external_id.endswith("/item-11.html")
    assert records[-1].external_id.endswith("/item-14.html")
    assert calls == [(11, 4)]

