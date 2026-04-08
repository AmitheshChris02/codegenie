import json
from typing import Any

from backend.models.ui_protocols import A2UIPayload


class A2UISurfaceMessageBuilder:
    """
    Builds official @a2ui/react ServerToClientMessage objects for a single surface per run.
    First payload emits beginRendering + surfaceUpdate.
    Subsequent payloads emit surfaceUpdate only.
    """

    def __init__(self, run_id: str) -> None:
        self._surface_id = f"surface-{run_id}"
        self._node_count = 0
        self._started = False
        self._child_ids: list[str] = []

    @property
    def surface_id(self) -> str:
        return self._surface_id

    def build_messages(self, payload: A2UIPayload) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        node_id = f"node-{self._node_count}"
        self._node_count += 1
        self._child_ids.append(node_id)

        if not self._started:
            messages.append({
                "beginRendering": {
                    "surfaceId": self._surface_id,
                    "root": "root",
                }
            })
            self._started = True

        # Flat list of ComponentInstance objects:
        # root column updated with all children so far, plus the new leaf node
        components: list[dict[str, Any]] = [
            {
                "id": "root",
                "component": {
                    "Column": {
                        "children": {"explicitList": list(self._child_ids)}
                    }
                },
            },
            {
                "id": node_id,
                "component": {
                    payload.componentName: payload.componentData
                },
            },
        ]

        messages.append({
            "surfaceUpdate": {
                "surfaceId": self._surface_id,
                "components": components,
            }
        })

        return messages


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
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            text = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict) and part.get("text", "").strip()
            )
        else:
            text = str(content)

        text = text.strip()
        if not text:
            continue

        if role == "user":
            prompt = text
        history.append({"role": role, "content": text})

    if a2ui_action:
        user_action = a2ui_action.get("userAction") if isinstance(a2ui_action, dict) else None
        if user_action:
            action_prompt = "\n".join([
                f"UI Action: {user_action.get('name', '')}",
                f"Source: {user_action.get('sourceComponentId', '')}",
                f"Surface: {user_action.get('surfaceId', '')}",
                f"Context: {json.dumps(user_action.get('context', []))}",
            ])
            prompt = action_prompt
            history.append({"role": "user", "content": action_prompt})

    return prompt, history
