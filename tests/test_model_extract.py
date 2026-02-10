from app.services.model_extract import extract_model_number, normalize_model_key, title_contains_model


def test_extract_model_number_prefers_alnum_with_hyphen() -> None:
    title = "Sony WF-1000XM5 Wireless Earbuds Noise Canceling Black"
    assert extract_model_number(title) == "WF-1000XM5"


def test_extract_model_number_returns_empty_for_plain_words() -> None:
    assert extract_model_number("Sony wireless earbuds black") == ""


def test_title_contains_model_matches_with_or_without_separators() -> None:
    assert title_contains_model("SONY WF1000XM5 replacement case", "WF-1000XM5")
    assert normalize_model_key("WF-1000XM5") == "WF1000XM5"
