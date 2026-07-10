"""FastAPI application for the AI-First CRM HCP module.

Endpoints
    POST /api/interaction/agent   – run a prompt through LangGraph
    POST /api/interaction/save    – persist a finalized interaction + audit log
    GET  /api/interaction/{id}    – fetch a saved interaction
    PATCH /api/interaction/{id}   – update a saved interaction
    GET  /api/hcps/search         – search HCP profiles
"""
from __future__ import annotations

import re

# pyrefly: ignore [missing-import]
from fastapi import Depends, FastAPI, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.agent import graph as agent_graph
from app.config import settings
from app.db import crud
from app.db.session import get_db, init_db
from app.schemas import (
    AgentRequest,
    AgentResponse,
    HcpSearchResponse,
    HCPProfile,
    SaveRequest,
    SaveResponse,
    InteractionState,
)

app = FastAPI(title="AI-First CRM HCP Module", version="1.0.0")

# CORS policy:
#   - Development: accept any localhost / 127.0.0.1 origin on any port, so the
#     Vite dev server and the API can run on whatever ports they start on
#     without CORS surprises.
#   - Production: only the explicitly configured origins are allowed.
_DEV_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

_cors = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.app_env == "development":
    _cors["allow_origin_regex"] = _DEV_ORIGIN_REGEX
else:
    _cors["allow_origins"] = [
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(CORSMiddleware, **_cors)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": settings.groq_model, "groq": settings.has_groq}


@app.post("/api/interaction/agent", response_model=AgentResponse)
def interaction_agent(req: AgentRequest, db: Session = Depends(get_db)) -> AgentResponse:
    """Process a chat prompt through the LangGraph agent."""
    if not req.message.strip():
        raise HTTPException(status_code=422, detail="message must not be empty")
    try:
        result = agent_graph.run_agent(req.message, req.currentInteractionState, db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent failed: {exc}") from exc

    # Audit the AI-driven change.
    crud.write_audit(
        db,
        interaction_id=None,
        user_id=None,
        user_prompt=req.message,
        tool_called=result.selectedTool,
        previous_state=req.currentInteractionState.model_dump(mode="json"),
        new_state=result.updatedInteractionState.model_dump(mode="json"),
        model_used=settings.groq_model,
    )
    return result


@app.post("/api/interaction/save", response_model=SaveResponse)
def save_interaction(req: SaveRequest, db: Session = Depends(get_db)) -> SaveResponse:
    """Persist the finalized interaction."""
    state = req.interaction
    missing = [f for f in ("hcpName", "interactionType", "date", "topicsDiscussed")
               if not getattr(state, f)]
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Missing required fields: {', '.join(missing)}"
        )
    try:
        interaction_id = crud.save_interaction(db, state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Save failed: {exc}") from exc

    crud.write_audit(
        db,
        interaction_id=interaction_id,
        user_id=None,
        user_prompt="(save)",
        tool_called="interaction.save",
        previous_state={},
        new_state=state.model_dump(mode="json"),
        model_used=settings.groq_model,
    )
    return SaveResponse(interactionId=interaction_id, status="saved")


@app.get("/api/interaction/{interaction_id}", response_model=InteractionState)
def get_interaction(interaction_id: str, db: Session = Depends(get_db)) -> InteractionState:
    state = crud.get_interaction(db, interaction_id)
    if not state:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return state


@app.patch("/api/interaction/{interaction_id}", response_model=InteractionState)
def patch_interaction(
    interaction_id: str, patch: dict, db: Session = Depends(get_db)
) -> InteractionState:
    state = crud.patch_interaction(db, interaction_id, patch)
    if not state:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return state


@app.get("/api/hcps/search", response_model=HcpSearchResponse)
def hcp_search(q: str = "", db: Session = Depends(get_db)) -> HcpSearchResponse:
    rows = crud.search_hcps(db, q)
    return HcpSearchResponse(
        results=[
            HCPProfile(
                id=r.id,
                name=r.name,
                specialty=r.specialty,
                territory=r.territory,
                preferred_channel=r.preferred_channel,
                previous_product_interest=r.previous_product_interest,
                compliance_restrictions=r.compliance_restrictions,
            )
            for r in rows
        ]
    )
