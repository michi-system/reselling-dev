from __future__ import annotations

import base64
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import floor
from typing import Any

import httpx
from sqlalchemy import delete, func, select

from app.core.config import Settings
from app.db.models import ApiUsageEvent
from app.db.session import SessionLocal

WINDOW_MINUTES = 60
_KNOWN_PROVIDERS = ("yahoo", "rakuten", "ebay")

_EBAY_OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
_EBAY_DEFAULT_RATE_LIMIT_URL = "https://api.ebay.com/developer/analytics/v1_beta/rate_limit/"
_EBAY_RATE_LIMIT_CACHE_TTL_SECONDS = 60

_lock = threading.Lock()
_ebay_token: str | None = None
_ebay_token_expire_at: float = 0.0
_ebay_rate_cache_until: float = 0.0
_ebay_rate_cache_value: "EbayRateLimitSnapshot | None" = None


@dataclass
class ApiUsageItem:
    provider: str
    calls_last_hour: int
    hourly_budget: int | None
    usage_rate_percent: float | None
    remaining_calls: int | None
    usage_basis: str
    limit_window: str
    note: str


@dataclass
class EbayRateLimitSnapshot:
    limit: int
    remaining: int
    limit_window: str
    resource_name: str
    fetched_at: datetime


def record_api_call(provider: str) -> None:
    normalized = provider.strip().lower()
    if normalized not in _KNOWN_PROVIDERS:
        return
    now = datetime.now(UTC)
    db = SessionLocal()
    try:
        db.add(ApiUsageEvent(provider=normalized, called_at=now))
        db.execute(delete(ApiUsageEvent).where(ApiUsageEvent.called_at < now - timedelta(minutes=WINDOW_MINUTES * 24)))
        db.commit()
    finally:
        db.close()


def build_usage_snapshot(settings: Settings) -> list[ApiUsageItem]:
    now = datetime.now(UTC)
    threshold = now - timedelta(minutes=WINDOW_MINUTES)

    db = SessionLocal()
    try:
        db.execute(delete(ApiUsageEvent).where(ApiUsageEvent.called_at < threshold))
        rows = db.execute(
            select(ApiUsageEvent.provider, func.count(ApiUsageEvent.id))
            .where(ApiUsageEvent.called_at >= threshold)
            .group_by(ApiUsageEvent.provider)
        ).all()
        db.commit()
    finally:
        db.close()

    counts = {provider: 0 for provider in _KNOWN_PROVIDERS}
    for provider, count in rows:
        counts[str(provider)] = int(count)

    ebay_official = _get_ebay_rate_limit_snapshot(settings=settings)

    items: list[ApiUsageItem] = []
    for provider in _KNOWN_PROVIDERS:
        calls = counts.get(provider, 0)
        if provider == "ebay" and ebay_official is not None:
            limit = max(1, int(ebay_official.limit))
            remaining = max(0, int(ebay_official.remaining))
            usage_rate = min(100.0, ((limit - remaining) / limit) * 100.0)
            items.append(
                ApiUsageItem(
                    provider=provider,
                    calls_last_hour=calls,
                    hourly_budget=limit,
                    usage_rate_percent=usage_rate,
                    remaining_calls=remaining,
                    usage_basis="official",
                    limit_window=ebay_official.limit_window,
                    note=f"eBay公式Rate Limits API（resource={ebay_official.resource_name}）",
                )
            )
            continue

        local_budget = _local_budget_per_hour(provider=provider, settings=settings)
        if local_budget is None:
            items.append(
                ApiUsageItem(
                    provider=provider,
                    calls_last_hour=calls,
                    hourly_budget=None,
                    usage_rate_percent=None,
                    remaining_calls=None,
                    usage_basis="unknown",
                    limit_window="不明",
                    note="公式上限の残量取得手段がないため、直近呼び出し回数のみ表示",
                )
            )
            continue

        usage_rate = min(100.0, (calls / local_budget) * 100.0)
        items.append(
            ApiUsageItem(
                provider=provider,
                calls_last_hour=calls,
                hourly_budget=local_budget,
                usage_rate_percent=usage_rate,
                remaining_calls=max(0, local_budget - calls),
                usage_basis="local_throttle",
                limit_window="1h（ローカル抑止換算）",
                note="公式上限ではなく、クライアント側の最小間隔設定から算出",
            )
        )
    return items


def reset_api_usage_for_tests() -> None:
    db = SessionLocal()
    try:
        db.query(ApiUsageEvent).delete()
        db.commit()
    finally:
        db.close()
    global _ebay_rate_cache_value, _ebay_rate_cache_until, _ebay_token, _ebay_token_expire_at
    _ebay_rate_cache_value = None
    _ebay_rate_cache_until = 0.0
    _ebay_token = None
    _ebay_token_expire_at = 0.0


def _local_budget_per_hour(provider: str, settings: Settings) -> int | None:
    configured_budget = {
        "yahoo": int(settings.yahoo_hourly_call_budget),
        "rakuten": int(settings.rakuten_hourly_call_budget),
        "ebay": int(settings.ebay_hourly_call_budget),
    }.get(provider, 0)
    if configured_budget > 0:
        return configured_budget

    interval = {
        "yahoo": float(settings.yahoo_min_interval_seconds),
        "rakuten": float(settings.rakuten_min_interval_seconds),
        "ebay": float(settings.ebay_min_interval_seconds),
    }.get(provider, 0.0)
    if interval <= 0:
        return None
    return max(1, floor(3600.0 / interval))


def _get_ebay_rate_limit_snapshot(settings: Settings) -> EbayRateLimitSnapshot | None:
    global _ebay_rate_cache_value, _ebay_rate_cache_until
    if not settings.api_usage_use_ebay_rate_api:
        return None
    if not settings.ebay_client_id or not settings.ebay_client_secret:
        return None

    now = time.time()
    with _lock:
        if _ebay_rate_cache_value is not None and now < _ebay_rate_cache_until:
            return _ebay_rate_cache_value

    snapshot = _fetch_ebay_rate_limit_snapshot(settings=settings)
    with _lock:
        _ebay_rate_cache_value = snapshot
        _ebay_rate_cache_until = time.time() + _EBAY_RATE_LIMIT_CACHE_TTL_SECONDS
    return snapshot


def _fetch_ebay_rate_limit_snapshot(settings: Settings) -> EbayRateLimitSnapshot | None:
    token = _get_ebay_app_token(settings=settings)
    if not token:
        return None

    url = (settings.ebay_rate_limit_api_url or "").strip() or _EBAY_DEFAULT_RATE_LIMIT_URL
    params = {"api_name": "browse", "api_context": "buy"}
    headers = {"Authorization": f"Bearer {token}"}
    timeout = max(1.0, min(10.0, float(settings.http_timeout_seconds)))

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params, headers=headers)
    except Exception:
        return None

    if response.status_code >= 400:
        return None

    try:
        payload = response.json()
    except Exception:
        return None

    pairs = _collect_ebay_limit_pairs(payload)
    if not pairs:
        return None

    chosen = min(
        pairs,
        key=lambda p: ((p["remaining"] / max(1, p["limit"])), p["remaining"]),
    )
    limit = int(chosen["limit"])
    remaining = int(chosen["remaining"])
    window = str(chosen.get("window") or "不明")
    resource = str(chosen.get("resource") or "unknown")
    return EbayRateLimitSnapshot(
        limit=max(1, limit),
        remaining=max(0, remaining),
        limit_window=window,
        resource_name=resource,
        fetched_at=datetime.now(UTC),
    )


def _get_ebay_app_token(settings: Settings) -> str | None:
    global _ebay_token, _ebay_token_expire_at
    now = time.time()
    with _lock:
        if _ebay_token and now < _ebay_token_expire_at:
            return _ebay_token

    credential = f"{settings.ebay_client_id}:{settings.ebay_client_secret}".encode("utf-8")
    encoded = base64.b64encode(credential).decode("utf-8")
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }
    timeout = max(1.0, min(10.0, float(settings.http_timeout_seconds)))

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(_EBAY_OAUTH_URL, data=data, headers=headers)
    except Exception:
        return None

    if response.status_code >= 400:
        return None
    try:
        payload = response.json()
    except Exception:
        return None

    token = str(payload.get("access_token") or "").strip()
    if not token:
        return None
    expires_in = int(payload.get("expires_in") or 7200)

    with _lock:
        _ebay_token = token
        _ebay_token_expire_at = time.time() + max(300, expires_in - 120)
    return token


def _collect_ebay_limit_pairs(payload: Any) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []

    def walk(node: Any, resource_name: str = "") -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, resource_name=resource_name)
            return
        if not isinstance(node, dict):
            return

        current_resource = str(node.get("name") or node.get("resourceName") or resource_name or "").strip()
        limit = _to_int(node.get("limit"))
        remaining = _to_int(node.get("remaining"))
        if limit is not None and remaining is not None:
            pairs.append(
                {
                    "limit": limit,
                    "remaining": remaining,
                    "window": _extract_window_label(node),
                    "resource": current_resource or "unknown",
                }
            )

        for value in node.values():
            walk(value, resource_name=current_resource)

    walk(payload)
    return pairs


def _extract_window_label(node: dict[str, Any]) -> str:
    # eBay payload may include a reset timestamp or a generic time-window field depending on endpoint version.
    reset = str(node.get("reset") or node.get("nextResetTime") or "").strip()
    if reset:
        return f"reset={reset}"

    seconds = _to_int(node.get("timeWindow") or node.get("timeWindowSeconds"))
    if seconds is not None and seconds > 0:
        if seconds % 3600 == 0:
            return f"{seconds // 3600}h"
        if seconds % 60 == 0:
            return f"{seconds // 60}m"
        return f"{seconds}s"
    return "不明"


def _to_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed
