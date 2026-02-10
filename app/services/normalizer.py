import re
from collections.abc import Iterable

TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


STOPWORDS = {
    "the",
    "and",
    "with",
    "for",
    "new",
    "used",
    "japan",
    "official",
    "edition",
}


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str) -> set[str]:
    tokens = {t.lower() for t in TOKEN_PATTERN.findall(text)}
    return {t for t in tokens if t not in STOPWORDS}


def jaccard_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union
