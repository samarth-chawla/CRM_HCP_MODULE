"""Pydantic schemas for request/response validation.

The `InteractionState` model mirrors the Redux `interactionSlice` shape so the
backend and frontend speak the same JSON contract.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Sentiment = Literal["Positive", "Neutral", "Negative", "Unknown"]


class SampleItem(BaseModel):
    productName: str
    quantity: int = 1
    batchNumber: str = ""


class InteractionState(BaseModel):
    hcpId: Optional[str] = None
    hcpName: str = ""
    interactionType: str = ""
    date: str = ""
    time: str = ""
    attendees: list[str] = Field(default_factory=list)
    topicsDiscussed: str = ""
    materialsShared: list[str] = Field(default_factory=list)
    samplesDistributed: list[Any] = Field(default_factory=list)
    sentiment: Sentiment = "Unknown"
    outcomes: str = ""
    followUpActions: list[str] = Field(default_factory=list)
    suggestedFollowUps: list[str] = Field(default_factory=list)


# ---- Agent endpoint ----------------------------------------------------------

class AgentRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's natural language prompt")
    currentInteractionState: InteractionState = Field(
        default_factory=InteractionState,
        description="Current form state, used for edit/merge context",
    )


class AgentResponse(BaseModel):
    assistantMessage: str
    updatedInteractionState: InteractionState
    toolCalls: list[str] = Field(default_factory=list)
    suggestedFollowUps: list[str] = Field(default_factory=list)
    intent: str = ""
    selectedTool: str = ""
    errors: list[str] = Field(default_factory=list)


# ---- Save endpoint -----------------------------------------------------------

class SaveRequest(BaseModel):
    interaction: InteractionState


class SaveResponse(BaseModel):
    interactionId: str
    status: str = "saved"
    warnings: list[str] = Field(default_factory=list)


# ---- HCP lookup --------------------------------------------------------------

class HCPProfile(BaseModel):
    id: str
    name: str
    specialty: str = ""
    territory: str = ""
    preferred_channel: str = ""
    previous_product_interest: str = ""
    compliance_restrictions: str = ""


class HcpSearchResponse(BaseModel):
    results: list[HCPProfile] = Field(default_factory=list)
