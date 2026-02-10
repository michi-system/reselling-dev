from app.services.condition_infer import condition_gate_reason, infer_condition, resolve_condition


def test_infer_condition_from_keywords() -> None:
    assert infer_condition("【中古】SONY WF-1000XM5 ランクB") == "used"
    assert infer_condition("新品未開封 SONY WF-1000XM5") == "new"
    assert infer_condition("SONY WF-1000XM5") == "unknown"


def test_resolve_condition_prefers_explicit_value() -> None:
    assert resolve_condition("Used", "Brand New item") == "used"
    assert resolve_condition("", "新品 未使用") == "new"


def test_condition_gate_reason() -> None:
    assert condition_gate_reason("new", "used", "any") == "condition_pair_mismatch"
    assert condition_gate_reason("used", "used", "new") == "source_condition_filter_mismatch"
    assert condition_gate_reason("new", "used", "new") == "market_condition_filter_mismatch"
    assert condition_gate_reason("new", "new", "new") == ""
