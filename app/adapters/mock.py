from app.adapters.base import ListingRecord, MarketAdapter, SourceAdapter


class MockSourceAdapter(SourceAdapter):
    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        return [
            ListingRecord(
                external_id="src-001",
                site="mock-source",
                category=category,
                title=f"{query} Main Unit",
                brand="Sony",
                model_number="ABC-100",
                code="4900000000001",
                condition="new",
                price=8500,
                shipping=500,
                weight_g=420,
            )
        ][:limit]


class MockMarketAdapter(MarketAdapter):
    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        return [
            ListingRecord(
                external_id="mkt-001",
                site="mock-ebay",
                category=category,
                title=f"{query} Sony ABC-100 Brand New",
                brand="Sony",
                model_number="ABC-100",
                code="4900000000001",
                condition="new",
                price=169.0,
                shipping=15.0,
                price_confidence="trusted",
            ),
            ListingRecord(
                external_id="mkt-002",
                site="mock-ebay",
                category=category,
                title=f"{query} case cover for ABC-100",
                brand="",
                model_number="",
                code="",
                condition="new",
                price=12.0,
                shipping=4.0,
                price_confidence="semi_trusted",
            ),
        ][:limit]
