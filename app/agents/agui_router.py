from __future__ import annotations

import json

from app.models.ui_protocols import AGUIPayload, ChatRequest


def _render_agui_prompt(payload: AGUIPayload, history: list[dict]) -> str:
    intent = payload.intent.upper()
    context_json = json.dumps(payload.context, ensure_ascii=False, indent=2)

    if intent == "EXPLAIN_CODE":
        return (
            "AGUI interaction: EXPLAIN_CODE.\n"
            "Explain the code line-by-line and include practical notes.\n"
            f"Context:\n{context_json}"
        )
    if intent == "SUMMARIZE":
        return (
            "AGUI interaction: SUMMARIZE.\n"
            "Summarize the referenced component data into concise bullets.\n"
            f"Context:\n{context_json}"
        )
    if intent == "EXPAND":
        return (
            "AGUI interaction: EXPAND.\n"
            "Elaborate with deeper details and examples.\n"
            f"Context:\n{context_json}"
        )
    if intent == "REGENERATE":
        last_user = next((msg for msg in reversed(history) if msg.get("role") == "user"), None)
        previous_query = last_user.get("content", "") if isinstance(last_user, dict) else ""
        return (
            "AGUI interaction: REGENERATE.\n"
            "Regenerate the previous response with better structure.\n"
            f"Previous user query:\n{previous_query}\n"
            f"Context:\n{context_json}"
        )

    return (
        f"AGUI interaction: {payload.intent}\n"
        f"Interaction type: {payload.interaction_type}\n"
        f"Context:\n{context_json}"
    )


def resolve_incoming_message(request: ChatRequest) -> str:
    """Return normalized text prompt for both plain text and AGUI interactions."""
    message = request.message
    if isinstance(message, AGUIPayload):
        return _render_agui_prompt(message, request.history)
    return str(message)
