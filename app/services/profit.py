from dataclasses import dataclass

from app.core.config import get_settings
from app.db.models import MarketItem, SourceItem
from app.services.fx_rate import get_current_usd_jpy_rate


@dataclass
class ProfitResult:
    revenue_jpy: float
    total_cost_jpy: float
    expected_profit_jpy: float
    expected_margin_rate: float
    storage_score: float
    shipping_score: float


def estimate_international_shipping_jpy(weight_g: int) -> float:
    if weight_g <= 250:
        return 1400
    if weight_g <= 500:
        return 1800
    if weight_g <= 1000:
        return 2600
    if weight_g <= 2000:
        return 3900
    return 6400


def calculate_profit(source: SourceItem, market: MarketItem) -> ProfitResult:
    settings = get_settings()
    usd_jpy_rate = get_current_usd_jpy_rate()

    revenue_jpy = (market.price_usd + market.shipping_usd) * usd_jpy_rate
    fees = revenue_jpy * (settings.ebay_fee_rate + settings.international_payment_fee_rate)

    intl_shipping_jpy = estimate_international_shipping_jpy(source.weight_g)
    procurement_cost_jpy = source.price_jpy + source.shipping_jpy
    total_cost_jpy = procurement_cost_jpy + intl_shipping_jpy + settings.packaging_cost_jpy + fees

    expected_profit_jpy = revenue_jpy - total_cost_jpy
    expected_margin_rate = expected_profit_jpy / revenue_jpy if revenue_jpy > 0 else -1.0

    storage_score = 1.0 if source.weight_g <= 500 else 0.6 if source.weight_g <= 1500 else 0.2
    shipping_score = 1.0 if source.weight_g <= 500 else 0.5 if source.weight_g <= 1500 else 0.1

    return ProfitResult(
        revenue_jpy=revenue_jpy,
        total_cost_jpy=total_cost_jpy,
        expected_profit_jpy=expected_profit_jpy,
        expected_margin_rate=expected_margin_rate,
        storage_score=storage_score,
        shipping_score=shipping_score,
    )
