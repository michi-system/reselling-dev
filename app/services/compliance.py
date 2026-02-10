from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import get_settings
from app.db.models import MarketItem, SourceItem


@dataclass
class ComplianceCheckResult:
    mode: str
    risk_level: str
    reasons: list[str] = field(default_factory=list)
    block_auto_accept: bool = False
    force_human_review: bool = False


def evaluate_compliance(source: SourceItem, market: MarketItem) -> ComplianceCheckResult:
    settings = get_settings()
    mode = settings.compliance_mode.lower().strip()
    if mode not in {"strict", "warn", "off"}:
        mode = "warn"

    reasons: list[str] = []

    source_site = (source.source_site or "").lower()
    market_site = (market.marketplace or "").lower()

    if market_site.startswith("ebay") and not source_site.startswith("ebay"):
        reasons.append("cross_market_to_ebay")

    if "mercari" in source_site:
        reasons.append("mercari_terms_sensitive_source")

    if "rakuten" in source_site:
        reasons.append("rakuten_usage_terms_check_required")

    if not reasons or mode == "off":
        return ComplianceCheckResult(mode=mode, risk_level="low", reasons=reasons)

    if mode == "warn":
        return ComplianceCheckResult(mode=mode, risk_level="medium", reasons=reasons)

    # strict
    block_auto_accept = settings.block_auto_accept_cross_market and "cross_market_to_ebay" in reasons
    force_human_review = "mercari_terms_sensitive_source" in reasons
    risk_level = "high" if (block_auto_accept or force_human_review) else "medium"

    return ComplianceCheckResult(
        mode=mode,
        risk_level=risk_level,
        reasons=reasons,
        block_auto_accept=block_auto_accept,
        force_human_review=force_human_review,
    )
