import os
from pathlib import Path

import pytest

_TEST_DB_PATH = Path(__file__).resolve().parent / ".test_app.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"

from app.core import config
from app.db.models import BatchJob, BatchRun, FxRateState, MarketItem, Opportunity, ReviewDecision, ScanState, ScanSummary, SourceItem, SourceScanHistory
from app.db.session import SessionLocal, init_db
from app.services.api_usage import reset_api_usage_for_tests
from app.services.fx_rate import reset_fx_rate_cache_for_tests


@pytest.fixture(autouse=True)
def clean_db(monkeypatch) -> None:
    # Keep tests deterministic regardless of local .env settings.
    monkeypatch.setenv("COMPLIANCE_MODE", "warn")
    monkeypatch.setenv("BLOCK_AUTO_ACCEPT_CROSS_MARKET", "true")
    monkeypatch.setenv("AUTO_ACCEPT_REQUIRES_TRUSTED_PRICE", "true")
    monkeypatch.setenv("MIN_EXPECTED_MARGIN_RATE", "0.10")
    monkeypatch.setenv("CATEGORY_MIN_MARGIN_OVERRIDES", "")
    monkeypatch.setenv("MIN_EXPECTED_PROFIT_JPY", "0")
    monkeypatch.setenv("API_USAGE_USE_EBAY_RATE_API", "false")
    config.get_settings.cache_clear()

    init_db()
    db = SessionLocal()
    db.query(ReviewDecision).delete()
    db.query(SourceScanHistory).delete()
    db.query(ScanSummary).delete()
    db.query(ScanState).delete()
    db.query(BatchRun).delete()
    db.query(BatchJob).delete()
    db.query(Opportunity).delete()
    db.query(SourceItem).delete()
    db.query(MarketItem).delete()
    db.query(FxRateState).delete()
    db.commit()
    db.close()
    reset_api_usage_for_tests()
    reset_fx_rate_cache_for_tests()
    config.get_settings.cache_clear()
