from __future__ import annotations

import json
from collections import Counter

from sqlalchemy.orm import Session

from app.db.models import Opportunity


def summarize_reject_reasons(db: Session, limit: int = 1000) -> tuple[int, list[tuple[str, int]]]:
    opportunities = (
        db.query(Opportunity)
        .filter(Opportunity.decision == "reject")
        .order_by(Opportunity.id.desc())
        .limit(limit)
        .all()
    )

    counter: Counter[str] = Counter()
    for opp in opportunities:
        reason = _extract_reject_reason(opp.decision_trace)
        counter[reason] += 1

    return len(opportunities), counter.most_common()


def summarize_compliance_reasons(db: Session, limit: int = 1000) -> tuple[int, list[tuple[str, int]]]:
    opportunities = db.query(Opportunity).order_by(Opportunity.id.desc()).limit(limit).all()
    counter: Counter[str] = Counter()
    flagged = 0
    for opp in opportunities:
        reasons = _extract_compliance_reasons(opp.decision_trace)
        if reasons:
            flagged += 1
            for reason in reasons:
                counter[reason] += 1

    return flagged, counter.most_common()


def _extract_reject_reason(decision_trace: str) -> str:
    try:
        trace = json.loads(decision_trace)
    except json.JSONDecodeError:
        return "trace_parse_error"

    reason = str(trace.get("reject_reason", ""))
    if reason:
        return reason

    accessory_reasons = trace.get("accessory_reasons")
    if isinstance(accessory_reasons, list) and accessory_reasons:
        return "accessory_rule"

    return "unknown"


def _extract_compliance_reasons(decision_trace: str) -> list[str]:
    try:
        trace = json.loads(decision_trace)
    except json.JSONDecodeError:
        return ["trace_parse_error"]

    reasons = trace.get("compliance_reasons", [])
    if isinstance(reasons, list):
        return [str(item) for item in reasons if str(item)]
    return []
