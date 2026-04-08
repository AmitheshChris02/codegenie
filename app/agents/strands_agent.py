from __future__ import annotations

import asyncio
import importlib
import json
import os
import threading
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional

import boto3
from botocore.config import Config

from app.models.ui_protocols import AGUIPayload

SYSTEM_PROMPT = """You are CodeGenie, an intelligent coding assistant that can emit UI instructions.

Output rules:
1) Always prefer A2UI output for user-facing content. For most responses, emit one or more A2UI blocks.
2) A2UI blocks MUST be wrapped with <a2ui>...</a2ui> and contain valid JSON.
3) You may interleave short plain text between A2UI blocks.
4) Plain text-only responses should be avoided; return at least one MarkdownBlock A2UI payload.
5) Optional reasoning placeholders can be wrapped as <thinking>...</thinking>.

A2UI JSON schema:
{
  "type": "A2UI",
  "componentName": "MarkdownBlock|CodeViewer|ActionCard|RechartGraph|DiffViewer|ThinkingBubble",
  "componentData": { ... },
  "aguiActions": [{ "label": "...", "intent": "...", "parameters": {}, "style": "default|primary|danger" }]
}

Component mapping:
- Code -> CodeViewer with { "language": "...", "code": "...", "filename": "optional" }
- Rich explanation -> MarkdownBlock with { "markdown": "..." }
- Actions -> ActionCard with componentData { "title": "...", "description": "...", "metadata": {} }
- Charts -> RechartGraph with { "chartType": "bar|line|pie", "data": [], "xKey": "...", "yKey": "...", "title": "..." }
- Diffs -> DiffViewer with { "oldCode": "...", "newCode": "...", "language": "...", "filename": "optional" }

If the user asks for a chart, diff, or code view, prefer the matching component instead of plain text.
"""


def _normalize_env() -> None:
    """Map project .env keys to standard AWS names, when needed."""
    if not os.getenv("AWS_REGION") and os.getenv("AWS_BEDROCK_REGION"):
        os.environ["AWS_REGION"] = os.environ["AWS_BEDROCK_REGION"]
    if not os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_BEDROCK_ACCESS_KEY"):
        os.environ["AWS_ACCESS_KEY_ID"] = os.environ["AWS_BEDROCK_ACCESS_KEY"]
    if not os.getenv("AWS_SECRET_ACCESS_KEY") and os.getenv("AWS_BEDROCK_SECRET_KEY"):
        os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ["AWS_BEDROCK_SECRET_KEY"]
    if not os.getenv("AWS_EC2_METADATA_DISABLED"):
        os.environ["AWS_EC2_METADATA_DISABLED"] = "true"


def _serialize_history_message(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    role = entry.get("role")
    if role not in {"user", "assistant"}:
        return None

    content = entry.get("content", "")
    text: str
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            kind = block.get("kind")
            if kind == "text":
                parts.append(str(block.get("text", "")))
            elif kind == "a2ui":
                payload = block.get("payload", {})
                parts.append(f"<a2ui>{json.dumps(payload, ensure_ascii=False)}</a2ui>")
            elif kind == "thinking":
                parts.append("<thinking>Thinking...</thinking>")
        text = "\n".join(p for p in parts if p).strip()
    else:
        text = str(content)

    if not text:
        return None

    return {"role": role, "content": [{"text": text}]}


def _format_agui_message(payload: AGUIPayload, history: List[Dict[str, Any]]) -> str:
    intent = payload.intent.upper()
    context_json = json.dumps(payload.context, ensure_ascii=False, indent=2)

    if intent == "EXPLAIN_CODE":
        return (
            "User clicked an AGUI action to explain code.\n"
            "Provide a step-by-step explanation with a MarkdownBlock.\n"
            f"Context:\n{context_json}"
        )
    if intent == "SUMMARIZE":
        return (
            "User asked to summarize a previously rendered component.\n"
            "Respond with a concise MarkdownBlock summary.\n"
            f"Context:\n{context_json}"
        )
    if intent == "EXPAND":
        return (
            "User asked to expand on previous output.\n"
            "Provide a deeper, structured answer in MarkdownBlock and CodeViewer if useful.\n"
            f"Context:\n{context_json}"
        )
    if intent == "REGENERATE":
        last_user = next((msg for msg in reversed(history) if msg.get("role") == "user"), None)
        last_content = last_user.get("content", "") if isinstance(last_user, dict) else ""
        return (
            "Regenerate the prior answer with improved clarity and structure.\n"
            f"Last user query:\n{last_content}\n"
            f"Extra context:\n{context_json}"
        )

    return (
        "Handle this AGUI interaction as a structured UI action.\n"
        f"Intent: {payload.intent}\n"
        f"Interaction type: {payload.interaction_type}\n"
        f"Context:\n{context_json}"
    )


class BedrockStreamingAgent:
    def __init__(self) -> None:
        _normalize_env()
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv(
            "BEDROCK_MODEL_ID",
            os.getenv("AWS_BEDROCK_INFERENCE_PROFILE_ARN", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
        )
        self._strands_agent = self._build_strands_agent()
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                config=Config(proxies={}),
            )
        return self._client

    def _build_strands_agent(self) -> Optional[Any]:
        """Best-effort Strands initialization with flexible import paths."""
        try:
            agent_cls = getattr(importlib.import_module("strands"), "Agent")
        except Exception:
            return None

        bedrock_model_cls = None
        for module_name in ("strands.models", "strands.models.bedrock"):
            try:
                module = importlib.import_module(module_name)
                bedrock_model_cls = getattr(module, "BedrockModel", None)
                if bedrock_model_cls:
                    break
            except Exception:
                continue

        if bedrock_model_cls is None:
            return None

        try:
            model = bedrock_model_cls(model_id=self.model_id, region_name=self.region)
            return agent_cls(model=model, system_prompt=SYSTEM_PROMPT)
        except Exception:
            return None

    def _build_messages(self, prompt: str, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        for entry in history:
            msg = _serialize_history_message(entry)
            if msg:
                messages.append(msg)
        messages.append({"role": "user", "content": [{"text": prompt}]})
        return messages

    async def _stream_with_bedrock(self, messages: List[Dict[str, Any]]) -> AsyncIterator[str]:
        def _blocking_stream() -> Iterable[str]:
            response = self._get_client().converse_stream(
                modelId=self.model_id,
                system=[{"text": SYSTEM_PROMPT}],
                messages=messages,
                inferenceConfig={"temperature": 0.2, "maxTokens": 4096},
            )
            for event in response.get("stream", []):
                delta = event.get("contentBlockDelta", {}).get("delta", {}).get("text")
                if delta:
                    yield delta

        queue: asyncio.Queue[tuple[str, Optional[str]]] = asyncio.Queue()

        def _run_stream() -> None:
            try:
                for token in _blocking_stream():
                    loop.call_soon_threadsafe(queue.put_nowait, ("token", token))
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, ("end", None))

        loop = asyncio.get_running_loop()
        worker = threading.Thread(target=_run_stream, daemon=True)
        worker.start()

        while True:
            event_type, payload = await queue.get()
            if event_type == "end":
                break
            if event_type == "error":
                raise RuntimeError(payload or "Unknown Bedrock streaming error")
            if payload is not None:
                yield payload

    async def _stream_with_strands(self, prompt: str, history: List[Dict[str, Any]]) -> AsyncIterator[str]:
        if self._strands_agent is None:
            return
        payload = {
            "messages": self._build_messages(prompt, history),
            "stream": True,
        }

        candidate_methods = ("stream", "invoke", "run")
        for method_name in candidate_methods:
            method = getattr(self._strands_agent, method_name, None)
            if not callable(method):
                continue
            try:
                result = method(**payload)
            except TypeError:
                try:
                    result = method(payload)
                except Exception:
                    continue
            except Exception:
                continue

            if hasattr(result, "__aiter__"):
                async for item in result:
                    if isinstance(item, str):
                        yield item
                    elif isinstance(item, dict):
                        text = item.get("text") or item.get("delta")
                        if text:
                            yield text
                    else:
                        text = getattr(item, "text", None) or getattr(item, "delta", None)
                        if text:
                            yield str(text)
                return

            if hasattr(result, "__iter__"):
                for item in result:
                    if isinstance(item, str):
                        yield item
                    elif isinstance(item, dict):
                        text = item.get("text") or item.get("delta")
                        if text:
                            yield text
                    else:
                        text = getattr(item, "text", None) or getattr(item, "delta", None)
                        if text:
                            yield str(text)
                return

    async def stream_response(self, message: str | AGUIPayload, history: List[Dict[str, Any]]) -> AsyncIterator[str]:
        prompt = _format_agui_message(message, history) if isinstance(message, AGUIPayload) else str(message)

        if self._strands_agent is not None:
            emitted = False
            async for token in self._stream_with_strands(prompt, history):
                emitted = True
                yield token
            if emitted:
                return

        messages = self._build_messages(prompt, history)
        async for token in self._stream_with_bedrock(messages):
            yield token


_agent_client: Optional[BedrockStreamingAgent] = None


def get_agent_client() -> BedrockStreamingAgent:
    global _agent_client
    if _agent_client is None:
        _agent_client = BedrockStreamingAgent()
    return _agent_client
