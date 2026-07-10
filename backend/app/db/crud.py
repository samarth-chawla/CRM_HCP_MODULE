"""Persistence helpers: save / get / patch interactions, HCP search, audit log.

The audit log captures every AI-driven change:
user prompt, tool called, previous state, new state, model used, timestamp.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import models
from app.schemas import InteractionState


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


# ---- Interactions -----------------------------------------------------------

def save_interaction(db: Session, state: InteractionState, user_id: str | None = None) -> str:
    interaction_id = _new_id("INT")
    rec = models.Interaction(
        id=interaction_id,
        hcp_id=state.hcpId,
        hcp_name=state.hcpName,
        interaction_type=state.interactionType,
        interaction_date=state.date,
        interaction_time=state.time,
        topics_discussed=state.topicsDiscussed,
        sentiment=state.sentiment,
        outcomes=state.outcomes,
        created_by=user_id,
    )
    db.add(rec)
    db.flush()

    for a in state.attendees:
        db.add(models.InteractionAttendee(interaction_id=interaction_id, name=a))
    for m in state.materialsShared:
        db.add(models.InteractionMaterial(interaction_id=interaction_id, material_name=m))
    for s in state.samplesDistributed:
        if isinstance(s, dict):
            db.add(
                models.InteractionSample(
                    interaction_id=interaction_id,
                    product_name=s.get("productName", ""),
                    quantity=int(s.get("quantity", 1)),
                    batch_number=s.get("batchNumber", ""),
                )
            )
        else:
            db.add(models.InteractionSample(interaction_id=interaction_id, product_name=str(s)))
    for f in state.followUpActions:
        db.add(models.FollowUpAction(interaction_id=interaction_id, action_text=f))

    db.commit()
    return interaction_id


def get_interaction(db: Session, interaction_id: str) -> Optional[InteractionState]:
    rec = db.get(models.Interaction, interaction_id)
    if not rec:
        return None
    return _to_state(rec)


def patch_interaction(db: Session, interaction_id: str, patch: dict) -> Optional[InteractionState]:
    rec = db.get(models.Interaction, interaction_id)
    if not rec:
        return None
    for key, val in patch.items():
        if key in ("interactionType", "interaction_type"):
            rec.interaction_type = patch[key]
        elif key in ("date", "interaction_date"):
            rec.interaction_date = patch[key]
        elif key in ("time", "interaction_time"):
            rec.interaction_time = patch[key]
        elif key in ("topicsDiscussed", "topics_discussed"):
            rec.topics_discussed = patch[key]
        elif key in ("sentiment",):
            rec.sentiment = patch[key]
        elif key in ("outcomes",):
            rec.outcomes = patch[key]
    db.commit()
    return _to_state(rec)


def _to_state(rec: models.Interaction) -> InteractionState:
    return InteractionState(
        hcpId=rec.hcp_id,
        hcpName=rec.hcp_name or (rec.hcp.name if rec.hcp else ""),
        interactionType=rec.interaction_type,
        date=rec.interaction_date,
        time=rec.interaction_time,
        attendees=[a.name for a in rec.attendees],
        topicsDiscussed=rec.topics_discussed,
        materialsShared=[m.material_name for m in rec.materials],
        samplesDistributed=[
            {"productName": s.product_name, "quantity": s.quantity, "batchNumber": s.batch_number}
            for s in rec.samples
        ],
        sentiment=rec.sentiment,  # type: ignore[arg-type]
        outcomes=rec.outcomes,
        followUpActions=[f.action_text for f in rec.follow_ups],
    )


# ---- HCP search --------------------------------------------------------------

def search_hcps(db: Session, query: str, limit: int = 10) -> list[models.HCP]:
    if not query:
        return db.query(models.HCP).limit(limit).all()
    like = f"%{query}%"
    return (
        db.query(models.HCP)
        .filter(or_(models.HCP.name.ilike(like), models.HCP.specialty.ilike(like)))
        .limit(limit)
        .all()
    )


def get_hcp_by_name(db: Session, name: str) -> Optional[models.HCP]:
    return db.query(models.HCP).filter(models.HCP.name.ilike(f"%{name}%")).first()


def list_interactions(db: Session, name: str | None = None, limit: int = 20) -> list[models.Interaction]:
    """Return interactions, most recent first. Filter by HCP name when given."""
    q = db.query(models.Interaction)
    if name:
        q = q.filter(models.Interaction.hcp_name.ilike(f"%{name}%"))
    return q.order_by(models.Interaction.created_at.desc()).limit(limit).all()


# ---- Audit --------------------------------------------------------------------

def write_audit(
    db: Session,
    *,
    interaction_id: str | None,
    user_id: str | None,
    user_prompt: str,
    tool_called: str,
    previous_state: InteractionState | dict,
    new_state: InteractionState | dict,
    model_used: str,
) -> None:
    def dump(x):
        return json.dumps(x, default=str)

    db.add(
        models.AuditLog(
            interaction_id=interaction_id,
            user_id=user_id,
            user_prompt=user_prompt,
            tool_called=tool_called,
            previous_state=dump(previous_state),
            new_state=dump(new_state),
            model_used=model_used,
        )
    )
    db.commit()
