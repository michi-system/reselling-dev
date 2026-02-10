from __future__ import annotations

import re
import time
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

# Legacy app.rakuten endpoint has been sunset; use the current OpenAPI endpoint.
RAKUTEN_ICHIBA_SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"
_MAX_429_RETRIES = 3


class RakutenIchibaAdapter(SourceAdapter):
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.rakuten_app_id:
            raise ExternalApiError("RAKUTEN_APP_ID is not set")
        if self.settings.rakuten_app_id.startswith("pk_"):
            raise ExternalApiError(
                "RAKUTEN_APP_ID looks like Access Key (pk_...). "
                "Set RAKUTEN_APP_ID to Application ID and RAKUTEN_ACCESS_KEY to Access Key."
            )

    def fetch(self, query: str, category: str, limit: int = 20, cursor: int = 0) -> list[ListingRecord]:
        requested_limit = max(1, min(int(limit), 100))
        page_size = 30
        max_page = 99
        first_page = min(max_page, _offset_to_page(cursor=cursor, limit=page_size))
        skip_in_first_page = max(0, int(cursor)) % page_size

        headers: dict[str, str] = {}
        if self.settings.rakuten_access_key:
            headers["Authorization"] = f"Bearer {self.settings.rakuten_access_key}"

        records: list[ListingRecord] = []
        seen_external_ids: set[str] = set()
        page = first_page
        first_loop = True
        with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
            while len(records) < requested_limit:
                params = {
                    "format": "json",
                    "applicationId": self.settings.rakuten_app_id,
                    "keyword": query,
                    "hits": page_size,
                    "page": page,
                }
                if self.settings.rakuten_access_key:
                    params["accessKey"] = self.settings.rakuten_access_key

                response = _get_with_429_retry(
                    client=client,
                    url=RAKUTEN_ICHIBA_SEARCH_URL,
                    params=params,
                    headers=headers or None,
                    min_interval_seconds=self.settings.rakuten_min_interval_seconds,
                )
                if response.status_code >= 400:
                    body = response.text[:200]
                    if response.status_code == 400 and "specify valid applicationId" in body:
                        raise ExternalApiError(
                            "Rakuten API error: invalid applicationId. "
                            "Check RAKUTEN_APP_ID (Application ID) and set RAKUTEN_ACCESS_KEY if required."
                        )
                    raise ExternalApiError(f"Rakuten API error: {response.status_code} {body}")

                payload = response.json()
                items = payload.get("Items", [])
                if not items:
                    break

                start_index = skip_in_first_page if first_loop else 0
                first_loop = False
                for idx in range(start_index, len(items)):
                    wrapped = items[idx]
                    item = wrapped.get("Item", {}) if isinstance(wrapped, dict) else {}
                    title = _safe_str(item.get("itemName"))
                    if not title:
                        continue

                    external_id = (
                        _normalize_public_url(_safe_str(item.get("itemUrl")))
                        or _safe_str(item.get("itemCode"))
                        or f"rakuten-{page}-{idx}-{hash(title)}"
                    )
                    postage_flag = item.get("postageFlag")
                    shipping = 0.0 if str(postage_flag) == "0" else 500.0
                    price = _extract_price(item.get("itemPrice"))
                    model_number = extract_model_number(title)
                    condition = resolve_condition(
                        _safe_str(item.get("condition")),
                        title,
                        _safe_str(item.get("itemCaption")),
                    )
                    if external_id in seen_external_ids:
                        continue
                    seen_external_ids.add(external_id)

                    records.append(
                        ListingRecord(
                            external_id=external_id,
                            site="rakuten-ichiba",
                            category=category,
                            title=title,
                            brand="",
                            model_number=model_number,
                            code="",
                            condition=condition,
                            price=price,
                            shipping=shipping,
                            weight_g=0,
                        )
                    )
                    if len(records) >= requested_limit:
                        break

                if len(items) < page_size:
                    break
                if page >= max_page:
                    break
                page += 1

        return records


def _safe_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _extract_price(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _normalize_public_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw.startswith("http://") and not raw.startswith("https://"):
        return ""
    parts = urlsplit(raw)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _offset_to_page(cursor: int, limit: int) -> int:
    safe_limit = max(1, int(limit))
    safe_cursor = max(0, int(cursor))
    return (safe_cursor // safe_limit) + 1


def _get_with_429_retry(
    client: httpx.Client,
    url: str,
    params: dict[str, Any],
    headers: dict[str, str] | None,
    min_interval_seconds: float,
) -> httpx.Response:
    attempt = 0
    while True:
        wait_for_slot("rakuten_ichiba_search", min_interval_seconds)
        record_api_call("rakuten")
        response = client.get(url, params=params, headers=headers)
        if response.status_code != 429:
            return response
        if attempt >= _MAX_429_RETRIES:
            return response

        delay_seconds = _extract_retry_after_seconds(response)
        time.sleep(max(delay_seconds, min_interval_seconds, 0.1))
        attempt += 1


def _extract_retry_after_seconds(response: httpx.Response) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            value = float(retry_after)
            if value > 0:
                return value
        except ValueError:
            pass

    message = response.text or ""
    match = re.search(r"Try again in\s+(\d+(?:\.\d+)?)\s+seconds", message, flags=re.IGNORECASE)
    if match:
        try:
            value = float(match.group(1))
            if value > 0:
                return value
        except ValueError:
            pass
    return 1.0
