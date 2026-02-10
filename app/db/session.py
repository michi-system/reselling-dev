from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def resolve_database_url(raw_url: str) -> str:
    if not raw_url.startswith("sqlite:///"):
        return raw_url
    if raw_url.startswith("sqlite:////"):
        return raw_url
    path_part = raw_url[len("sqlite:///") :]
    if path_part == ":memory:":
        return raw_url

    normalized = path_part[2:] if path_part.startswith("./") else path_part
    project_root = Path(__file__).resolve().parents[2]
    absolute_path = (project_root / normalized).resolve()
    return f"sqlite:///{absolute_path}"


database_url = resolve_database_url(settings.database_url)

connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_lightweight_schema_migrations()


def _apply_lightweight_schema_migrations() -> None:
    if not database_url.startswith("sqlite"):
        return

    with engine.begin() as conn:
        _ensure_sqlite_column(
            conn=conn,
            table="scan_summaries",
            column="total_source_items_imported",
            ddl="INTEGER DEFAULT 0",
        )
        _ensure_sqlite_column(
            conn=conn,
            table="scan_summaries",
            column="total_market_items_imported",
            ddl="INTEGER DEFAULT 0",
        )


def _ensure_sqlite_column(conn, table: str, column: str, ddl: str) -> None:
    rows = conn.exec_driver_sql(f"PRAGMA table_info('{table}')").fetchall()
    if not rows:
        return
    existing = {str(row[1]) for row in rows if len(row) > 1}
    if column in existing:
        return
    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
