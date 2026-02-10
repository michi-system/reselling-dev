from app.db.session import resolve_database_url


def test_resolve_database_url_normalizes_relative_sqlite_path() -> None:
    resolved = resolve_database_url("sqlite:///./app.db")
    assert resolved.startswith("sqlite:////")
    assert resolved.endswith("/app.db")


def test_resolve_database_url_keeps_absolute_sqlite_path() -> None:
    raw = "sqlite:////tmp/test.db"
    assert resolve_database_url(raw) == raw
