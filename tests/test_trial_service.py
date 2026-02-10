from app.adapters.mock import MockMarketAdapter, MockSourceAdapter
from app.adapters.base import ListingRecord
from app.db.models import MarketItem
from app.db.models import ScanState
from app.db.session import SessionLocal
from app.services.trial import CURSOR_DONE, normalize_live_trial_limits, run_live_trial


def test_live_trial_pipeline_with_mock_adapters() -> None:
    db = SessionLocal()
    result = run_live_trial(
        db=db,
        source_adapter=MockSourceAdapter(),
        market_adapter=MockMarketAdapter(),
        source_site="mock-source",
        market_source="mock",
        query="Bluetooth Speaker",
        category="audio",
        source_limit=1,
        market_limit=2,
        run_pipeline_top_n=1,
        only_small_items=True,
    )

    assert result.imported_source_items == 1
    assert result.imported_market_items == 1
    assert result.processed_source_items == 1
    assert len(result.results) == 1

    run = result.results[0]
    assert run.created_opportunities == 1
    assert run.auto_accept_count == 0
    assert run.human_review_count == 1
    assert run.reject_count == 0
    db.close()


def test_normalize_live_trial_limits() -> None:
    source_limit, market_limit, top_n = normalize_live_trial_limits(
        source_site="rakuten",
        source_limit=999,
        market_limit=999,
        run_pipeline_top_n=999,
    )
    assert source_limit == 100
    assert market_limit == 100
    assert top_n == 100

    source_limit2, market_limit2, top_n2 = normalize_live_trial_limits(
        source_site="yahoo",
        source_limit=999,
        market_limit=0,
        run_pipeline_top_n=1,
    )
    assert source_limit2 == 100
    assert market_limit2 == 100
    assert top_n2 == 100


class RejectOnlySourceAdapter(MockSourceAdapter):
    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        return [
            ListingRecord(
                external_id="src-reject-1",
                site="yahoo-shopping",
                category=category,
                title=f"{query} Main Unit",
                brand="Sony",
                model_number="ABC-100",
                code="4900000000001",
                condition="new",
                price=9000.0,
                shipping=0.0,
                weight_g=300,
            )
        ]


class RejectOnlyMarketAdapter(MockMarketAdapter):
    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        return [
            ListingRecord(
                external_id="mkt-reject-1",
                site="ebay",
                category=category,
                title=f"{query} case cover only",
                brand="",
                model_number="",
                code="",
                condition="new",
                price=5.0,
                shipping=1.0,
                price_confidence="semi_trusted",
            )
        ]


def test_recent_reject_only_sources_are_skipped() -> None:
    db = SessionLocal()
    source_adapter = RejectOnlySourceAdapter()
    market_adapter = RejectOnlyMarketAdapter()

    first = run_live_trial(
        db=db,
        source_adapter=source_adapter,
        market_adapter=market_adapter,
        source_site="yahoo",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=1,
        market_limit=1,
        run_pipeline_top_n=1,
        scan_cooldown_minutes=60,
        only_small_items=True,
    )
    assert first.processed_source_items == 1
    assert first.skipped_recent_source_items == 0

    second = run_live_trial(
        db=db,
        source_adapter=source_adapter,
        market_adapter=market_adapter,
        source_site="yahoo",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=1,
        market_limit=1,
        run_pipeline_top_n=1,
        scan_cooldown_minutes=60,
        only_small_items=True,
    )
    assert second.processed_source_items == 0
    assert second.skipped_recent_source_items >= 1
    db.close()


class CursorCaptureSourceAdapter(MockSourceAdapter):
    def __init__(self) -> None:
        self.seen_cursors: list[int] = []

    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        self.seen_cursors.append(cursor)
        return [
            ListingRecord(
                external_id="src-cursor-1",
                site="yahoo-shopping",
                category=category,
                title=f"{query} Main Unit",
                brand="Sony",
                model_number="ABC-100",
                code="4900000000001",
                condition="new",
                price=9500.0,
                shipping=0.0,
                weight_g=200,
            )
        ]


class CursorCaptureRangeSourceAdapter(MockSourceAdapter):
    def __init__(self) -> None:
        self.seen_cursors: list[int] = []

    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        self.seen_cursors.append(cursor)
        records: list[ListingRecord] = []
        for i in range(limit):
            idx = cursor + i
            records.append(
                ListingRecord(
                    external_id=f"src-cursor-range-{idx}",
                    site="rakuten-ichiba",
                    category=category,
                    title=f"{query} Main Unit {idx}",
                    brand="Sony",
                    model_number=f"ABC-{idx}",
                    code=f"490000000{idx:04d}",
                    condition="new",
                    price=9500.0,
                    shipping=0.0,
                    weight_g=200,
                )
            )
        return records


class CursorCaptureMarketAdapter(MockMarketAdapter):
    def __init__(self) -> None:
        self.seen_cursors: list[int] = []

    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        self.seen_cursors.append(cursor)
        records: list[ListingRecord] = []
        for i in range(limit):
            records.append(
                ListingRecord(
                    external_id=f"mkt-cursor-{cursor}-{i}",
                    site="ebay",
                    category=category,
                    title=f"{query} Sony ABC-100 Listing {i}",
                    brand="Sony",
                    model_number="ABC-100",
                    code="4900000000001",
                    condition="new",
                    price=120.0,
                    shipping=5.0,
                    price_confidence="trusted",
                )
            )
        return records


def test_market_cursor_is_aligned_to_limit_boundary() -> None:
    db = SessionLocal()
    db.add(
        ScanState(
            source_site="yahoo",
            market_source="ebay",
            query="Sony Speaker",
            category="audio",
            source_cursor=0,
            market_cursor=40,
        )
    )
    db.commit()

    source_adapter = CursorCaptureSourceAdapter()
    market_adapter = CursorCaptureMarketAdapter()
    result = run_live_trial(
        db=db,
        source_adapter=source_adapter,
        market_adapter=market_adapter,
        source_site="yahoo",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=60,
        market_limit=60,
        run_pipeline_top_n=1,
        scan_cooldown_minutes=60,
        only_small_items=True,
    )

    assert market_adapter.seen_cursors == [0]
    assert result.market_cursor == 60
    db.close()


def test_legacy_rakuten_page_cursor_is_converted_to_count_cursor() -> None:
    db = SessionLocal()
    db.add(
        ScanState(
            source_site="rakuten",
            market_source="ebay",
            query="Sony Speaker",
            category="audio",
            source_cursor=3,
            market_cursor=0,
        )
    )
    db.commit()

    source_adapter = CursorCaptureSourceAdapter()
    market_adapter = CursorCaptureMarketAdapter()
    run_live_trial(
        db=db,
        source_adapter=source_adapter,
        market_adapter=market_adapter,
        source_site="rakuten",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=30,
        market_limit=60,
        run_pipeline_top_n=1,
        scan_cooldown_minutes=60,
        only_small_items=True,
    )

    assert source_adapter.seen_cursors == [90]
    db.close()


class DuplicateSourceAdapter(MockSourceAdapter):
    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        record = ListingRecord(
            external_id="src-dup-1",
            site="yahoo-shopping",
            category=category,
            title=f"{query} Main Unit",
            brand="Sony",
            model_number="ABC-100",
            code="4900000000001",
            condition="new",
            price=10000.0,
            shipping=0.0,
            weight_g=300,
        )
        return [record, record, record][: max(1, min(limit, 3))]


def test_duplicate_source_records_are_deduplicated_before_processing() -> None:
    db = SessionLocal()
    result = run_live_trial(
        db=db,
        source_adapter=DuplicateSourceAdapter(),
        market_adapter=MockMarketAdapter(),
        source_site="yahoo",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=3,
        market_limit=2,
        run_pipeline_top_n=3,
        scan_cooldown_minutes=60,
        only_small_items=True,
    )

    assert result.imported_source_items == 1
    assert result.processed_source_items == 1
    db.close()


class RangeSourceAdapter(MockSourceAdapter):
    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        records: list[ListingRecord] = []
        for i in range(limit):
            idx = cursor + i
            records.append(
                ListingRecord(
                    external_id=f"src-range-{idx}",
                    site="yahoo-shopping",
                    category=category,
                    title=f"{query} Unit {idx}",
                    brand="Sony",
                    model_number=f"ABC-{idx}",
                    code=f"490000000{idx:04d}",
                    condition="new",
                    price=9000.0 + idx,
                    shipping=0.0,
                    weight_g=300,
                )
            )
        return records


def test_source_cursor_advances_without_overlap_between_runs() -> None:
    db = SessionLocal()
    source_adapter = RangeSourceAdapter()
    market_adapter = MockMarketAdapter()

    first = run_live_trial(
        db=db,
        source_adapter=source_adapter,
        market_adapter=market_adapter,
        source_site="yahoo",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=3,
        market_limit=2,
        run_pipeline_top_n=1,
        scan_cooldown_minutes=1,
        only_small_items=True,
    )
    second = run_live_trial(
        db=db,
        source_adapter=source_adapter,
        market_adapter=market_adapter,
        source_site="yahoo",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=3,
        market_limit=2,
        run_pipeline_top_n=1,
        scan_cooldown_minutes=1,
        only_small_items=True,
    )

    assert first.source_cursor == 3
    assert second.source_cursor == 6
    db.close()


def test_rakuten_cursor_wraps_before_page_limit_error() -> None:
    db = SessionLocal()
    db.add(
        ScanState(
            source_site="rakuten",
            market_source="ebay",
            query="Sony Speaker",
            category="audio",
            source_cursor=2960,
            market_cursor=0,
        )
    )
    db.commit()

    source_adapter = CursorCaptureSourceAdapter()
    market_adapter = CursorCaptureMarketAdapter()
    result = run_live_trial(
        db=db,
        source_adapter=source_adapter,
        market_adapter=market_adapter,
        source_site="rakuten",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=10,
        market_limit=60,
        run_pipeline_top_n=1,
        scan_cooldown_minutes=60,
        only_small_items=True,
    )

    assert source_adapter.seen_cursors == [2960]
    assert result.source_cursor == CURSOR_DONE
    db.close()


def test_rakuten_cursor_with_limit_10_is_not_misconverted_to_300() -> None:
    db = SessionLocal()
    db.add(
        ScanState(
            source_site="rakuten",
            market_source="ebay",
            query="Sony Speaker",
            category="audio",
            source_cursor=10,
            market_cursor=0,
        )
    )
    db.commit()

    source_adapter = CursorCaptureRangeSourceAdapter()
    market_adapter = CursorCaptureMarketAdapter()
    result = run_live_trial(
        db=db,
        source_adapter=source_adapter,
        market_adapter=market_adapter,
        source_site="rakuten",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=10,
        market_limit=60,
        run_pipeline_top_n=1,
        scan_cooldown_minutes=60,
        only_small_items=True,
    )

    assert source_adapter.seen_cursors == [10]
    assert result.source_cursor == 20
    db.close()


def test_stops_fetching_when_both_source_and_market_are_complete() -> None:
    db = SessionLocal()
    db.add(
        ScanState(
            source_site="yahoo",
            market_source="ebay",
            query="Sony Speaker",
            category="audio",
            source_cursor=CURSOR_DONE,
            market_cursor=CURSOR_DONE,
        )
    )
    db.commit()

    source_adapter = CursorCaptureSourceAdapter()
    market_adapter = CursorCaptureMarketAdapter()
    result = run_live_trial(
        db=db,
        source_adapter=source_adapter,
        market_adapter=market_adapter,
        source_site="yahoo",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=10,
        market_limit=20,
        run_pipeline_top_n=3,
        scan_cooldown_minutes=60,
        only_small_items=True,
    )

    assert source_adapter.seen_cursors == []
    assert market_adapter.seen_cursors == []
    assert result.imported_source_items == 0
    assert result.imported_market_items == 0
    assert result.processed_source_items == 0
    assert result.source_cursor == CURSOR_DONE
    assert result.market_cursor == CURSOR_DONE
    db.close()


def test_stops_fetching_when_source_is_complete_even_if_market_not_complete() -> None:
    db = SessionLocal()
    db.add(
        ScanState(
            source_site="yahoo",
            market_source="ebay",
            query="Sony Speaker",
            category="audio",
            source_cursor=CURSOR_DONE,
            market_cursor=200,
        )
    )
    db.commit()

    source_adapter = CursorCaptureSourceAdapter()
    market_adapter = CursorCaptureMarketAdapter()
    result = run_live_trial(
        db=db,
        source_adapter=source_adapter,
        market_adapter=market_adapter,
        source_site="yahoo",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=10,
        market_limit=20,
        run_pipeline_top_n=10,
        scan_cooldown_minutes=60,
        only_small_items=True,
    )

    assert source_adapter.seen_cursors == []
    assert market_adapter.seen_cursors == []
    assert result.imported_source_items == 0
    assert result.imported_market_items == 0
    assert result.processed_source_items == 0
    assert result.source_cursor == CURSOR_DONE
    assert result.market_cursor == CURSOR_DONE
    db.close()


def test_ebay_cursor_becomes_done_after_reaching_max_offset_window() -> None:
    db = SessionLocal()
    db.add(
        ScanState(
            source_site="yahoo",
            market_source="ebay",
            query="Sony Speaker",
            category="audio",
            source_cursor=0,
            market_cursor=9960,
        )
    )
    db.commit()

    source_adapter = CursorCaptureSourceAdapter()
    market_adapter = CursorCaptureMarketAdapter()
    result = run_live_trial(
        db=db,
        source_adapter=source_adapter,
        market_adapter=market_adapter,
        source_site="yahoo",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=60,
        market_limit=60,
        run_pipeline_top_n=1,
        scan_cooldown_minutes=60,
        only_small_items=True,
    )

    assert market_adapter.seen_cursors == [9960]
    assert result.market_cursor == CURSOR_DONE
    db.close()


def test_live_trial_compares_only_markets_fetched_in_this_run() -> None:
    db = SessionLocal()
    # Existing historical market row in same category should not be included.
    db.add(
        MarketItem(
            marketplace="ebay",
            market_item_id="ebay:historical-1",
            category="audio",
            title="historical listing",
            brand="Sony",
            model_number="ABC-100",
            gtin="",
            condition="new",
            price_usd=99.0,
            shipping_usd=10.0,
            price_confidence="trusted",
        )
    )
    db.commit()

    result = run_live_trial(
        db=db,
        source_adapter=MockSourceAdapter(),  # returns 1 source
        market_adapter=MockMarketAdapter(),  # returns 2 markets
        source_site="yahoo",
        market_source="ebay",
        query="Sony Speaker",
        category="audio",
        source_limit=1,
        market_limit=2,
        run_pipeline_top_n=1,
        scan_cooldown_minutes=60,
        only_small_items=True,
    )

    assert result.imported_market_items == 1
    assert len(result.results) == 1
    # If historical row were included, created_opportunities would be >=2.
    assert result.results[0].created_opportunities == 1
    db.close()
