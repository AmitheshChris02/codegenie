from __future__ import annotations

import json
from typing import Any

from ag_ui.core import RunAgentInput

from app.models.ui_protocols import A2UIPayload


A2UI_CUSTOM_EVENT_NAME = "A2UI_MESSAGES"


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            item_type = getattr(item, "type", None)
            if item_type == "text":
                text = getattr(item, "text", "")
                if text:
                    parts.append(str(text))
                continue

            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if text:
                    parts.append(str(text))
                continue

            if isinstance(item, dict):
                source = item.get("source")
                if isinstance(source, dict):
                    value = source.get("value")
                    if value:
                        parts.append(str(value))

        return "\n".join(part for part in parts if part).strip()

    if content is None:
        return ""
    return str(content)


def _normalize_history(messages: list[Any]) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []

    for message in messages:
        role = getattr(message, "role", None)
        if role not in {"user", "assistant"}:
            continue
        text = _content_to_text(getattr(message, "content", ""))
        if not text:
            continue
        history.append({"role": str(role), "content": text})

    return history


def _try_parse_json_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return value
    if not ((stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]"))):
        return value
    try:
        return json.loads(stripped)
    except Exception:
        return value


def _build_action_prompt(forwarded_props: Any) -> str | None:
    if not isinstance(forwarded_props, dict):
        return None

    action_envelope = forwarded_props.get("a2uiAction")
    if not isinstance(action_envelope, dict):
        return None

    user_action = action_envelope.get("userAction")
    if not isinstance(user_action, dict):
        return None

    name = str(user_action.get("name", "unknown_action"))
    source_component = str(user_action.get("sourceComponentId", "unknown_component"))
    surface_id = str(user_action.get("surfaceId", "unknown_surface"))
    raw_context = user_action.get("context", {})
    context: Any
    if isinstance(raw_context, dict):
        context = {k: _try_parse_json_string(v) for k, v in raw_context.items()}
    else:
        context = raw_context

    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    return (
        "The user interacted with a rendered A2UI component.\n"
        f"Action: {name}\n"
        f"Source component: {source_component}\n"
        f"Surface: {surface_id}\n"
        f"Resolved action context:\n{context_json}\n"
        "Respond by updating the UI with one or more A2UI blocks."
    )


def build_prompt_and_history(run_input: RunAgentInput) -> tuple[str, list[dict[str, str]]]:
    normalized_history = _normalize_history(list(run_input.messages or []))

    action_prompt = _build_action_prompt(run_input.forwarded_props)
    if action_prompt:
        return action_prompt, normalized_history

    if not normalized_history:
        return "Introduce yourself and ask how you can help.", []

    last_user_idx = -1
    for idx in range(len(normalized_history) - 1, -1, -1):
        if normalized_history[idx]["role"] == "user":
            last_user_idx = idx
            break

    if last_user_idx < 0:
        return "Continue the conversation and provide the most helpful next response.", normalized_history

    prompt = normalized_history[last_user_idx]["content"]
    history_without_last_user = normalized_history[:last_user_idx] + normalized_history[last_user_idx + 1 :]
    return prompt, history_without_last_user


def _serialize_action_value(value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"literalBoolean": value}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"literalNumber": value}
    if isinstance(value, float):
        return {"literalNumber": value}
    return {"literalString": json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)}


class A2UISurfaceMessageBuilder:
    def __init__(self, surface_id: str) -> None:
        self.surface_id = surface_id
        self.initialized = False
        self.children: list[str] = []
        self.counter = 0

    def _next_component_id(self) -> str:
        self.counter += 1
        return f"node-{self.counter}"

    def _payload_properties(self, payload: A2UIPayload) -> dict[str, Any]:
        properties = dict(payload.componentData)

        if payload.aguiActions:
            properties["aguiActions"] = [
                {
                    "label": action.label,
                    "intent": action.intent,
                    "parameters": action.parameters,
                    "style": action.style or "default",
                }
                for action in payload.aguiActions
            ]
            properties["actions"] = [
                {
                    "label": action.label,
                    "style": action.style or "default",
                    "action": {
                        "name": action.intent,
                        "context": [
                            {"key": key, "value": _serialize_action_value(value)}
                            for key, value in (action.parameters or {}).items()
                        ],
                    },
                }
                for action in payload.aguiActions
            ]

        return properties

    def append_payload(self, payload: A2UIPayload) -> list[dict[str, Any]]:
        component_id = self._next_component_id()
        self.children.append(component_id)

        surface_update = {
            "surfaceUpdate": {
                "surfaceId": self.surface_id,
                "components": [
                    {
                        "id": "root",
                        "component": {
                            "Column": {
                                "children": {
                                    "explicitList": list(self.children),
                                }
                            }
                        },
                    },
                    {
                        "id": component_id,
                        "component": {
                            payload.componentName: self._payload_properties(payload),
                        },
                    },
                ],
            }
        }

        if not self.initialized:
            self.initialized = True
            return [
                {
                    "beginRendering": {
                        "surfaceId": self.surface_id,
                        "root": "root",
                    }
                },
                surface_update,
            ]

        return [surface_update]


def a2ui_payload_to_text(payload: A2UIPayload) -> str:
    data = payload.componentData

    if payload.componentName == "MarkdownBlock":
        return str(data.get("markdown", ""))

    if payload.componentName == "CodeViewer":
        language = str(data.get("language", "text"))
        code = str(data.get("code", ""))
        return f"```{language}\n{code}\n```"

    if payload.componentName == "DiffViewer":
        old_code = str(data.get("oldCode", ""))
        new_code = str(data.get("newCode", ""))
        return f"Diff:\n---\n{old_code}\n+++\n{new_code}"

    if payload.componentName == "ActionCard":
        title = str(data.get("title", "Action"))
        description = str(data.get("description", "")).strip()
        action_labels = [action.label for action in payload.aguiActions]
        label_text = ", ".join(action_labels) if action_labels else "No actions"
        return f"{title}\n{description}\nAvailable actions: {label_text}".strip()

    if payload.componentName == "RechartGraph":
        title = str(data.get("title", "Chart"))
        return f"{title}\n(Chart data updated)"

    return json.dumps(payload.model_dump(), ensure_ascii=False)
