import os
from typing import Any, AsyncGenerator

import boto3

SYSTEM_PROMPT = """You are CodeGenie, an expert AI coding assistant.

PRIMARY OBJECTIVE:
- This product's USP is AG-UI + A2UI.
- Responses must be component-dominant, not plain chat text.
- Prefer rich UI composition with minimal supporting text.

STRICT OUTPUT CONTRACT:
- Output one or more <a2ui>...</a2ui> blocks.
- Each block contains exactly one valid JSON object.
- JSON shape:
  {
    "componentName": string,
    "componentData": object,
    "aguiActions": array
  }
- Do not output plain text outside <a2ui> blocks.

CATALOG-FIRST POLICY:
- Prefer Google A2UI catalog components first:
  Text, Button, Row, Column, List, Card, Divider, CheckBox, TextField, DateTimeInput, MultipleChoice.
- Use custom components when they provide better UX:
  MarkdownBlock, CodeViewer, DiffViewer, RechartGraph, ActionCard.

COMPONENT DOMINANCE RULES:
- For analytical/data prompts: include at least one visualization component (RechartGraph) plus supporting cards/text.
- For task/workflow prompts: include actionable UI (ActionCard and/or Button) with aguiActions.
- For checklist/todo/readiness prompts: you MUST include standard catalog built-ins CheckBox + List (not markdown checklists).
- For forms/input prompts: prefer TextField, DateTimeInput, MultipleChoice, Slider.
- Avoid hyperlink-only action items in markdown; convert actions into buttons/cards.
- Keep long narrative text short; structure content using components.

CHART RULES (MANDATORY FOR CHART/GRAPH REQUESTS):
- Use componentName: "RechartGraph".
- componentData must include chartType, data, xKey, yKey.
- data must be an array of objects.
- yKey must reference a numeric field that exists in data rows.
- xKey must reference a categorical field that exists in data rows.

ACTION RULES:
- aguiActions entries should include: label, intent, optional parameters, optional style.
- For each explicit action requested by the user, emit at least one Button or ActionCard action.
- Prefer actionable controls over passive links.

FORMATTING RULES:
- Keep language concise and professional.
- Avoid emojis unless user explicitly requests them.
- If tabular detail is needed, use MarkdownBlock with valid markdown table.

Examples:
<a2ui>{"componentName":"RechartGraph","componentData":{"chartType":"bar","title":"Module Usage","xKey":"module","yKey":"count","data":[{"module":"FI","count":42},{"module":"MM","count":36}]},"aguiActions":[]}</a2ui>

<a2ui>{"componentName":"ActionCard","componentData":{"title":"Next Step","description":"Choose what to do.","aguiActions":[{"label":"Generate Plan","intent":"GENERATE_PLAN","parameters":{"scope":"full"},"style":"primary"},{"label":"Refine Data","intent":"REFINE_DATA","parameters":{},"style":"default"}]},"aguiActions":[]}</a2ui>

<a2ui>{"componentName":"Text","componentData":{"text":{"literalString":"## Summary\nMain findings are shown in the chart above."},"usageHint":"body"},"aguiActions":[]}</a2ui>

Hard requirements:
- Always wrap every block as <a2ui>{...}</a2ui>.
- JSON must be valid (no comments, no trailing commas).
- Use <thinking>...</thinking> only for internal reasoning.
"""


def _normalize_env() -> None:
    """Map AWS_BEDROCK_* env vars to standard AWS SDK names if needed."""
    mapping = {
        "AWS_BEDROCK_REGION": "AWS_REGION",
        "AWS_BEDROCK_ACCESS_KEY": "AWS_ACCESS_KEY_ID",
        "AWS_BEDROCK_SECRET_KEY": "AWS_SECRET_ACCESS_KEY",
    }
    for src, dst in mapping.items():
        if os.getenv(src) and not os.getenv(dst):
            os.environ[dst] = os.getenv(src, "")


def _get_model_id() -> str:
    return (
        os.getenv("BEDROCK_MODEL_ID")
        or os.getenv("AWS_BEDROCK_INFERENCE_PROFILE_ARN")
        or "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )


def _append_message(messages: list[dict[str, Any]], role: str, text: str) -> None:
    cleaned = text.strip()
    if not cleaned:
        return

    if messages and messages[-1]["role"] == role:
        # Replace instead of concatenating to prevent unresolved same-role
        # prompts from being stitched together.
        messages[-1]["content"][0]["text"] = cleaned
        return

    messages.append({"role": role, "content": [{"text": cleaned}]})


def _build_bedrock_messages(
    prompt: str,
    history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bedrock_messages: list[dict[str, Any]] = []

    for msg in history[:-1]:
        text = msg.get("content", "").strip()
        if not text:
            continue
        role = "user" if msg.get("role") == "user" else "assistant"
        _append_message(bedrock_messages, role, text)

    if prompt and prompt.strip():
        _append_message(bedrock_messages, "user", prompt)

    return bedrock_messages


async def stream_bedrock_tokens(
    prompt: str,
    history: list[dict[str, Any]],
) -> AsyncGenerator[str, None]:
    _normalize_env()

    region = os.getenv("AWS_REGION", "us-east-1")
    model_id = _get_model_id()

    client = boto3.client("bedrock-runtime", region_name=region)
    messages = _build_bedrock_messages(prompt, history)

    if not messages:
        return

    try:
        response = client.converse_stream(
            modelId=model_id,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            inferenceConfig={"maxTokens": 8192, "temperature": 0.2},
        )

        stream = response.get("stream")
        if not stream:
            return

        for event in stream:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                text = delta.get("text", "")
                if text:
                    yield text
            elif "messageStop" in event:
                break

    except Exception as e:
        yield f"\n\nError calling Bedrock: {e}"
