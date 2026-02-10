from __future__ import annotations

import re

_CANDIDATE_TOKEN = re.compile(r"[A-Za-z0-9-]{4,24}")
_SEP_PATTERN = re.compile(r"[^A-Za-z0-9]+")


def extract_model_number(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""

    candidates: list[str] = []
    for token in _CANDIDATE_TOKEN.findall(raw):
        cleaned = token.strip("-")
        if not cleaned:
            continue
        if not _has_alpha_and_digit(cleaned):
            continue
        if cleaned.isdigit():
            continue
        if len(cleaned) < 4:
            continue
        candidates.append(cleaned.upper())

    if not candidates:
        return ""

    def score(value: str) -> tuple[int, int]:
        has_hyphen = 1 if "-" in value else 0
        alpha_num_len = len(normalize_model_key(value))
        return (has_hyphen, alpha_num_len)

    candidates.sort(key=score, reverse=True)
    return candidates[0]


def normalize_model_key(value: str) -> str:
    return _SEP_PATTERN.sub("", (value or "").upper())


def title_contains_model(title: str, model: str) -> bool:
    model_key = normalize_model_key(model)
    if not model_key:
        return False
    title_key = normalize_model_key(title)
    return model_key in title_key


def _has_alpha_and_digit(value: str) -> bool:
    has_alpha = any(ch.isalpha() for ch in value)
    has_digit = any(ch.isdigit() for ch in value)
    return has_alpha and has_digit
