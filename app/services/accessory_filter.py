from dataclasses import dataclass, field
import re

from app.db.models import MarketItem, SourceItem
from app.services.normalizer import normalize_text, tokenize


ACCESSORY_KEYWORDS = {
    "case",
    "cover",
    "shell",
    "strap",
    "cable",
    "adapter",
    "holder",
    "mount",
    "for",
    "compatible",
    "replacement",
    "parts",
    "empty box",
    "manual",
    "speaker cover",
    "lens cap",
}

ACCESSORY_PATTERNS = [
    re.compile(r"\bfor\b"),
    re.compile(r"\bcompatible with\b"),
    re.compile(r"\breplacement\b"),
    re.compile(r"\bpart[s]?\b"),
]


@dataclass
class AccessoryResult:
    score: float
    reasons: list[str] = field(default_factory=list)


def score_accessory_risk(source: SourceItem, market: MarketItem) -> AccessoryResult:
    title = normalize_text(market.title)
    source_title = normalize_text(source.title)
    reasons: list[str] = []
    risk = 0.0

    for keyword in ACCESSORY_KEYWORDS:
        if keyword in title:
            risk += 0.16
            reasons.append(f"keyword:{keyword}")

    for pattern in ACCESSORY_PATTERNS:
        if pattern.search(title):
            risk += 0.12
            reasons.append(f"pattern:{pattern.pattern}")

    if source.model_number:
        normalized_model = normalize_text(source.model_number)
        if normalized_model and normalized_model not in title:
            risk += 0.20
            reasons.append("missing_model_token")

    if source.brand and source.brand.lower() not in title:
        risk += 0.10
        reasons.append("missing_brand_token")

    # If market title misses most source core tokens, treat as accessory-like mismatch.
    source_tokens = {t for t in tokenize(source_title) if len(t) >= 4}
    market_tokens = tokenize(title)
    if source_tokens:
        common = len(source_tokens & market_tokens)
        ratio = common / len(source_tokens)
        if ratio < 0.30:
            risk += 0.20
            reasons.append(f"low_core_token_overlap:{ratio:.2f}")

    if market.price_usd > 0 and source.price_jpy > 0:
        source_usd = source.price_jpy / 150
        if market.price_usd < source_usd * 0.25:
            risk += 0.35
            reasons.append("price_too_low_vs_source")

    risk = min(1.0, risk)
    return AccessoryResult(score=risk, reasons=reasons)
