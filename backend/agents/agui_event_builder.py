import json
from typing import Any

from backend.models.ui_protocols import A2UIPayload


class A2UISurfaceMessageBuilder:
    """
    Builds official @a2ui/react ServerToClientMessage objects.
    Each payload is rendered on its own surface to avoid cross-component
    schema coupling issues.
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
        "Slider",
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
        self._run_id = run_id
        self._surface_count = 0

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

    @staticmethod
    def _to_literal_string_binding(value: Any, fallback: str = "") -> dict[str, Any]:
        if isinstance(value, dict):
            if isinstance(value.get("literalString"), str):
                return {"literalString": value["literalString"]}
            if isinstance(value.get("path"), str):
                return {"path": value["path"]}
            if "text" in value:
                return {"literalString": str(value.get("text") or fallback)}
        if isinstance(value, str):
            return {"literalString": value}
        if value is None:
            return {"literalString": fallback}
        return {"literalString": str(value)}

    @staticmethod
    def _to_literal_bool_binding(value: Any, fallback: bool = False) -> dict[str, Any]:
        if isinstance(value, dict):
            if isinstance(value.get("literalBoolean"), bool):
                return {"literalBoolean": value["literalBoolean"]}
            if isinstance(value.get("path"), str):
                return {"path": value["path"]}
        if isinstance(value, bool):
            return {"literalBoolean": value}
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "yes", "1", "checked", "done"}:
                return {"literalBoolean": True}
            if lowered in {"false", "no", "0", "unchecked", "todo"}:
                return {"literalBoolean": False}
        return {"literalBoolean": fallback}

    def _extract_text(self, value: Any, fallback: str = "") -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            if isinstance(value.get("literalString"), str):
                return value["literalString"]

            # Handle list-item style payloads such as primaryText/secondaryText.
            primary_raw = value.get("primaryText") or value.get("primary") or value.get("headline")
            secondary_raw = value.get("secondaryText") or value.get("subtitle") or value.get("subtext")
            primary = self._extract_text(primary_raw, "").strip() if primary_raw is not None else ""
            secondary = self._extract_text(secondary_raw, "").strip() if secondary_raw is not None else ""
            if primary and secondary:
                return f"{primary}\n{secondary}"
            if primary:
                return primary
            if secondary:
                return secondary

            for key in ("text", "label", "title", "content", "description", "name", "value"):
                nested = value.get(key)
                if nested is None:
                    continue
                nested_text = self._extract_text(nested, "").strip()
                if nested_text:
                    return nested_text
        if value is None:
            return fallback
        return str(value)

    def _make_text_node(self, node_id: str, text: str, usage_hint: str = "body") -> dict[str, Any]:
        return {
            "id": node_id,
            "component": {
                "Text": {
                    "text": {"literalString": text},
                    "usageHint": usage_hint if usage_hint in {"h1", "h2", "h3", "h4", "h5", "caption", "body"} else "body",
                }
            },
        }

    def _normalize_text_data(self, component_data: dict[str, Any]) -> dict[str, Any]:
        data = dict(component_data)
        raw_text = data.get("text", data.get("markdown", ""))
        data["text"] = self._to_literal_string_binding(raw_text)
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
        text_component = self._make_text_node(label_id, str(label or "Action"))
        data["child"] = label_id
        button_component = {"id": node_id, "component": {"Button": data}}
        return [text_component, button_component]

    def _to_literal_array_binding(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            if isinstance(value.get("path"), str):
                return {"path": value["path"]}
            literal = value.get("literalArray")
            if isinstance(literal, list):
                return {"literalArray": [str(v) for v in literal]}

        if isinstance(value, list):
            return {"literalArray": [str(v) for v in value]}

        if isinstance(value, str) and value.strip():
            return {"literalArray": [value.strip()]}

        return {"literalArray": []}

    def _to_literal_number_binding(self, value: Any, fallback: float = 0.0) -> dict[str, Any]:
        if isinstance(value, dict):
            if isinstance(value.get("path"), str):
                return {"path": value["path"]}
            literal = value.get("literalNumber")
            if isinstance(literal, (int, float)) and not isinstance(literal, bool):
                return {"literalNumber": float(literal)}

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return {"literalNumber": float(value)}

        if isinstance(value, str):
            try:
                return {"literalNumber": float(value.strip())}
            except ValueError:
                pass

        return {"literalNumber": fallback}

    def _normalize_checkbox_data(self, component_data: dict[str, Any]) -> dict[str, Any]:
        data = dict(component_data)
        label = data.get("label", data.get("text", "Item"))
        value = data.get("value", data.get("checked", False))
        return {
            "label": self._to_literal_string_binding(label, "Item"),
            "value": self._to_literal_bool_binding(value, False),
        }

    def _normalize_text_field_data(self, component_data: dict[str, Any]) -> dict[str, Any]:
        data = dict(component_data)
        label = data.get("label", data.get("title", "Input"))
        text_value = data.get("text", data.get("value", ""))
        text_field_type = str(data.get("textFieldType", "shortText"))
        if text_field_type not in {"date", "longText", "number", "shortText", "obscured"}:
            text_field_type = "shortText"

        normalized: dict[str, Any] = {
            "label": self._to_literal_string_binding(label, "Input"),
            "textFieldType": text_field_type,
        }

        if text_value is not None and str(text_value) != "":
            normalized["text"] = self._to_literal_string_binding(text_value, "")

        validation_regexp = data.get("validationRegexp")
        if isinstance(validation_regexp, str) and validation_regexp.strip():
            normalized["validationRegexp"] = validation_regexp

        return normalized

    def _normalize_datetime_input_data(self, component_data: dict[str, Any]) -> dict[str, Any]:
        data = dict(component_data)
        value = data.get("value", data.get("text", ""))
        normalized: dict[str, Any] = {
            "value": self._to_literal_string_binding(value, ""),
        }

        if isinstance(data.get("enableDate"), bool):
            normalized["enableDate"] = data["enableDate"]
        if isinstance(data.get("enableTime"), bool):
            normalized["enableTime"] = data["enableTime"]

        return normalized

    def _normalize_multiple_choice_data(self, component_data: dict[str, Any]) -> dict[str, Any]:
        data = dict(component_data)
        raw_options = data.get("options", data.get("choices", data.get("items", [])))

        if isinstance(raw_options, dict):
            raw_options = [
                {"label": k, "value": v}
                for k, v in raw_options.items()
            ]

        if not isinstance(raw_options, list):
            raw_options = []

        options: list[dict[str, Any]] = []
        for index, option in enumerate(raw_options):
            if isinstance(option, dict):
                label_raw = option.get("label") or option.get("text") or option.get("title") or option.get("name") or option.get("value")
                value_raw = option.get("value") or label_raw
            else:
                label_raw = option
                value_raw = option

            label_text = self._extract_text(label_raw, f"Option {index + 1}").strip() or f"Option {index + 1}"
            value_text = self._extract_text(value_raw, label_text).strip() or label_text

            options.append(
                {
                    "label": self._to_literal_string_binding(label_text, label_text),
                    "value": value_text,
                }
            )

        if not options:
            options.append(
                {
                    "label": self._to_literal_string_binding("Option 1", "Option 1"),
                    "value": "option_1",
                }
            )

        selections_raw = data.get("selections", data.get("selected", data.get("value", [])))
        normalized: dict[str, Any] = {
            "selections": self._to_literal_array_binding(selections_raw),
            "options": options,
        }

        max_allowed = data.get("maxAllowedSelections")
        if isinstance(max_allowed, int) and max_allowed > 0:
            normalized["maxAllowedSelections"] = max_allowed

        return normalized

    def _normalize_slider_data(self, component_data: dict[str, Any]) -> dict[str, Any]:
        data = dict(component_data)
        value = data.get("value", data.get("currentValue", data.get("selected", 0)))
        normalized: dict[str, Any] = {
            "value": self._to_literal_number_binding(value, 0.0),
        }

        min_value = data.get("minValue")
        max_value = data.get("maxValue")
        if isinstance(min_value, (int, float)) and not isinstance(min_value, bool):
            normalized["minValue"] = float(min_value)
        if isinstance(max_value, (int, float)) and not isinstance(max_value, bool):
            normalized["maxValue"] = float(max_value)

        return normalized

    def _build_card_data(
        self,
        node_id: str,
        component_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        data = dict(component_data)
        child = data.get("child")
        if isinstance(child, str) and child.strip():
            return [{"id": node_id, "component": {"Card": {"child": child}}}]

        child_id = f"{node_id}-child"
        child_text = self._extract_text(
            data.get("content") or data.get("text") or data.get("title") or data.get("description"),
            "Card content",
        )
        child_node = self._make_text_node(child_id, child_text)
        card_node = {"id": node_id, "component": {"Card": {"child": child_id}}}
        return [card_node, child_node]

    def _build_container_data(
        self,
        node_id: str,
        component_name: str,
        component_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        data = dict(component_data)
        child_nodes: list[dict[str, Any]] = []
        child_ids: list[str] = []

        raw_children = data.get("children", data.get("items", []))

        if isinstance(raw_children, dict):
            explicit = raw_children.get("explicitList")
            if isinstance(explicit, list) and all(isinstance(item, str) for item in explicit):
                container_props: dict[str, Any] = {"children": {"explicitList": explicit}}
                if component_name == "List":
                    container_props["direction"] = data.get("direction", "vertical")
                if component_name in {"Row", "Column", "List"} and "alignment" in data:
                    container_props["alignment"] = data.get("alignment")
                if component_name == "Row" and "distribution" in data:
                    container_props["distribution"] = data.get("distribution")
                container_node = {"id": node_id, "component": {component_name: container_props}}
                return [container_node]
            raw_children = []

        if not isinstance(raw_children, list):
            raw_children = [raw_children] if raw_children else []

        for index, child in enumerate(raw_children):
            child_id = f"{node_id}-child-{index}"

            if isinstance(child, dict) and "componentName" in child:
                nested_payload = A2UIPayload(
                    componentName=str(child.get("componentName") or "Text"),
                    componentData=child.get("componentData") if isinstance(child.get("componentData"), dict) else {},
                    aguiActions=child.get("aguiActions") if isinstance(child.get("aguiActions"), list) else [],
                )
                nested_nodes = self._build_component_instances(child_id, nested_payload)
                child_nodes.extend(nested_nodes)
                child_ids.append(child_id)
                continue

            if isinstance(child, dict) and (
                "checked" in child or "value" in child or str(child.get("type", "")).lower() == "checkbox"
            ):
                child_nodes.append({
                    "id": child_id,
                    "component": {"CheckBox": self._normalize_checkbox_data(child)},
                })
                child_ids.append(child_id)
                continue

            child_text = self._extract_text(child, "")
            if child_text.strip():
                child_nodes.append(self._make_text_node(child_id, child_text.strip()))
                child_ids.append(child_id)

        if not child_ids:
            placeholder_id = f"{node_id}-child-0"
            placeholder = str(data.get("emptyText") or "No items")
            child_nodes.append(self._make_text_node(placeholder_id, placeholder))
            child_ids.append(placeholder_id)

        container_props: dict[str, Any] = {
            "children": {"explicitList": child_ids}
        }

        if component_name == "List":
            direction = data.get("direction", "vertical")
            container_props["direction"] = direction if direction in {"vertical", "horizontal"} else "vertical"

        if component_name in {"Row", "Column", "List"} and data.get("alignment") in {"start", "center", "end", "stretch"}:
            container_props["alignment"] = data.get("alignment")

        if component_name == "Row" and data.get("distribution") in {
            "start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly"
        }:
            container_props["distribution"] = data.get("distribution")

        container_node = {"id": node_id, "component": {component_name: container_props}}
        return [container_node, *child_nodes]

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

        if component_name == "CheckBox":
            return [{"id": node_id, "component": {"CheckBox": self._normalize_checkbox_data(component_data)}}]

        if component_name == "TextField":
            return [{"id": node_id, "component": {"TextField": self._normalize_text_field_data(component_data)}}]

        if component_name == "DateTimeInput":
            return [{"id": node_id, "component": {"DateTimeInput": self._normalize_datetime_input_data(component_data)}}]

        if component_name == "MultipleChoice":
            return [{"id": node_id, "component": {"MultipleChoice": self._normalize_multiple_choice_data(component_data)}}]

        if component_name == "Slider":
            return [{"id": node_id, "component": {"Slider": self._normalize_slider_data(component_data)}}]

        if component_name == "ActionCard":
            data = dict(component_data)
            if "aguiActions" not in data and agui_actions:
                data["aguiActions"] = agui_actions
            return [{"id": node_id, "component": {"ActionCard": data}}]

        if component_name in {"Row", "Column", "List"}:
            return self._build_container_data(node_id, component_name, component_data)

        if component_name == "Card":
            return self._build_card_data(node_id, component_data)

        if component_name == "Divider":
            return [{"id": node_id, "component": {"Divider": {}}}]

        return [{"id": node_id, "component": {component_name: component_data}}]

    def build_messages(self, payload: A2UIPayload) -> list[dict[str, Any]]:
        surface_id = f"surface-{self._run_id}-{self._surface_count}"
        self._surface_count += 1
        node_id = "root-node"

        components = self._build_component_instances(node_id, payload)

        return [
            {
                "beginRendering": {
                    "surfaceId": surface_id,
                    "root": node_id,
                }
            },
            {
                "surfaceUpdate": {
                    "surfaceId": surface_id,
                    "components": components,
                }
            },
        ]


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
