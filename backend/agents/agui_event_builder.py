import json
from typing import Any

from backend.models.ui_protocols import A2UIPayload


class A2UISurfaceMessageBuilder:
    """
    Builds official @a2ui/react ServerToClientMessage objects for a single surface per run.
    First payload emits beginRendering + surfaceUpdate.
    Subsequent payloads emit surfaceUpdate only.
    """

    _ALLOWED_COMPONENTS = {
        "Text",
        "Button",
        "Row",
        "Column",
        "List",
        "Card",
        "Divider",
        "CheckBox",
        "TextField",
        "DateTimeInput",
        "MultipleChoice",
        "Image",
        "Icon",
        "Video",
        "AudioPlayer",
        "Tabs",
        "Modal",
        "MarkdownBlock",
        "CodeViewer",
        "DiffViewer",
        "RechartGraph",
        "ActionCard",
        "ThinkingBubble",
    }

    def __init__(self, run_id: str) -> None:
        self._surface_id = f"surface-{run_id}"
        self._node_count = 0
        self._started = False
        self._child_ids: list[str] = []

    @property
    def surface_id(self) -> str:
        return self._surface_id

    @staticmethod
    def _to_literal_value(value: Any) -> dict[str, Any]:
        if isinstance(value, bool):
            return {"literalBoolean": value}
        if isinstance(value, int) and not isinstance(value, bool):
            return {"literalNumber": value}
        if isinstance(value, float):
            return {"literalNumber": value}
        if isinstance(value, str):
            return {"literalString": value}
        return {"literalString": json.dumps(value)}

    def _normalize_text_data(self, component_data: dict[str, Any]) -> dict[str, Any]:
        data = dict(component_data)
        raw_text = data.get("text", data.get("markdown", ""))
        if isinstance(raw_text, dict):
            data["text"] = raw_text
        else:
            data["text"] = {"literalString": str(raw_text)}
        usage_hint = data.get("usageHint")
        if usage_hint not in {"h1", "h2", "h3", "h4", "h5", "caption", "body"}:
            data["usageHint"] = "body"
        return data

    def _normalize_button_data(
        self,
        node_id: str,
        component_data: dict[str, Any],
        agui_actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        data = dict(component_data)
        label = data.pop("label", None)
        if isinstance(label, dict):
            label = label.get("literalString")
        if label is None:
            label = data.pop("text", None)

        action = data.get("action")
        if not isinstance(action, dict):
            first_action = agui_actions[0] if agui_actions else {}
            intent = str(first_action.get("intent") or first_action.get("name") or "ACTION")
            context_items: list[dict[str, Any]] = []
            parameters = first_action.get("parameters", {})
            if isinstance(parameters, dict):
                context_items.extend(
                    {
                        "key": str(key),
                        "value": self._to_literal_value(value),
                    }
                    for key, value in parameters.items()
                )
            data["action"] = {"name": intent, "context": context_items}
            if "primary" not in data:
                style = str(first_action.get("style") or "").lower()
                data["primary"] = style == "primary"
            if label is None:
                label = first_action.get("label", "Action")

        child_id = data.get("child")
        if isinstance(child_id, str) and child_id.strip():
            return [{"id": node_id, "component": {"Button": data}}]

        label_id = f"{node_id}-label"
        text_component = {
            "id": label_id,
            "component": {
                "Text": {
                    "text": {"literalString": str(label or "Action")},
                    "usageHint": "body",
                }
            },
        }
        data["child"] = label_id
        button_component = {"id": node_id, "component": {"Button": data}}
        return [text_component, button_component]

    def _build_component_instances(
        self,
        node_id: str,
        payload: A2UIPayload,
    ) -> list[dict[str, Any]]:
        component_name = str(payload.componentName or "Text")
        component_data = payload.componentData if isinstance(payload.componentData, dict) else {}
        agui_actions = payload.aguiActions if isinstance(payload.aguiActions, list) else []

        if component_name not in self._ALLOWED_COMPONENTS:
            safe_markdown = json.dumps(
                {
                    "componentName": component_name,
                    "componentData": component_data,
                    "aguiActions": agui_actions,
                },
                indent=2,
            )
            return [
                {
                    "id": node_id,
                    "component": {
                        "MarkdownBlock": {
                            "markdown": f"Unsupported component '{component_name}'. Rendering raw payload:\n\n```json\n{safe_markdown}\n```"
                        }
                    },
                }
            ]

        if component_name == "Text":
            return [{"id": node_id, "component": {"Text": self._normalize_text_data(component_data)}}]

        if component_name == "Button":
            return self._normalize_button_data(node_id, component_data, agui_actions)

        if component_name == "ActionCard":
            data = dict(component_data)
            if "aguiActions" not in data and agui_actions:
                data["aguiActions"] = agui_actions
            return [{"id": node_id, "component": {"ActionCard": data}}]

        return [{"id": node_id, "component": {component_name: component_data}}]

    def build_messages(self, payload: A2UIPayload) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        node_id = f"node-{self._node_count}"
        self._node_count += 1
        self._child_ids.append(node_id)

        if not self._started:
            messages.append(
                {
                    "beginRendering": {
                        "surfaceId": self._surface_id,
                        "root": "root",
                    }
                }
            )
            self._started = True

        components: list[dict[str, Any]] = [
            {
                "id": "root",
                "component": {
                    "Column": {
                        "children": {"explicitList": list(self._child_ids)}
                    }
                },
            },
        ]
        components.extend(self._build_component_instances(node_id, payload))

        messages.append(
            {
                "surfaceUpdate": {
                    "surfaceId": self._surface_id,
                    "components": components,
                }
            }
        )

        return messages


def _extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                if part.strip():
                    parts.append(part.strip())
                continue

            if not isinstance(part, dict):
                continue

            value = part.get("text", "")
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
            elif isinstance(value, dict):
                literal = value.get("literalString")
                if isinstance(literal, str) and literal.strip():
                    parts.append(literal.strip())
        return "\n".join(parts).strip()

    return str(content).strip()


def build_prompt_and_history(
    messages: list[dict[str, Any]],
    forwarded_props: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    """
    Extract the latest user prompt and conversation history from AG-UI messages.
    Handles plain text turns and A2UI action envelopes.
    """
    history: list[dict[str, Any]] = []
    prompt = ""

    a2ui_action = forwarded_props.get("a2uiAction") or forwarded_props.get("a2ui_action")

    for msg in messages:
        role = str(msg.get("role", "user")).strip().lower()
        role = "user" if role == "user" else "assistant"
        text = _extract_text_from_content(msg.get("content", ""))
        if not text:
            continue

        if role == "user":
            prompt = text
        history.append({"role": role, "content": text})

    if a2ui_action:
        user_action = a2ui_action.get("userAction") if isinstance(a2ui_action, dict) else None
        if user_action:
            action_prompt = "\n".join(
                [
                    f"UI Action: {user_action.get('name', '')}",
                    f"Source: {user_action.get('sourceComponentId', '')}",
                    f"Surface: {user_action.get('surfaceId', '')}",
                    f"Context: {json.dumps(user_action.get('context', []))}",
                ]
            )
            prompt = action_prompt
            history.append({"role": "user", "content": action_prompt})

    return prompt, history
