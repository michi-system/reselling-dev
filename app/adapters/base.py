from dataclasses import dataclass


@dataclass
class ListingRecord:
    external_id: str
    site: str
    category: str
    title: str
    brand: str
    model_number: str
    code: str
    condition: str
    price: float
    shipping: float
    weight_g: int = 0
    price_confidence: str = "semi_trusted"


class SourceAdapter:
    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        raise NotImplementedError


class MarketAdapter:
    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        raise NotImplementedError
