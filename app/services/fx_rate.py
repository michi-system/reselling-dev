from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import threading
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.errors import ExternalApiError
from app.core.config import get_settings
from app.db.models import FxRateState
from app.db.session import SessionLocal

USD_JPY_PAIR = "USDJPY"

_cache_lock = threading.Lock()
_cached_rate: float | None = None
_cached_source: str = "config"
_cached_fetched_at: datetime | None = None


@dataclass
class FxRateStatus:
    pair: str
    rate: float
    source: str
    fetched_at: datetime | None
    next_refresh_at: datetime | None
    last_error: str


def get_current_usd_jpy_rate() -> float:
    with _cache_lock:
        if _cached_rate is not None:
            return _cached_rate

    settings = get_settings()
    db = SessionLocal()
    try:
        state = db.scalar(select(FxRateState).where(FxRateState.pair == USD_JPY_PAIR))
    finally:
        db.close()

    if state and state.rate > 0:
        _set_cache(rate=float(state.rate), source=state.source or "db", fetched_at=state.fetched_at)
        return float(state.rate)

    _set_cache(rate=float(settings.fx_usd_jpy), source="config", fetched_at=None)
    return float(settings.fx_usd_jpy)


def maybe_refresh_usd_jpy_rate(db: Session) -> FxRateStatus:
    settings = get_settings()
    now = datetime.now(UTC)
    state = _get_or_create_state(db=db, now=now)

    _set_cache(rate=float(state.rate), source=state.source or "db", fetched_at=state.fetched_at)
    if not settings.fx_auto_update_enabled:
        return _to_status(state)

    next_refresh = _as_utc(state.next_refresh_at) if state.next_refresh_at else None
    if next_refresh and next_refresh > now:
        return _to_status(state)

    try:
        rate, source = _fetch_usd_jpy_from_provider()
    except ExternalApiError as exc:
        state.last_error = str(exc)
        retry_minutes = max(1, int(settings.fx_refresh_retry_minutes))
        state.next_refresh_at = now + timedelta(minutes=retry_minutes)
        db.commit()
        db.refresh(state)
        return _to_status(state)

    state.rate = rate
    state.source = source
    state.fetched_at = now
    state.last_error = ""
    state.next_refresh_at = now + timedelta(minutes=max(1, int(settings.fx_update_interval_minutes)))
    db.commit()
    db.refresh(state)
    _set_cache(rate=rate, source=source, fetched_at=state.fetched_at)
    return _to_status(state)


def refresh_usd_jpy_rate_now(db: Session) -> FxRateStatus:
    now = datetime.now(UTC)
    state = _get_or_create_state(db=db, now=now)
    rate, source = _fetch_usd_jpy_from_provider()

    settings = get_settings()
    state.rate = rate
    state.source = source
    state.fetched_at = now
    state.last_error = ""
    state.next_refresh_at = now + timedelta(minutes=max(1, int(settings.fx_update_interval_minutes)))
    db.commit()
    db.refresh(state)
    _set_cache(rate=rate, source=source, fetched_at=state.fetched_at)
    return _to_status(state)


def get_usd_jpy_status(db: Session) -> FxRateStatus:
    state = db.scalar(select(FxRateState).where(FxRateState.pair == USD_JPY_PAIR))
    if state is None:
        state = _get_or_create_state(db=db, now=datetime.now(UTC))
    _set_cache(rate=float(state.rate), source=state.source or "db", fetched_at=state.fetched_at)
    return _to_status(state)


def _get_or_create_state(db: Session, now: datetime) -> FxRateState:
    settings = get_settings()
    state = db.scalar(select(FxRateState).where(FxRateState.pair == USD_JPY_PAIR))
    if state is not None:
        return state

    state = FxRateState(
        pair=USD_JPY_PAIR,
        rate=float(settings.fx_usd_jpy),
        source="config",
        fetched_at=None,
        next_refresh_at=now + timedelta(minutes=max(1, int(settings.fx_update_interval_minutes))),
        last_error="",
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def _fetch_usd_jpy_from_provider() -> tuple[float, str]:
    settings = get_settings()
    url = settings.fx_rate_provider_url.strip()
    if not url:
        raise ExternalApiError("FX rate provider URL is not configured")

    try:
        with httpx.Client(timeout=settings.http_timeout_seconds) as client:
            response = client.get(url)
    except httpx.HTTPError as exc:
        raise ExternalApiError(f"FX provider connection error: {exc}") from exc

    if response.status_code >= 400:
        raise ExternalApiError(f"FX provider error: {response.status_code} {response.text[:200]}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise ExternalApiError("FX provider returned invalid JSON") from exc

    rate = _extract_usd_jpy_rate(payload)
    source = urlsplit(url).netloc or "fx-provider"
    return rate, source


def _extract_usd_jpy_rate(payload: object) -> float:
    if isinstance(payload, dict):
        rates = payload.get("rates")
        if isinstance(rates, dict):
            jpy = rates.get("JPY")
            if isinstance(jpy, (int, float)) and float(jpy) > 0:
                return float(jpy)

        conversion_rates = payload.get("conversion_rates")
        if isinstance(conversion_rates, dict):
            jpy = conversion_rates.get("JPY")
            if isinstance(jpy, (int, float)) and float(jpy) > 0:
                return float(jpy)

        data = payload.get("data")
        if isinstance(data, dict):
            jpy_info = data.get("JPY")
            if isinstance(jpy_info, dict):
                jpy = jpy_info.get("value")
                if isinstance(jpy, (int, float)) and float(jpy) > 0:
                    return float(jpy)

    raise ExternalApiError("FX provider response does not include USD->JPY rate")


def _to_status(state: FxRateState) -> FxRateStatus:
    return FxRateStatus(
        pair=state.pair,
        rate=float(state.rate),
        source=state.source or "unknown",
        fetched_at=state.fetched_at,
        next_refresh_at=state.next_refresh_at,
        last_error=state.last_error or "",
    )


def _set_cache(rate: float, source: str, fetched_at: datetime | None) -> None:
    with _cache_lock:
        global _cached_rate, _cached_source, _cached_fetched_at
        _cached_rate = rate
        _cached_source = source
        _cached_fetched_at = fetched_at


def reset_fx_rate_cache_for_tests() -> None:
    with _cache_lock:
        global _cached_rate, _cached_source, _cached_fetched_at
        _cached_rate = None
        _cached_source = "config"
        _cached_fetched_at = None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
