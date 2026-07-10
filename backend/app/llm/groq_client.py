"""Groq LLM client.

Uses the Groq `gemma2-9b-it` model (configurable) to turn natural language into
structured JSON. When `GROQ_API_KEY` is absent, a deterministic fallback is used
so the app still runs end-to-end (and so the AI pipeline is demonstrably
wired through LangGraph). The real Groq call is always preferred when a key is
configured.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from app.config import settings

_SYSTEM = (
    "You are a life-sciences CRM extraction assistant. "
    "Extract structured interaction data from the user's description. "
    "Return ONLY valid JSON. Do not invent missing information: use null or an "
    "empty array/string for anything not stated. "
    "Allowed sentiment values: 'Positive', 'Negative', 'Neutral', 'Unknown'."
)

_FALLBACK_RULES = {
    "positive": "Positive",
    "positve": "Positive",
    "upbeat": "Positive",
    "happy": "Positive",
    "negative": "Negative",
    "concerned": "Negative",
    "unhappy": "Negative",
    "neutral": "Neutral",
}


# Small shared helpers (defined early so normalize_log / _heuristic_json can use them).
def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _sentiment(v: Any) -> str:
    s = _str(v).strip().lower()
    return s.capitalize() if s in ("positive", "negative", "neutral", "unknown") else "Unknown"



class GroqClient:
    """Thin wrapper around the Groq SDK with a JSON-mode contract."""

    def __init__(self) -> None:
        self.model = settings.groq_model
        self._client = None
        if settings.has_groq:
            try:
                from groq import Groq

                self._client = Groq(api_key=settings.groq_api_key)
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def complete_json(self, prompt: str, *, temperature: float = 0.2) -> dict:
        """Send a user prompt and return parsed JSON. Falls back on error."""
        if self._client is not None:
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": _SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                content = resp.choices[0].message.content or "{}"
                return normalize_log(_extract_json(content))
            except Exception as exc:  # network / quota / bad json
                return normalize_log({"_error": str(exc), **_heuristic_json(prompt)})
        return normalize_log(_heuristic_json(prompt))

    def chat(self, prompt: str, *, temperature: float = 0.4) -> str:
        if self._client is not None:
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                )
                return resp.choices[0].message.content or ""
            except Exception:
                pass
        return prompt

    def complete_json_raw(self, prompt: str, *, temperature: float = 0.2) -> dict:
        """Like ``complete_json`` but returns the model's JSON WITHOUT the
        interaction-log normalization. Use for prompts with a custom schema
        (e.g. scheduling a follow-up with ``action_text``/``due_date``)."""
        if self._client is not None:
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": _SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                content = resp.choices[0].message.content or "{}"
                return _extract_json(content)
            except Exception:
                return {}
        return {}


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {"_raw": text}


def normalize_log(data: dict[str, Any]) -> dict[str, Any]:
    """Map a model's (possibly messy) JSON onto our log schema.

    Handles array-wrapping ({'interactions':[...]}), snake_case keys, and
    plural aliases. Unknown/missing fields fall back to empty.
    """
    if not isinstance(data, dict):
        return {}
    # Unwrap an array wrapper the model may produce.
    if "interactions" in data and isinstance(data["interactions"], list) and data["interactions"]:
        data = data["interactions"][0]
    if "interaction" in data and isinstance(data["interaction"], dict):
        data = data["interaction"]

    def first(*keys, default=""):
        for k in keys:
            if k in data and data[k] not in (None, ""):
                return data[k]
        return default

    def first_list(*keys):
        for k in keys:
            v = data.get(k)
            if isinstance(v, list):
                return v
        return []

    return {
        "hcpName": _str(first("hcpName", "hcp_name")),
        "interactionType": _str(first("interactionType", "interaction_type", "type")) or "Meeting",
        "date": _str(first("date")),
        "time": _str(first("time")),
        "attendees": first_list("attendees", "attendee"),
        "topicsDiscussed": _str(first("topicsDiscussed", "topics_discussed", "topics", "topic")),
        "materialsShared": first_list("materialsShared", "materials_shared", "materials"),
        "samplesDistributed": first_list("samplesDistributed", "samples_distributed", "samples"),
        "sentiment": _sentiment(first("sentiment")),
        "outcomes": _str(first("outcomes")),
        "followUpActions": first_list("followUpActions", "follow_up_actions", "next_steps", "nextSteps"),
    }


def _heuristic_json(prompt: str) -> dict[str, Any]:
    """Deterministic fallback extraction (no external API)."""
    text = prompt
    lowered = text.lower()

    # HCP name: "Dr. <Name>" or "Dr <Name>"
    hcp_name = ""
    m = re.search(r"dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?", text)
    if m:
        hcp_name = m.group(0).replace("dr.", "Dr.").replace("dr ", "Dr. ")

    # Interaction type by keyword
    itype = "Meeting"
    if re.search(r"\b(called|phone|tele)\b", lowered):
        itype = "Call"
    elif re.search(r"\b(email|e-mail|sent)\b", lowered):
        itype = "Email"
    elif re.search(r"\b(visited|field|stopped by)\b", lowered):
        itype = "Field Visit"

    # Date / time
    date = datetime.now().strftime("%Y-%m-%d")  # current local date
    tm = re.search(r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b", lowered)
    time = tm.group(1).upper() if tm else ""

    # Sentiment
    sentiment = "Unknown"
    for k, v in _FALLBACK_RULES.items():
        if k in lowered:
            sentiment = v
            break

    # Materials
    materials = []
    if "brochure" in lowered:
        materials.append("Clinical study brochure")
    if "safety" in lowered and "pdf" in lowered:
        materials.append("Safety profile PDF")

    # Follow-ups
    follow_ups = []
    if "ask" in lowered or "request" in lowered:
        follow_ups.append("Send requested information")

    return {
        "hcpName": hcp_name,
        "interactionType": itype,
        "date": date,
        "time": time,
        "attendees": [],
        "topicsDiscussed": "",
        "materialsShared": materials,
        "samplesDistributed": [],
        "sentiment": sentiment,
        "outcomes": "",
        "followUpActions": follow_ups,
    }


groq_client = GroqClient()
