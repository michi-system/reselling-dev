import json
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import MarketItem, Opportunity, SourceItem
from app.services.accessory_filter import score_accessory_risk
from app.services.compliance import evaluate_compliance
from app.services.condition_infer import condition_gate_reason, normalize_requested_condition, resolve_condition
from app.services.matcher import score_match
from app.services.model_extract import normalize_model_key, title_contains_model
from app.services.profit import calculate_profit
from app.services.rules import resolve_min_margin_rate


@dataclass
class RuntimeThresholds:
    min_auto_accept_score: float
    min_human_review_score: float
    min_title_similarity_auto_accept: float
    min_title_similarity_human_review: float
    min_expected_profit_jpy: float
    min_margin_rate: float
    accessory_reject_score: float


def run_pipeline(
    db: Session,
    source_item: SourceItem,
    category: str | None = None,
    only_small_items: bool = True,
    listing_condition_filter: str = "any",
    threshold_overrides: dict[str, float] | None = None,
    market_item_ids: Sequence[int] | None = None,
) -> list[Opportunity]:
    settings = get_settings()
    thresholds = _resolve_runtime_thresholds(
        source_item=source_item,
        overrides=threshold_overrides or {},
    )

    if only_small_items and source_item.weight_g > 2000:
        return []

    market_query = db.query(MarketItem)
    if market_item_ids is not None:
        ids = [int(item_id) for item_id in market_item_ids if int(item_id) > 0]
        if not ids:
            return []
        market_query = market_query.filter(MarketItem.id.in_(ids))
    if category:
        market_query = market_query.filter(MarketItem.category == category)
    else:
        market_query = market_query.filter(MarketItem.category == source_item.category)

    candidates = market_query.all()
    if market_item_ids is not None:
        # Live trial path: reduce obvious non-matching comparisons for precision.
        candidates = _narrow_candidates_by_model(source_item=source_item, candidates=candidates)
    opportunities: list[Opportunity] = []
    normalized_requested_condition = normalize_requested_condition(listing_condition_filter)
    source_condition = resolve_condition(source_item.condition, source_item.title, source_item.model_number)

    for market in candidates:
        match = score_match(source_item, market)
        accessory = score_accessory_risk(source_item, market)
        profit = calculate_profit(source_item, market)
        compliance = evaluate_compliance(source_item, market)
        market_condition = resolve_condition(market.condition, market.title, market.model_number)
        condition_reject_reason = condition_gate_reason(
            source_condition=source_condition,
            market_condition=market_condition,
            requested_condition=normalized_requested_condition,
        )
        reject_reason = ""

        if condition_reject_reason:
            decision = "reject"
            reject_reason = condition_reject_reason
        elif accessory.score >= thresholds.accessory_reject_score:
            decision = "reject"
            reject_reason = "accessory_risk_high"
        elif (
            match.score >= thresholds.min_auto_accept_score
            and match.title_similarity >= thresholds.min_title_similarity_auto_accept
            and market.price_confidence != "noisy"
            and (
                not settings.auto_accept_requires_trusted_price
                or market.price_confidence == "trusted"
            )
            and profit.expected_profit_jpy >= thresholds.min_expected_profit_jpy
            and profit.expected_margin_rate >= thresholds.min_margin_rate
        ):
            decision = "auto_accept"
        elif (
            match.score >= thresholds.min_human_review_score
            and match.title_similarity >= thresholds.min_title_similarity_human_review
            and profit.expected_profit_jpy >= thresholds.min_expected_profit_jpy
        ):
            decision = "human_review"
        else:
            decision = "reject"
            if profit.expected_profit_jpy < thresholds.min_expected_profit_jpy:
                reject_reason = "profit_below_threshold"
            elif profit.expected_margin_rate < thresholds.min_margin_rate:
                reject_reason = "margin_below_threshold"
            elif match.title_similarity < thresholds.min_title_similarity_human_review:
                reject_reason = "title_similarity_low"
            elif match.score < thresholds.min_human_review_score:
                reject_reason = "match_score_low"
            elif market.price_confidence == "noisy":
                reject_reason = "price_confidence_low"
            else:
                reject_reason = "rule_gate_failed"

        if decision == "auto_accept" and compliance.block_auto_accept:
            decision = "human_review"
            reject_reason = "compliance_block_auto_accept"

        if decision in {"auto_accept", "human_review"} and compliance.force_human_review:
            decision = "human_review"
            reject_reason = "compliance_force_human_review"

        trace = {
            "match_reasons": match.reasons,
            "title_similarity": round(match.title_similarity, 4),
            "source_condition": source_condition,
            "market_condition": market_condition,
            "requested_condition": normalized_requested_condition,
            "accessory_reasons": accessory.reasons,
            "price_confidence": market.price_confidence,
            "expected_revenue_jpy": round(profit.revenue_jpy, 2),
            "expected_total_cost_jpy": round(profit.total_cost_jpy, 2),
            "expected_margin_rate": round(profit.expected_margin_rate, 4),
            "min_margin_rate": round(thresholds.min_margin_rate, 4),
            "min_expected_profit_jpy": round(thresholds.min_expected_profit_jpy, 2),
            "min_auto_accept_score": round(thresholds.min_auto_accept_score, 4),
            "min_human_review_score": round(thresholds.min_human_review_score, 4),
            "min_title_similarity_auto_accept": round(thresholds.min_title_similarity_auto_accept, 4),
            "min_title_similarity_human_review": round(thresholds.min_title_similarity_human_review, 4),
            "accessory_reject_score": round(thresholds.accessory_reject_score, 4),
            "reject_reason": reject_reason,
            "compliance_mode": compliance.mode,
            "compliance_risk_level": compliance.risk_level,
            "compliance_reasons": compliance.reasons,
            "decision_logic": "rules-v2",
        }

        opp = Opportunity(
            source_item_id=source_item.id,
            market_item_id=market.id,
            match_score=match.score,
            accessory_score=accessory.score,
            decision=decision,
            decision_trace=json.dumps(trace, ensure_ascii=False),
            expected_profit_jpy=profit.expected_profit_jpy,
            expected_margin_rate=profit.expected_margin_rate,
            storage_score=profit.storage_score,
            shipping_score=profit.shipping_score,
            rule_version="rules-v2",
        )
        db.add(opp)
        opportunities.append(opp)

    db.commit()
    for opp in opportunities:
        db.refresh(opp)

    return opportunities


def _narrow_candidates_by_model(source_item: SourceItem, candidates: list[MarketItem]) -> list[MarketItem]:
    source_model_key = normalize_model_key(source_item.model_number)
    if not source_model_key or not candidates:
        return candidates

    strict: list[MarketItem] = []
    loose: list[MarketItem] = []
    for item in candidates:
        market_model_key = normalize_model_key(item.model_number)
        if market_model_key and market_model_key == source_model_key:
            strict.append(item)
            continue
        if title_contains_model(item.title, source_item.model_number):
            loose.append(item)

    if strict:
        return strict
    if loose:
        return loose
    return candidates


def _resolve_runtime_thresholds(
    source_item: SourceItem,
    overrides: dict[str, float],
) -> RuntimeThresholds:
    settings = get_settings()
    min_margin_rate = resolve_min_margin_rate(source_item.category, settings)

    min_auto_accept_score = _clamp_float(overrides.get("min_auto_accept_score"), settings.min_auto_accept_score, 0.0, 1.0)
    min_human_review_score = _clamp_float(overrides.get("min_human_review_score"), settings.min_human_review_score, 0.0, 1.0)
    min_title_similarity_auto_accept = _clamp_float(
        overrides.get("min_title_similarity_auto_accept"),
        settings.min_title_similarity_auto_accept,
        0.0,
        1.0,
    )
    min_title_similarity_human_review = _clamp_float(
        overrides.get("min_title_similarity_human_review"),
        settings.min_title_similarity_human_review,
        0.0,
        1.0,
    )
    min_expected_profit_jpy = _clamp_float(
        overrides.get("min_expected_profit_jpy"),
        settings.min_expected_profit_jpy,
        -1000000.0,
        100000000.0,
    )
    min_margin_rate = _clamp_float(overrides.get("min_expected_margin_rate"), min_margin_rate, 0.0, 1.0)
    accessory_reject_score = _clamp_float(overrides.get("accessory_reject_score"), settings.accessory_reject_score, 0.0, 1.0)

    # Keep ordering consistent even when user enters inverted thresholds.
    min_auto_accept_score = max(min_auto_accept_score, min_human_review_score)
    min_title_similarity_auto_accept = max(min_title_similarity_auto_accept, min_title_similarity_human_review)

    return RuntimeThresholds(
        min_auto_accept_score=min_auto_accept_score,
        min_human_review_score=min_human_review_score,
        min_title_similarity_auto_accept=min_title_similarity_auto_accept,
        min_title_similarity_human_review=min_title_similarity_human_review,
        min_expected_profit_jpy=min_expected_profit_jpy,
        min_margin_rate=min_margin_rate,
        accessory_reject_score=accessory_reject_score,
    )


def _clamp_float(value: float | None, fallback: float, lower: float, upper: float) -> float:
    if value is None:
        return float(fallback)
    return max(lower, min(float(value), upper))
