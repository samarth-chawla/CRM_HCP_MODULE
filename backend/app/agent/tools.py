"""LangGraph tools for the HCP interaction agent.

Five tools are implemented (the spec requires a minimum of five):
  1. log_interaction        – parse NL into a structured record (uses Groq)
  2. edit_interaction       – patch only requested fields (uses Groq)
  3. hcp_profile_lookup     – enrich HCP details from the CRM
  4. material_recommendation– suggest approved materials by topic
  5. follow_up_suggestion   – recommend next best actions

Each tool returns a dict the agent merges into the LangGraph state:
  { updatedInteractionState, assistantMessage, suggestedFollowUps, toolCalls }
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.db import crud, models
from app.llm import groq_client
from app.llm.prompts import (
    edit_interaction_prompt,
    follow_up_prompt,
    insights_prompt,
    log_interaction_prompt,
    material_recommendation_prompt,
    schedule_followup_prompt,
)
from app.schemas import InteractionState, SampleItem


# ---------------------------------------------------------------------------
# Tool 1 — Log Interaction
# ---------------------------------------------------------------------------

def log_interaction(message: str, current: InteractionState, db, llm) -> dict:
    prompt = log_interaction_prompt(message)
    data = llm.complete_json(prompt)
    state = _merge_log(current, data)
    tool_calls = ["log_interaction"]

    follow = follow_up_suggestion(message, state, db, llm)
    suggested = follow.get("suggestedFollowUps", [])
    state.suggestedFollowUps = suggested

    assistant = (
        f"I logged the interaction with {state.hcpName or 'the HCP'}. "
        f"Type: {state.interactionType or 'n/a'}, sentiment: {state.sentiment}. "
        "The form on the left is now populated."
    )
    return {
        "updatedInteractionState": state,
        "assistantMessage": assistant,
        "suggestedFollowUps": suggested,
        "toolCalls": tool_calls,
    }


def _merge_log(current: InteractionState, data: dict) -> InteractionState:
    def arr(v):
        if v is None:
            return []
        return v if isinstance(v, list) else [v]

    samples = []
    for s in arr(data.get("samplesDistributed")):
        if isinstance(s, dict):
            samples.append(SampleItem(**_coerce_sample(s)).model_dump())
        elif isinstance(s, str):
            samples.append({"productName": s, "quantity": 1, "batchNumber": ""})

    return InteractionState(
        hcpId=current.hcpId,
        hcpName=_str(data.get("hcpName")) or current.hcpName,
        interactionType=_str(data.get("interactionType")) or "Meeting",
        date=_str(data.get("date")) or current.date,
        time=_str(data.get("time")) or current.time,
        attendees=arr(data.get("attendees")) or current.attendees,
        topicsDiscussed=_str(data.get("topicsDiscussed")) or current.topicsDiscussed,
        materialsShared=arr(data.get("materialsShared")) or current.materialsShared,
        samplesDistributed=samples or current.samplesDistributed,
        sentiment=_sentiment(data.get("sentiment")) or current.sentiment,
        outcomes=_str(data.get("outcomes")) or current.outcomes,
        followUpActions=arr(data.get("followUpActions")) or current.followUpActions,
    )


# ---------------------------------------------------------------------------
# Tool 2 — Edit Interaction
# ---------------------------------------------------------------------------

def edit_interaction(message: str, current: InteractionState, db, llm) -> dict:
    prompt = edit_interaction_prompt(message, current)
    patch = llm.complete_json(prompt)
    patch.pop("toolCalls", None)
    patch.pop("_raw", None)
    patch = merge_edit_patch(patch, message)

    updated = current.model_copy(deep=True)
    changed = []
    for key, val in patch.items():
        if key == "samplesDistributed":
            val = [
                SampleItem(**_coerce_sample(s)).model_dump() if isinstance(s, dict) else s
                for s in (val if isinstance(val, list) else [val])
            ]
        if key == "sentiment":
            val = _sentiment(val)
        setattr(updated, key, val)
        changed.append(key)

    assistant = (
        "I updated "
        + (", ".join(changed) if changed else "nothing")
        + ". All other fields are unchanged."
    )
    return {
        "updatedInteractionState": updated,
        "assistantMessage": assistant,
        "suggestedFollowUps": updated.suggestedFollowUps,
        "toolCalls": ["edit_interaction"],
    }


# ---------------------------------------------------------------------------
# Tool 3 — HCP Profile Lookup
# ---------------------------------------------------------------------------

def hcp_profile_lookup(message: str, current: InteractionState, db, llm) -> dict:
    name_hint = current.hcpName or _extract_name(message)
    hcp: models.HCP | None = crud.get_hcp_by_name(db, name_hint) if name_hint else None

    # NOTE: lookups are read-only. We intentionally do NOT auto-create an HCP
    # here — creating a record as a side effect of a "show/find" query pollutes
    # the CRM with blank duplicates. If the HCP isn't found, we just report it.

    updated = current.model_copy(deep=True)
    if hcp:
        updated.hcpId = hcp.id
        if not updated.hcpName:
            updated.hcpName = hcp.name

    detail = (
        f"{hcp.name} — {hcp.specialty or 'specialty n/a'}, territory "
        f"{hcp.territory or 'n/a'}. Preferred channel: "
        f"{hcp.preferred_channel or 'n/a'}. Previous interest: "
        f"{hcp.previous_product_interest or 'n/a'}. "
        f"Compliance restrictions: {hcp.compliance_restrictions or 'none'}."
        if hcp
        else "No matching HCP found in the CRM."
    )
    return {
        "updatedInteractionState": updated,
        "assistantMessage": f"HCP profile lookup: {detail}",
        "suggestedFollowUps": updated.suggestedFollowUps,
        "toolCalls": ["hcp_profile_lookup"],
    }


# ---------------------------------------------------------------------------
# Tool 4 — Material Recommendation
# ---------------------------------------------------------------------------

APPROVED = {
    "clinical study brochure",
    "safety profile pdf",
    "product detail aid",
    "patient subgroup analysis",
    "dosing guide",
}


def material_recommendation(message: str, current: InteractionState, db, llm) -> dict:
    topics = current.topicsDiscussed or message
    # Use complete_json_raw: complete_json normalizes to the interaction-log
    # schema and would rename `materials` -> `materialsShared`, dropping it.
    data = llm.complete_json_raw(material_recommendation_prompt(topics))
    raw = data.get("materials", []) if isinstance(data, dict) else []
    approved = [m for m in (raw or []) if _norm(m) in APPROVED]

    updated = current.model_copy(deep=True)
    for m in approved:
        if m not in updated.materialsShared:
            updated.materialsShared = [*updated.materialsShared, m]

    assistant = (
        "Recommended approved materials: "
        + (", ".join(approved) if approved else "none applicable")
        + ". I added them to Materials Shared."
    )
    return {
        "updatedInteractionState": updated,
        "assistantMessage": assistant,
        "suggestedFollowUps": updated.suggestedFollowUps,
        "toolCalls": ["material_recommendation"],
    }


# ---------------------------------------------------------------------------
# Tool 5 — Follow-Up Suggestion
# ---------------------------------------------------------------------------

def follow_up_suggestion(message: str, current: InteractionState, db, llm) -> dict:
    # Use complete_json_raw: complete_json normalizes to the interaction-log
    # schema, which drops the `suggestedFollowUps` key entirely.
    data = llm.complete_json_raw(follow_up_prompt(current))
    sugg = data.get("suggestedFollowUps", []) if isinstance(data, dict) else []
    sugg = [s for s in (sugg or []) if isinstance(s, str)]

    updated = current.model_copy(deep=True)
    updated.suggestedFollowUps = sugg

    return {
        "updatedInteractionState": updated,
        "assistantMessage": (
            "Suggested follow-ups: " + (", ".join(sugg) if sugg else "none")
        ),
        "suggestedFollowUps": sugg,
        "toolCalls": ["follow_up_suggestion"],
    }


# ---------------------------------------------------------------------------
# Tool 6 — Summarize Interactions (read-only)
# ---------------------------------------------------------------------------

def summarize_interactions(message: str, current: InteractionState, db, llm) -> dict:
    name_hint = current.hcpName or _extract_name(message)
    rows = crud.list_interactions(db, name_hint) if db is not None else []

    updated = current.model_copy(deep=True)
    if name_hint and not updated.hcpName:
        updated.hcpName = name_hint

    if not rows:
        msg = (
            "No interactions found"
            + (f" for {name_hint}" if name_hint else "")
            + " in the CRM yet."
        )
    else:
        today = datetime.now().date()
        lines = []
        prev = None
        for r in rows:
            base = " ".join(
                p for p in [
                    f"- {r.interaction_date or 'undated'}",
                    r.interaction_time or "",
                    f": {r.interaction_type or 'interaction'} with {r.hcp_name or 'HCP'}",
                ]
                if p
            ).strip()
            extras = []
            if r.sentiment and r.sentiment != "Unknown":
                extras.append(f"sentiment {r.sentiment}")
            if r.topics_discussed:
                extras.append(f"topics: {r.topics_discussed}")

            # Annotate relationships between interactions so duplicates / future
            # plans are called out instead of looking like independent visits.
            notes = []
            d = _parse_date(r.interaction_date)
            if d is not None and d.date() > today:
                notes.append("planned/future interaction")
            if prev is not None:
                r_topics = {t.strip().lower() for t in (r.topics_discussed or "").split(",") if t.strip()}
                p_topics = {t.strip().lower() for t in (prev.topics_discussed or "").split(",") if t.strip()}
                if r_topics and (r_topics & p_topics):
                    same_sent = (r.sentiment or "Unknown") != "Unknown" and r.sentiment == prev.sentiment
                    notes.append(
                        "similar to the previous interaction"
                        + (" (same sentiment)" if same_sent else "")
                    )
            if notes:
                extras.append("note: " + "; ".join(notes))

            if extras:
                base += " (" + "; ".join(extras) + ")"
            lines.append(base)
            prev = r
        msg = (
            f"Found {len(rows)} interaction(s)"
            + (f" for {name_hint}" if name_hint else "")
            + ":\n"
            + "\n".join(lines)
        )

    # If the user also asked for a next best action, generate one from the
    # interaction history. The router only dispatches the summarize tool here,
    # so the "suggest the next best action" half of the request is satisfied
    # within summarize itself.
    _ASK_NEXT = (
        "next best action", "next best step", "suggest", "follow-up", "follow up",
        "what next", "next step", "recommended action", "recommended next",
    )
    if rows and any(k in message.lower() for k in _ASK_NEXT):
        action = _next_best_action(rows, name_hint, llm)
        if action:
            msg += "\n\nSuggested next best action: " + action
            updated.suggestedFollowUps = [action]

    return {
        "updatedInteractionState": updated,
        "assistantMessage": msg,
        "suggestedFollowUps": updated.suggestedFollowUps,
        "toolCalls": ["summarize_interactions"],
    }


# ---------------------------------------------------------------------------
# Tool 7 — Schedule Follow-up (action)
# ---------------------------------------------------------------------------

def schedule_followup(message: str, current: InteractionState, db, llm) -> dict:
    name_hint = current.hcpName or _extract_name(message)

    if llm is not None:
        try:
            data = llm.complete_json_raw(schedule_followup_prompt(message))
        except Exception:
            data = {}
    else:
        data = {}

    if not data:
        data = _heuristic_schedule(message)

    action_text = _str(data.get("action_text")) or f"Follow-up with {name_hint or 'HCP'}"
    due_date = _str(data.get("due_date"))
    due_time = _str(data.get("due_time"))

    updated = current.model_copy(deep=True)
    if name_hint and name_hint not in action_text:
        action_text = f"{action_text} (with {name_hint})"

    # Store date + time together in the single due_date string column.
    stored_due = " ".join(p for p in [due_date, due_time] if p).strip() or None

    if db is not None:
        fu = models.FollowUpAction(
            interaction_id=None,
            action_text=action_text,
            due_date=stored_due,
            status="Open",
            owner_id=None,
        )
        db.add(fu)
        db.commit()
        db.refresh(fu)

    when = stored_due or ""
    msg = f"Scheduled follow-up: {action_text}" + (f" — due {when}" if when else "")
    return {
        "updatedInteractionState": updated,
        "assistantMessage": msg,
        "suggestedFollowUps": updated.suggestedFollowUps,
        "toolCalls": ["schedule_followup"],
    }


# ---------------------------------------------------------------------------
# Tool 8 — Generate Interaction Insights (analysis)
# ---------------------------------------------------------------------------

def generate_insights(message: str, current: InteractionState, db, llm) -> dict:
    name_hint = current.hcpName or _extract_name(message)
    rows = crud.list_interactions(db, name_hint) if db is not None else []

    updated = current.model_copy(deep=True)
    if name_hint and not updated.hcpName:
        updated.hcpName = name_hint

    if not rows:
        msg = (
            "No interactions found"
            + (f" for {name_hint}" if name_hint else "")
            + " to analyze yet."
        )
        return {
            "updatedInteractionState": updated,
            "assistantMessage": msg,
            "suggestedFollowUps": updated.suggestedFollowUps,
            "toolCalls": ["generate_insights"],
        }

    lines = []
    for r in rows:
        lines.append(
            f"- {r.interaction_date or 'undated'} {r.interaction_time or ''}: "
            f"{r.interaction_type or 'interaction'} with {r.hcp_name or 'HCP'}; "
            f"sentiment {r.sentiment or 'Unknown'}; "
            f"topics: {r.topics_discussed or 'n/a'}; "
            f"outcomes: {r.outcomes or 'n/a'}"
        )
    interactions_text = "\n".join(lines)

    if llm is not None:
        try:
            data = llm.complete_json_raw(insights_prompt(interactions_text, name_hint))
        except Exception:
            data = {}
    else:
        data = {}
    if not data:
        data = _heuristic_insights(rows, name_hint)

    summary = _str(data.get("summary"))
    sentiment = _str(data.get("overallSentiment") or data.get("overall_sentiment"))
    products = data.get("productsDiscussed") or data.get("products_discussed") or []
    if isinstance(products, str):
        products = [products]
    concerns = data.get("keyConcerns") or data.get("key_concerns") or []
    if isinstance(concerns, str):
        concerns = [concerns]
    next_action = _str(
        data.get("recommendedNextAction") or data.get("recommended_next_action")
    )

    msg = (
        f"Interaction insights{f' for {name_hint}' if name_hint else ''} "
        f"({len(rows)} interaction(s)):\n"
        f"• Summary: {summary}\n"
        f"• Overall sentiment: {sentiment or 'Unknown'}\n"
        f"• Products discussed: {', '.join(products) if products else 'none'}\n"
        f"• Key concerns: {', '.join(concerns) if concerns else 'none'}\n"
        f"• Recommended next best action: {next_action or 'none'}"
    )
    return {
        "updatedInteractionState": updated,
        "assistantMessage": msg,
        "suggestedFollowUps": updated.suggestedFollowUps,
        "toolCalls": ["generate_insights"],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip().lower())


def _parse_date(s: str) -> datetime | None:
    """Best-effort YYYY-MM-DD parse of an interaction date string."""
    if not s:
        return None
    head = s.strip().split(" ")[0].split("T")[0]
    try:
        return datetime.strptime(head, "%Y-%m-%d")
    except ValueError:
        return None


def _next_best_action(rows, name_hint, llm) -> str:
    """Derive a single next-best-action recommendation from interaction history.

    Used when a 'summarize' request also asks to 'suggest the next best action':
    the router only runs the summarize tool, so it must produce the suggestion
    itself rather than relying on a separate follow-up/suggestion tool.
    """
    lines = [
        f"- {r.interaction_date or 'undated'} {r.interaction_time or ''}: "
        f"{r.interaction_type or 'interaction'} with {r.hcp_name or 'HCP'}; "
        f"sentiment {r.sentiment or 'Unknown'}; topics: {r.topics_discussed or 'n/a'}"
        for r in rows
    ]
    text = "\n".join(lines)
    data: dict = {}
    if llm is not None:
        try:
            data = llm.complete_json_raw(insights_prompt(text, name_hint))
        except Exception:
            data = {}
    action = _str(data.get("recommendedNextAction") or data.get("recommended_next_action"))
    if not action:
        action = _str(_heuristic_insights(rows, name_hint).get("recommendedNextAction")) \
            or "Follow up as planned."
    return action


def _heuristic_schedule(message: str) -> dict:
    """Deterministic fallback for scheduling when no LLM is available."""
    from datetime import datetime, timedelta

    lowered = message.lower()
    today = datetime.now()
    target = today

    days = {
        "monday": 0, "tuesday": 1, "wednesday": 2,
        "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
    }
    for dname, dnum in days.items():
        if dname in lowered:
            delta = (dnum - today.weekday()) % 7 or 7
            target = today + timedelta(days=delta)
            break
    if "tomorrow" in lowered:
        target = today + timedelta(days=1)

    due_date = target.strftime("%Y-%m-%d")

    tm = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", lowered)
    due_time = ""
    if tm:
        hh = int(tm.group(1))
        mm = tm.group(2) or "00"
        ap = tm.group(3)
        if ap == "pm" and hh != 12:
            hh += 12
        if ap == "am" and hh == 12:
            hh = 0
        due_time = f"{hh:02d}:{mm}"

    return {"action_text": "Follow-up", "due_date": due_date, "due_time": due_time}


def _heuristic_insights(rows, name_hint):
    """Deterministic fallback insights when no LLM is available."""
    sentiments = [r.sentiment for r in rows if r.sentiment and r.sentiment != "Unknown"]
    if sentiments:
        from collections import Counter

        overall = Counter(sentiments).most_common(1)[0][0]
    else:
        overall = "Unknown"
    products: list[str] = []
    concerns: list[str] = []
    for r in rows:
        for tok in (r.topics_discussed or "").split(","):
            tok = tok.strip()
            if tok:
                products.append(tok)
        if r.outcomes:
            concerns.append(r.outcomes)
    return {
        "summary": f"{len(rows)} interaction(s) recorded"
        + (f" for {name_hint}" if name_hint else "")
        + ".",
        "overallSentiment": overall,
        "productsDiscussed": products,
        "keyConcerns": concerns,
        "recommendedNextAction": "Follow up as planned.",
    }


def merge_edit_patch(patch: dict, message: str = "") -> dict:
    """Keep ONLY the fields the user explicitly asked to change.

    The LLM returns every schema key (most empty) for an edit prompt. We drop
    any key whose value is empty / null. We ALSO drop keys the user's message
    did not reference, so the LLM cannot silently overwrite an unrelated field
    with a guessed default (e.g. resetting interactionType to "Meeting").
    """
    _field_keywords = {
        "hcpName": ["name", "hcp", "doctor", "dr"],
        "interactionType": ["type", "interaction type", "visit", "call", "meeting", "email", "field"],
        "date": ["date", "when", "reschedule"],
        "time": ["time"],
        "attendees": ["attendee", "who", "present", "with"],
        "topicsDiscussed": ["product", "topic", "discuss", "competitor"],
        "materialsShared": ["material", "resource"],
        "samplesDistributed": ["sample"],
        "sentiment": ["sentiment", "feeling", "tone"],
        "outcomes": ["note", "outcome", "summary", "conclusion", "result",
                     "mention", "request", "requested", "asked", "said", "comment", "feedback"],
        "followUpActions": ["follow", "next step", "action item", "todo"],
    }
    allowed = set(_field_keywords.keys())
    lowered = message.lower()
    out = {}
    for k, v in patch.items():
        if k not in allowed or v is None:
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        if isinstance(v, (list, dict)) and len(v) == 0:
            continue
        if k in _field_keywords and not any(kw in lowered for kw in _field_keywords[k]):
            continue
        out[k] = v
    return out


def _sentiment(v: Any) -> str:
    s = _norm(v)
    return s.capitalize() if s in ("positive", "negative", "neutral", "unknown") else "Unknown"


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _coerce_sample(s: dict) -> dict:
    return {
        "productName": _str(s.get("productName")),
        "quantity": int(s.get("quantity", 1) or 1),
        "batchNumber": _str(s.get("batchNumber")),
    }


def _extract_name(text: str) -> str:
    # The "Dr" prefix may be any case (dr / DR / Dr.), but the actual name words
    # must be Capitalized so we don't swallow trailing lowercase words like
    # "for" in "Dr. Sharma for next Friday".
    m = re.search(r"(?i:dr\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
    if not m:
        return ""
    return "Dr. " + m.group(1)
