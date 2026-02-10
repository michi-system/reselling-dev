from dataclasses import dataclass, field

from app.db.models import MarketItem, SourceItem
from app.services.normalizer import jaccard_similarity, normalize_text, tokenize


@dataclass
class MatchResult:
    score: float
    title_similarity: float
    reasons: list[str] = field(default_factory=list)


def score_match(source: SourceItem, market: MarketItem) -> MatchResult:
    score = 0.0
    reasons: list[str] = []
    source_title = normalize_text(source.title)
    market_title = normalize_text(market.title)

    if source.jan and market.gtin and source.jan == market.gtin:
        score += 0.70
        reasons.append("jan_gtin_exact")

    if source.model_number and market.model_number:
        normalized_source_model = normalize_text(source.model_number)
        normalized_market_model = normalize_text(market.model_number)
        if normalized_source_model == normalized_market_model:
            score += 0.50
            reasons.append("model_exact")
        elif normalized_source_model in market_title:
            score += 0.30
            reasons.append("model_in_title")
        else:
            score -= 0.05
            reasons.append("model_mismatch_penalty")

    if source.brand and market.brand and normalize_text(source.brand) == normalize_text(market.brand):
        score += 0.15
        reasons.append("brand_exact")

    title_sim = jaccard_similarity(tokenize(source_title), tokenize(market_title))
    score += min(0.35, title_sim * 0.50)
    reasons.append(f"title_sim:{title_sim:.2f}")

    if source.model_number and normalize_text(source.model_number) not in market_title:
        model_fragments = [t for t in tokenize(source.model_number) if len(t) >= 3]
        if model_fragments and not any(token in market_title for token in model_fragments):
            score -= 0.08
            reasons.append("model_fragment_missing_penalty")

    if source.condition and market.condition and source.condition != "unknown":
        if normalize_text(source.condition) == normalize_text(market.condition):
            score += 0.10
            reasons.append("condition_exact")
        elif normalize_text(source.condition) == "new" and normalize_text(market.condition) != "new":
            score -= 0.20
            reasons.append("condition_mismatch_penalty")

    score = max(0.0, min(1.0, score))
    return MatchResult(score=score, title_similarity=title_sim, reasons=reasons)
