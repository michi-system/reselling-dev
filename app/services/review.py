from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Opportunity, ReviewDecision


def get_review_queue(db: Session, limit: int = 100) -> list[Opportunity]:
    reviewed_subquery = select(ReviewDecision.opportunity_id)
    stmt = (
        select(Opportunity)
        .where(Opportunity.decision == "human_review")
        .where(~Opportunity.id.in_(reviewed_subquery))
        .order_by(Opportunity.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def submit_review_decision(
    db: Session,
    opportunity_id: int,
    outcome: str,
    reviewer: str,
    note: str,
) -> ReviewDecision:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise ValueError("opportunity_not_found")

    existing = db.scalar(select(ReviewDecision).where(ReviewDecision.opportunity_id == opportunity_id))
    if existing:
        raise ValueError("already_reviewed")

    decision = ReviewDecision(
        opportunity_id=opportunity_id,
        outcome=outcome,
        reviewer=reviewer,
        note=note,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision
