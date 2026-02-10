import os

import pytest

from app.adapters.errors import ExternalApiError
from app.adapters.rakuten import RakutenIchibaAdapter, _offset_to_page


def test_rakuten_app_id_access_key_misconfigured(monkeypatch) -> None:
    monkeypatch.setenv("RAKUTEN_APP_ID", "pk_abcdefghijklmnopqrstuvwxyz")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "")

    from app.core import config

    config.get_settings.cache_clear()
    try:
        with pytest.raises(ExternalApiError) as exc:
            RakutenIchibaAdapter()
        assert "looks like Access Key" in str(exc.value)
    finally:
        config.get_settings.cache_clear()
        os.environ.pop("RAKUTEN_APP_ID", None)
        os.environ.pop("RAKUTEN_ACCESS_KEY", None)


def test_offset_to_page_converts_count_cursor() -> None:
    assert _offset_to_page(cursor=0, limit=30) == 1
    assert _offset_to_page(cursor=30, limit=30) == 2
    assert _offset_to_page(cursor=89, limit=30) == 3
