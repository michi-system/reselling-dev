from __future__ import annotations

from app.core.config import Settings


def resolve_min_margin_rate(category: str, settings: Settings) -> float:
    category_key = (category or "").strip().lower()
    base = settings.min_expected_margin_rate
    overrides = _parse_category_margin_overrides(settings.category_min_margin_overrides)
    return overrides.get(category_key, base)


def _parse_category_margin_overrides(raw: str) -> dict[str, float]:
    parsed: dict[str, float] = {}
    if not raw:
        return parsed

    for part in raw.split(","):
        token = part.strip()
        if not token or ":" not in token:
            continue
        key, value = token.split(":", 1)
        key = key.strip().lower()
        if not key:
            continue
        try:
            rate = float(value.strip())
        except ValueError:
            continue
        if rate < 0:
            continue
        parsed[key] = rate

    return parsed
