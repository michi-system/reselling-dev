from __future__ import annotations

import base64
import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.adapters.base import ListingRecord, MarketAdapter
from app.adapters.errors import ExternalApiError
from app.core.config import get_settings
from app.services.api_usage import record_api_call
from app.services.condition_infer import resolve_condition
from app.services.model_extract import extract_model_number
from app.services.rate_limit import wait_for_slot

EBAY_OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_BROWSE_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


class EbayBrowseAdapter(MarketAdapter):
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.ebay_client_id or not self.settings.ebay_client_secret:
            raise ExternalApiError("EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required")
        self._token: str | None = None
        self._token_expire_at: float = 0.0

    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        wait_for_slot("ebay_browse_search", self.settings.ebay_min_interval_seconds)
        record_api_call("ebay")

        token = self._get_access_token()
        normalized_limit = max(1, min(limit, 200))
        params = {
            "q": query,
            "limit": normalized_limit,
            "filter": "buyingOptions:{FIXED_PRICE}",
        }
        if cursor > 0:
            params["offset"] = _normalize_offset(cursor=cursor, limit=normalized_limit)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self.settings.ebay_marketplace_id,
        }

        with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
            response = client.get(EBAY_BROWSE_SEARCH_URL, params=params, headers=headers)

        if response.status_code >= 400:
            raise ExternalApiError(f"eBay Browse API error: {response.status_code} {response.text[:240]}")

        payload = response.json()
        item_summaries = payload.get("itemSummaries", [])
        records: list[ListingRecord] = []

        for idx, item in enumerate(item_summaries):
            title = _safe_str(item.get("title"))
            if not title:
                continue

            price = _extract_price(item.get("price"))
            if price <= 0:
                continue

            shipping = _extract_shipping(item.get("shippingOptions"))
            external_id = (
                _normalize_public_url(_safe_str(item.get("itemWebUrl")))
                or _safe_str(item.get("itemId"))
                or f"ebay-{idx}-{hash(title)}"
            )
            condition = resolve_condition(
                _safe_str(item.get("condition")),
                title,
                _safe_str(item.get("subtitle")),
            )

            records.append(
                ListingRecord(
                    external_id=external_id,
                    site="ebay",
                    category=category,
                    title=title,
                    brand=_safe_str(item.get("brand")),
                    model_number=_safe_str(item.get("mpn")) or extract_model_number(title),
                    code=_safe_str(item.get("gtin")),
                    condition=condition,
                    price=price,
                    shipping=shipping,
                    weight_g=0,
                    price_confidence="semi_trusted",
                )
            )

        return records

    def _get_access_token(self) -> str:
        if self._token and time.time() < self._token_expire_at:
            return self._token

        scope = "https://api.ebay.com/oauth/api_scope"
        credential = f"{self.settings.ebay_client_id}:{self.settings.ebay_client_secret}".encode("utf-8")
        encoded = base64.b64encode(credential).decode("utf-8")
        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "client_credentials",
            "scope": scope,
        }
        wait_for_slot("ebay_oauth_token", self.settings.ebay_min_interval_seconds)
        record_api_call("ebay")

        with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
            response = client.post(EBAY_OAUTH_URL, data=data, headers=headers)

        if response.status_code >= 400:
            raise ExternalApiError(f"eBay OAuth error: {response.status_code} {response.text[:240]}")

        payload = response.json()
        token = payload.get("access_token")
        expires_in = payload.get("expires_in", 7200)
        if not token:
            raise ExternalApiError("eBay OAuth error: access_token missing")

        self._token = str(token)
        self._token_expire_at = time.time() + max(300, int(expires_in) - 120)
        return self._token


def _safe_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _extract_price(price_obj: Any) -> float:
    if not isinstance(price_obj, dict):
        return 0.0
    value = price_obj.get("value")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _extract_shipping(shipping_options: Any) -> float:
    if not isinstance(shipping_options, list) or not shipping_options:
        return 0.0

    for option in shipping_options:
        if not isinstance(option, dict):
            continue
        shipping_cost = option.get("shippingCost")
        if isinstance(shipping_cost, dict):
            value = shipping_cost.get("value")
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str) and value.strip():
                try:
                    return float(value)
                except ValueError:
                    continue
    return 0.0


def _normalize_offset(cursor: int, limit: int) -> int:
    safe_limit = max(1, int(limit))
    safe_cursor = max(0, int(cursor))
    aligned = (safe_cursor // safe_limit) * safe_limit
    max_aligned = (10000 // safe_limit) * safe_limit
    return min(aligned, max_aligned)


def _normalize_public_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw.startswith("http://") and not raw.startswith("https://"):
        return ""
    parts = urlsplit(raw)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
