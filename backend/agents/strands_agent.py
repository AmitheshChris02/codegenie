import os
from typing import Any, AsyncGenerator

import boto3

SYSTEM_PROMPT = """You are CodeGenie, an expert AI coding assistant.

When responding, emit structured UI components using the <a2ui> tag with VALID JSON inside.
Each <a2ui> block must contain exactly one JSON object with these fields:
- "componentName": string (the component type)
- "componentData": object (the component's props)
- "aguiActions": array (default [])

Available components and their EXACT componentData shapes:

1. MarkdownBlock:
{"componentName":"MarkdownBlock","componentData":{"markdown":"## Hello\\nSome **bold** text."},"aguiActions":[]}

2. CodeViewer:
{"componentName":"CodeViewer","componentData":{"code":"print('hello')","language":"python","filename":"hello.py"},"aguiActions":[]}

3. DiffViewer:
{"componentName":"DiffViewer","componentData":{"oldCode":"x = 1","newCode":"x = 2","language":"python","filename":"file.py"},"aguiActions":[]}

4. RechartGraph — data MUST be an array of objects each with the xKey and yKey fields:
{"componentName":"RechartGraph","componentData":{"chartType":"bar","title":"SAP Modules","xKey":"module","yKey":"users","data":[{"module":"SAP FI","users":4200},{"module":"SAP MM","users":3800},{"module":"SAP SD","users":3100}]},"aguiActions":[]}

5. ActionCard:
{"componentName":"ActionCard","componentData":{"title":"Deploy","description":"Deploy to production?","aguiActions":[{"label":"Deploy","intent":"DEPLOY","parameters":{"env":"prod"},"style":"primary"}]},"aguiActions":[]}

RULES:
- Always wrap each <a2ui> block in its own tag: <a2ui>{...}</a2ui>
- The JSON inside must be valid — no trailing commas, no comments
- For charts, data array items MUST contain both the xKey field and the yKey field as keys
- Use <thinking>...</thinking> for internal reasoning only
- Prefer A2UI components over plain text for code, charts, diffs, and actions
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
            os.environ[dst] = os.environ[src]


def _get_model_id() -> str:
    return (
        os.getenv("BEDROCK_MODEL_ID")
        or os.getenv("AWS_BEDROCK_INFERENCE_PROFILE_ARN")
        or "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )


def _build_bedrock_messages(
    prompt: str,
    history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bedrock_messages: list[dict[str, Any]] = []

    # Add history excluding the last user message (added separately as prompt)
    for msg in history[:-1]:
        text = msg.get("content", "").strip()
        if not text:
            continue
        role = "user" if msg["role"] == "user" else "assistant"
        # Skip consecutive same-role messages (Bedrock requires alternating)
        if bedrock_messages and bedrock_messages[-1]["role"] == role:
            # Merge into previous
            bedrock_messages[-1]["content"][0]["text"] += "\n" + text
        else:
            bedrock_messages.append({"role": role, "content": [{"text": text}]})

    # Add current prompt
    if prompt and prompt.strip():
        if bedrock_messages and bedrock_messages[-1]["role"] == "user":
            bedrock_messages[-1]["content"][0]["text"] += "\n" + prompt.strip()
        else:
            bedrock_messages.append({"role": "user", "content": [{"text": prompt.strip()}]})

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
            inferenceConfig={"maxTokens": 8192, "temperature": 0.7},
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
