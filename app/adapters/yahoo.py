from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.adapters.base import ListingRecord, SourceAdapter
from app.adapters.errors import ExternalApiError
from app.core.config import get_settings
from app.services.api_usage import record_api_call
from app.services.condition_infer import resolve_condition
from app.services.model_extract import extract_model_number
from app.services.rate_limit import wait_for_slot

YAHOO_ITEM_SEARCH_URL = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"


class YahooShoppingAdapter(SourceAdapter):
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.yahoo_client_id:
            raise ExternalApiError("YAHOO_CLIENT_ID is not set")

    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        requested_limit = max(1, min(int(limit), 100))
        page_size = requested_limit
        start = max(1, int(cursor) + 1) if cursor > 0 else 1
        max_pages = 20

        records: list[ListingRecord] = []
        seen_external_ids: set[str] = set()
        page_count = 0

        with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
            while len(records) < requested_limit and page_count < max_pages:
                wait_for_slot("yahoo_item_search", self.settings.yahoo_min_interval_seconds)
                record_api_call("yahoo")

                params = {
                    "appid": self.settings.yahoo_client_id,
                    "query": query,
                    "results": page_size,
                    "start": start,
                }
                response = client.get(YAHOO_ITEM_SEARCH_URL, params=params)
                if response.status_code >= 400:
                    raise ExternalApiError(f"Yahoo API error: {response.status_code} {response.text[:200]}")

                payload = response.json()
                hits = payload.get("hits", [])
                if not hits:
                    break

                for idx, hit in enumerate(hits):
                    title = _safe_str(hit.get("name"))
                    if not title:
                        continue

                    external_id = (
                        _normalize_public_url(_safe_str(hit.get("url")))
                        or _safe_str(hit.get("code"))
                        or f"yahoo-{start}-{idx}-{hash(title)}"
                    )
                    if external_id in seen_external_ids:
                        continue
                    seen_external_ids.add(external_id)

                    brand = _extract_brand(hit)
                    jan = _safe_str(hit.get("janCode"))
                    model_number = extract_model_number(title)
                    condition = resolve_condition(
                        _extract_condition_text(hit),
                        title,
                    )
                    price = _extract_price_jpy(hit)
                    shipping = _extract_shipping_jpy(hit)

                    records.append(
                        ListingRecord(
                            external_id=external_id,
                            site="yahoo-shopping",
                            category=category,
                            title=title,
                            brand=brand,
                            model_number=model_number,
                            code=jan,
                            condition=condition,
                            price=price,
                            shipping=shipping,
                            weight_g=0,
                        )
                    )
                    if len(records) >= requested_limit:
                        break

                if len(hits) < page_size:
                    break

                start += len(hits)
                page_count += 1

        return records


def _safe_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _extract_brand(hit: dict[str, Any]) -> str:
    brand = hit.get("brand")
    if isinstance(brand, dict):
        return _safe_str(brand.get("name"))
    return _safe_str(brand)


def _extract_price_jpy(hit: dict[str, Any]) -> float:
    if isinstance(hit.get("price"), (int, float)):
        return float(hit["price"])
    price_label = hit.get("priceLabel")
    if isinstance(price_label, dict):
        for key in ("defaultPrice", "taxIn", "taxEx"):
            value = price_label.get(key)
            if isinstance(value, (int, float, str)) and str(value).strip():
                try:
                    return float(value)
                except ValueError:
                    continue
    return 0.0


def _extract_shipping_jpy(hit: dict[str, Any]) -> float:
    shipping = hit.get("shipping")
    if isinstance(shipping, dict):
        value = shipping.get("price")
        if isinstance(value, (int, float, str)) and str(value).strip():
            try:
                return float(value)
            except ValueError:
                return 0.0
    return 0.0


def _extract_condition_text(hit: dict[str, Any]) -> str:
    condition = hit.get("condition")
    if isinstance(condition, dict):
        return _safe_str(condition.get("name") or condition.get("id"))
    return _safe_str(condition)


def _normalize_public_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw.startswith("http://") and not raw.startswith("https://"):
        return ""
    parts = urlsplit(raw)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
