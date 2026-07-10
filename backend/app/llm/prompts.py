"""Prompt templates for Groq.

Each function returns the user-facing prompt for a specific tool. The Groq
client adds the shared system instruction (structured JSON, never invent data).
"""
from __future__ import annotations

from datetime import datetime

from app.schemas import InteractionState

LOG_SCHEMA_HINT = (
    "Return JSON with these exact keys: "
    "hcpName, interactionType, date, time, attendees (array), "
    "topicsDiscussed, materialsShared (array), samplesDistributed (array of "
    "{productName, quantity, batchNumber}), sentiment, outcomes, "
    "followUpActions (array)."
)


def _today() -> str:
    """Current local date as YYYY-MM-DD, used wherever 'today' is mentioned."""
    return datetime.now().strftime("%Y-%m-%d")


def log_interaction_prompt(message: str) -> str:
    return (
        "Extract a healthcare-professional interaction from the description.\n"
        "Return a SINGLE JSON object (not an array) with EXACTLY these keys:\n"
        "{\n"
        '  "hcpName": string,\n'
        '  "interactionType": string,   // one of Meeting, Call, Email, Field Visit\n'
        f'  "date": string,              // YYYY-MM-DD; if the user says "today" use {_today()}\n'
        '  "time": string,\n'
        '  "attendees": [string],\n'
        '  "topicsDiscussed": string,\n'
        '  "materialsShared": [string],\n'
        '  "samplesDistributed": [{"productName": string, "quantity": int, "batchNumber": string}],\n'
        '  "sentiment": string,         // Positive | Neutral | Negative | Unknown\n'
        '  "outcomes": string,\n'
        '  "followUpActions": [string]\n'
        "}\n"
        "Do NOT wrap it in another object or array. Do not use markdown. "
        "Do not invent missing information; use empty string/array if absent.\n\n"
        f"Description: {message}"
    )


def edit_interaction_prompt(message: str, current: InteractionState) -> str:
    cur = current.model_dump(mode="json")
    return (
        f"Today's date is {_today()}. "
        "Update an existing interaction based on the user's edit request. "
        "Return a JSON PATCH containing ONLY the fields the user asked to change. "
        "Do not repeat unchanged fields. If the user refers to 'today', use "
        f"{_today()} as the date.\n\n"
        "FIELD ROUTING (important):\n"
        "- A product/topic rename (e.g. 'change CardioX to NeuroX') goes in "
        "`topicsDiscussed` — change ONLY that token, keep the rest of the text.\n"
        "- A new note, request, or outcome the user asks to 'mention', 'record', "
        "'note', or says they 'requested'/'asked' goes in the `outcomes` field, "
        "NOT in topicsDiscussed.\n"
        "- Apply EVERY change the user requested; do not silently drop any.\n\n"
        f"Current interaction: {cur}\n\n"
        f"Edit request: {message}\n\n"
        "Keys you may include: hcpName, interactionType, date, time, attendees, "
        "topicsDiscussed, materialsShared, samplesDistributed, sentiment, "
        "outcomes, followUpActions."
    )


def follow_up_prompt(state: InteractionState) -> str:
    cur = state.model_dump(mode="json")
    return (
        "Given this interaction, suggest 2-3 next best follow-up actions for a "
        "field representative. Return JSON: {\"suggestedFollowUps\": [..]}. "
        "Do not invent approved material names that were not discussed.\n\n"
        f"Interaction: {cur}"
    )


def material_recommendation_prompt(topics: str) -> str:
    return (
        "Recommend approved CRM materials for a rep to share, based ONLY on these "
        "discussed topics. Return JSON: {\"materials\": [..]}. "
        "Allowed materials: Clinical study brochure, Safety profile PDF, Product "
        "detail aid, Patient subgroup analysis, Dosing guide. "
        "Do not invent non-approved content.\n\n"
        f"Topics discussed: {topics}"
    )


def schedule_followup_prompt(message: str) -> str:
    return (
        "Extract a follow-up action to SCHEDULE from the request.\n"
        "Return a SINGLE JSON object with EXACTLY these keys:\n"
        "{\n"
        '  "action_text": string,   // what to do, e.g. "Call Dr. Sharma about trial enrollment"\n'
        '  "due_date": string,      // YYYY-MM-DD; convert relative dates using the date below\n'
        '  "due_time": string       // HH:MM 24h (e.g. "11:00") or empty string if none\n'
        "}\n"
        "Do NOT wrap in an array. Do not use markdown. If no specific date is given, "
        "leave due_date empty.\n\n"
        f"Today is {_today()}.\n\n"
        f"Request: {message}"
    )


def insights_prompt(interactions_text: str, name_hint: str | None) -> str:
    return (
        "You are analyzing CRM interaction records for a pharmaceutical field "
        "representative. Based ONLY on the interactions below, produce a JSON "
        "object with EXACTLY these keys:\n"
        "{\n"
        '  "summary": string,               // 1-2 sentence overview of all interactions\n'
        '  "overallSentiment": string,      // Positive | Neutral | Negative | Mixed\n'
        '  "productsDiscussed": [string],   // product names mentioned\n'
        '  "keyConcerns": [string],         // physician concerns, objections, or requests\n'
        '  "recommendedNextAction": string  // single best next step for the rep\n'
        "}\n"
        "Do not use markdown. Do not invent products or concerns not present.\n\n"
        f"HCP: {name_hint or 'all HCPs'}\n\n"
        f"Interactions:\n{interactions_text}"
    )
