from app.adapters.ebay import _normalize_offset


def test_normalize_offset_aligns_to_limit_multiple() -> None:
    assert _normalize_offset(cursor=40, limit=60) == 0
    assert _normalize_offset(cursor=100, limit=60) == 60


def test_normalize_offset_respects_max_window() -> None:
    assert _normalize_offset(cursor=10001, limit=60) == 9960
    assert _normalize_offset(cursor=9999, limit=200) == 9800
