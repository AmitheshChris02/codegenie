import json
import re
from typing import Any, Generator

from backend.models.ui_protocols import A2UIPayload


_A2UI_OPEN = "<a2ui>"
_A2UI_CLOSE = "</a2ui>"
_THINK_OPEN = "<thinking>"
_THINK_CLOSE = "</thinking>"


def _repair_json(raw: str) -> str:
    """Best-effort repair for truncated/malformed JSON from the model."""
    raw = raw.strip()
    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        pass
    # Close unclosed braces/brackets
    opens = raw.count("{") - raw.count("}")
    closes = raw.count("[") - raw.count("]")
    raw += "}" * max(opens, 0) + "]" * max(closes, 0)
    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        return raw


def _parse_a2ui_block(raw: str) -> A2UIPayload | None:
    raw = raw.strip()
    repaired = _repair_json(raw)
    try:
        data = json.loads(repaired)
    except json.JSONDecodeError:
        # Fallback: wrap as MarkdownBlock
        return A2UIPayload(
            componentName="MarkdownBlock",
            componentData={"markdown": raw},
        )

    if not isinstance(data, dict):
        return A2UIPayload(
            componentName="MarkdownBlock",
            componentData={"markdown": raw},
        )

    component_name = data.get("componentName", "MarkdownBlock")
    component_data = data.get("componentData", data.get("props", {}))
    agui_actions = data.get("aguiActions", [])

    return A2UIPayload(
        componentName=component_name,
        componentData=component_data if isinstance(component_data, dict) else {},
        aguiActions=agui_actions if isinstance(agui_actions, list) else [],
    )


class StreamParser:
    """
    Incrementally parses model token output into typed events:
      - ("thinking", text)
      - ("text_delta", text)
      - ("a2ui", A2UIPayload)
    """

    def __init__(self) -> None:
        self._buf = ""
        self._in_thinking = False
        self._in_a2ui = False

    def feed(self, token: str) -> Generator[tuple[str, Any], None, None]:
        self._buf += token

        while True:
            if self._in_thinking:
                idx = self._buf.find(_THINK_CLOSE)
                if idx == -1:
                    break
                thinking_text = self._buf[:idx]
                self._buf = self._buf[idx + len(_THINK_CLOSE):]
                self._in_thinking = False
                if thinking_text:
                    yield ("thinking", thinking_text)
                continue

            if self._in_a2ui:
                idx = self._buf.find(_A2UI_CLOSE)
                if idx == -1:
                    break
                a2ui_raw = self._buf[:idx]
                self._buf = self._buf[idx + len(_A2UI_CLOSE):]
                self._in_a2ui = False
                payload = _parse_a2ui_block(a2ui_raw)
                if payload:
                    yield ("a2ui", payload)
                continue

            # Look for next special tag
            think_idx = self._buf.find(_THINK_OPEN)
            a2ui_idx = self._buf.find(_A2UI_OPEN)

            next_idx = None
            if think_idx != -1 and (a2ui_idx == -1 or think_idx < a2ui_idx):
                next_idx = think_idx
                tag = _THINK_OPEN
                flag = "thinking"
            elif a2ui_idx != -1:
                next_idx = a2ui_idx
                tag = _A2UI_OPEN
                flag = "a2ui"
            else:
                # No special tag found — emit safe prefix
                # Keep a tail in buffer in case a tag is split across tokens
                safe_len = max(0, len(self._buf) - max(len(_THINK_OPEN), len(_A2UI_OPEN)))
                if safe_len > 0:
                    text = self._buf[:safe_len]
                    self._buf = self._buf[safe_len:]
                    yield ("text_delta", text)
                break

            # Emit text before the tag
            if next_idx > 0:
                yield ("text_delta", self._buf[:next_idx])

            self._buf = self._buf[next_idx + len(tag):]
            if flag == "thinking":
                self._in_thinking = True
            else:
                self._in_a2ui = True

    def flush(self) -> Generator[tuple[str, Any], None, None]:
        if self._buf:
            # Emit whatever remains as plain text
            yield ("text_delta", self._buf)
            self._buf = ""
