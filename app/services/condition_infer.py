from __future__ import annotations

import re

ConditionValue = str

_NEW_KEYWORDS = (
    "新品",
    "未使用",
    "未開封",
    "new",
    "brand new",
    "new in box",
    "new with box",
    "new with tags",
    "sealed",
)

_USED_KEYWORDS = (
    "中古",
    "ユーズド",
    "used",
    "pre-owned",
    "pre owned",
    "second hand",
    "open box",
    "open-box",
    "refurbished",
    "for parts",
    "junk",
    "ジャンク",
    "訳あり",
    "難あり",
)

_RANK_PATTERN = re.compile(r"(?:ランク|grade)\s*[sabcd]", flags=re.IGNORECASE)


def normalize_requested_condition(value: str | None) -> ConditionValue:
    raw = (value or "").strip().lower()
    if raw in {"new", "used", "any"}:
        return raw
    return "any"


def infer_condition(*texts: str) -> ConditionValue:
    merged = " ".join(_normalize_text(text) for text in texts if str(text or "").strip())
    if not merged:
        return "unknown"

    new_hits = _count_keyword_hits(merged, _NEW_KEYWORDS)
    used_hits = _count_keyword_hits(merged, _USED_KEYWORDS)
    if _RANK_PATTERN.search(merged):
        used_hits += 1

    if new_hits == 0 and used_hits == 0:
        return "unknown"
    if used_hits >= new_hits:
        return "used"
    return "new"


def resolve_condition(raw_condition: str | None, *text_hints: str) -> ConditionValue:
    explicit = _normalize_explicit_condition(raw_condition)
    inferred = infer_condition(raw_condition or "", *text_hints)
    if explicit != "unknown":
        return explicit
    return inferred


def condition_gate_reason(
    source_condition: str,
    market_condition: str,
    requested_condition: str,
) -> str:
    source = _normalize_explicit_condition(source_condition)
    market = _normalize_explicit_condition(market_condition)
    requested = normalize_requested_condition(requested_condition)

    if requested in {"new", "used"}:
        if source != requested:
            return "source_condition_filter_mismatch"
        if market != requested:
            return "market_condition_filter_mismatch"
        return ""

    if source in {"new", "used"} and market in {"new", "used"} and source != market:
        return "condition_pair_mismatch"
    return ""


def _normalize_explicit_condition(value: str | None) -> ConditionValue:
    raw = _normalize_text(value or "")
    if not raw:
        return "unknown"
    if any(keyword in raw for keyword in _USED_KEYWORDS):
        return "used"
    if _RANK_PATTERN.search(raw):
        return "used"
    if any(keyword in raw for keyword in _NEW_KEYWORDS):
        return "new"
    if raw in {"new", "new_other", "new other"}:
        return "new"
    if raw in {"used", "pre_owned", "pre-owned", "refurbished"}:
        return "used"
    return "unknown"


def _normalize_text(value: str) -> str:
    return str(value or "").strip().lower().replace("_", " ")


def _count_keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)
