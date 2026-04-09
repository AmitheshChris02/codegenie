import json
import re
import ast
from math import isfinite
from typing import Any, Generator

from backend.models.ui_protocols import A2UIPayload


_A2UI_OPEN = "<a2ui>"
_A2UI_CLOSE = "</a2ui>"
_THINK_OPEN = "<thinking>"
_THINK_CLOSE = "</thinking>"

_COMPONENT_ALIASES: dict[str, str] = {
    "barchart": "RechartGraph",
    "linechart": "RechartGraph",
    "piechart": "RechartGraph",
    "chart": "RechartGraph",
    "graph": "RechartGraph",
    "actionitems": "ActionCard",
}


def _repair_json(raw: str) -> str:
    """Best-effort repair for truncated or malformed JSON from the model."""
    raw = raw.strip()
    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        pass

    opens = raw.count("{") - raw.count("}")
    closes = raw.count("[") - raw.count("]")
    raw += "}" * max(opens, 0) + "]" * max(closes, 0)

    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        return raw



def _looks_like_protocol_payload(raw: str) -> bool:
    lowered = raw.lower()
    return "componentname" in lowered and "componentdata" in lowered


def _sanitize_js_expressions(raw: str) -> str:
    sanitized = raw
    sanitized = re.sub(
        r"\s*\+\s*new\s+Date\(\)\.(?:toLocaleString|toISOString)\(\)",
        "",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"new\s+Date\(\)\.(?:toLocaleString|toISOString)\(\)",
        '"CURRENT_TIMESTAMP"',
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized


def _try_parse_dict(raw: str) -> dict[str, Any] | None:
    candidates: list[str] = []
    repaired = _repair_json(raw)
    sanitized = _sanitize_js_expressions(repaired)
    candidates.extend([repaired, sanitized, raw])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    literal_candidates = [sanitized, raw]
    for candidate in literal_candidates:
        py_candidate = re.sub(r"\btrue\b", "True", candidate, flags=re.IGNORECASE)
        py_candidate = re.sub(r"\bfalse\b", "False", py_candidate, flags=re.IGNORECASE)
        py_candidate = re.sub(r"\bnull\b", "None", py_candidate, flags=re.IGNORECASE)
        try:
            parsed = ast.literal_eval(py_candidate)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, SyntaxError):
            continue

    return None


def _extract_markdown_links(markdown: str) -> list[tuple[str, str]]:
    matches = re.findall(r"\[([^\]]+)\]\((https?://[^\)]+)\)", markdown)
    return [(label.strip(), url.strip()) for label, url in matches if label.strip() and url.strip()]

def _extract_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        parsed = float(value)
        return parsed if isfinite(parsed) else None

    if isinstance(value, dict):
        for key in ("literalNumber", "literalString", "value"):
            if key in value:
                nested = _extract_number(value.get(key))
                if nested is not None:
                    return nested
        return None

    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return None

        try:
            direct = float(cleaned)
            if isfinite(direct):
                return direct
        except ValueError:
            pass

        match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
        if match:
            try:
                extracted = float(match.group(0))
                if isfinite(extracted):
                    return extracted
            except ValueError:
                return None

    return None


def _normalize_chart_payload(component_data: dict[str, Any]) -> dict[str, Any]:
    data = dict(component_data)

    chart_type = str(data.get("chartType", "bar")).strip().lower()
    if "line" in chart_type:
        chart_type = "line"
    elif "pie" in chart_type or "donut" in chart_type or "doughnut" in chart_type:
        chart_type = "pie"
    else:
        chart_type = "bar"
    data["chartType"] = chart_type

    raw_data = data.get("data", [])
    normalized_data: list[dict[str, Any]] = []

    if isinstance(raw_data, list):
        normalized_data = [row for row in raw_data if isinstance(row, dict)]
    elif isinstance(raw_data, dict):
        normalized_data = [{"name": k, "value": v} for k, v in raw_data.items()]
    elif isinstance(raw_data, str):
        try:
            parsed = json.loads(raw_data)
            if isinstance(parsed, list):
                normalized_data = [row for row in parsed if isinstance(row, dict)]
            elif isinstance(parsed, dict):
                normalized_data = [{"name": k, "value": v} for k, v in parsed.items()]
        except json.JSONDecodeError:
            normalized_data = []

    data["data"] = normalized_data

    if normalized_data:
        keys = list(normalized_data[0].keys())
        x_key = str(data.get("xKey") or data.get("x") or data.get("labelKey") or "").strip()
        y_key = str(data.get("yKey") or data.get("y") or data.get("valueKey") or "").strip()

        if not x_key or x_key not in keys:
            x_key = next((k for k in keys if k.lower() in {"name", "label", "category", "module"}), keys[0])

        numeric_candidates = [
            k
            for k in keys
            if any(_extract_number(row.get(k)) is not None for row in normalized_data)
        ]

        if not y_key or y_key not in keys:
            y_key = next((k for k in numeric_candidates if k != x_key), numeric_candidates[0] if numeric_candidates else "value")

        if y_key in keys:
            for row in normalized_data:
                parsed = _extract_number(row.get(y_key))
                if parsed is not None:
                    row[y_key] = parsed

        data["xKey"] = x_key
        data["yKey"] = y_key

    return data


def _maybe_convert_markdown_links_to_action_card(component_name: str, component_data: dict[str, Any], agui_actions: list[dict[str, Any]]) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    if component_name not in {"MarkdownBlock"}:
        return component_name, component_data, agui_actions

    if agui_actions:
        return component_name, component_data, agui_actions

    markdown = ""
    if component_name == "MarkdownBlock":
        markdown = str(component_data.get("markdown", "")).strip()
    else:
        text_obj = component_data.get("text")
        if isinstance(text_obj, dict):
            markdown = str(text_obj.get("literalString", "")).strip()
        else:
            markdown = str(text_obj or "").strip()

    if not markdown:
        return component_name, component_data, agui_actions

    links = _extract_markdown_links(markdown)
    if not links:
        return component_name, component_data, agui_actions

    actions = [
        {
            "label": label,
            "intent": "OPEN_LINK",
            "parameters": {"url": url},
            "style": "default",
        }
        for label, url in links[:5]
    ]

    description = re.sub(r"\[[^\]]+\]\(https?://[^\)]+\)", "", markdown).strip()
    if len(description) > 240:
        description = description[:240].rstrip() + "..."

    action_card_data = {
        "title": "Action Items",
        "description": description or "Choose an action.",
        "aguiActions": actions,
        "metadata": {"source": "link-conversion", "linkCount": len(links)},
    }
    return "ActionCard", action_card_data, actions


def _normalize_component(
    component_name: str,
    component_data: dict[str, Any],
    agui_actions: list[dict[str, Any]],
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    alias_key = component_name.strip().lower().replace("_", "")
    canonical_name = _COMPONENT_ALIASES.get(alias_key, component_name)
    data = dict(component_data)
    actions = list(agui_actions)

    if not actions and isinstance(data.get("aguiActions"), list):
        actions = [a for a in data["aguiActions"] if isinstance(a, dict)]

    if canonical_name == "RechartGraph":
        data = _normalize_chart_payload(data)

    if canonical_name == "Button" and not actions:
        url = str(data.get("url") or data.get("href") or "").strip()
        label = str(data.get("label") or "Open").strip() or "Open"
        if url:
            actions = [{"label": label, "intent": "OPEN_LINK", "parameters": {"url": url}, "style": "primary"}]

    if canonical_name == "ActionCard" and "aguiActions" not in data and actions:
        data["aguiActions"] = actions

    canonical_name, data, actions = _maybe_convert_markdown_links_to_action_card(canonical_name, data, actions)

    return canonical_name, data, actions


def _parse_a2ui_block(raw: str) -> A2UIPayload | None:
    raw = raw.strip()
    data = _try_parse_dict(raw)

    if data is None:
        # Prevent raw protocol blobs from leaking as visible markdown.
        if _looks_like_protocol_payload(raw):
            return A2UIPayload(
                componentName="Text",
                componentData={
                    "text": {"literalString": "Structured response received. Some fields were incompatible and were skipped."},
                    "usageHint": "caption",
                },
            )
        return A2UIPayload(
            componentName="MarkdownBlock",
            componentData={"markdown": raw},
        )

    component_name = str(data.get("componentName", "MarkdownBlock"))
    component_data = data.get("componentData", data.get("props", {}))
    agui_actions = data.get("aguiActions", [])

    safe_component_data = component_data if isinstance(component_data, dict) else {}
    safe_actions = agui_actions if isinstance(agui_actions, list) else []

    component_name, safe_component_data, safe_actions = _normalize_component(
        component_name,
        safe_component_data,
        safe_actions,
    )

    return A2UIPayload(
        componentName=component_name,
        componentData=safe_component_data,
        aguiActions=safe_actions,
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
                safe_len = max(0, len(self._buf) - max(len(_THINK_OPEN), len(_A2UI_OPEN)))
                if safe_len > 0:
                    text = self._buf[:safe_len]
                    self._buf = self._buf[safe_len:]
                    yield ("text_delta", text)
                break

            if next_idx > 0:
                yield ("text_delta", self._buf[:next_idx])

            self._buf = self._buf[next_idx + len(tag):]
            if flag == "thinking":
                self._in_thinking = True
            else:
                self._in_a2ui = True

    def flush(self) -> Generator[tuple[str, Any], None, None]:
        if self._buf:
            yield ("text_delta", self._buf)
            self._buf = ""
