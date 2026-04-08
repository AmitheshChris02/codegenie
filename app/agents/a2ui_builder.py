from __future__ import annotations

import json
import re
from typing import AsyncIterator, List

from app.models.ui_protocols import A2UIPayload, StreamEvent


class A2UIStreamParser:
    START_A2UI = "a2ui"
    END_A2UI = "</a2ui>"
    START_THINKING = "thinking"
    END_THINKING = "</thinking>"
    MAX_TAG_LEN = 32

    def __init__(self) -> None:
        self.mode = "text"
        self.buffer = ""
        self.capture = ""

    @staticmethod
    def _find_open_tag(buffer: str, tag_name: str) -> tuple[int, int]:
        pattern = re.compile(rf"<{tag_name}\b[^>]*>", flags=re.IGNORECASE)
        match = pattern.search(buffer)
        if not match:
            return -1, -1
        return match.start(), match.end()

    @staticmethod
    def _find_close_tag(buffer: str, close_tag: str) -> int:
        return buffer.lower().find(close_tag.lower())

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 2 and lines[-1].strip().startswith("```"):
                return "\n".join(lines[1:-1]).strip()
        return stripped

    @staticmethod
    def _extract_json_like(text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start : end + 1]
        return text

    def _try_repair_payload(self, raw_block: str) -> A2UIPayload | None:
        cleaned = self._strip_code_fences(raw_block)
        cleaned = re.sub(r"(?is)</?a2ui[^>]*>", "", cleaned).strip()
        cleaned = self._extract_json_like(cleaned).strip()

        # Attempt 1: normal JSON parse.
        try:
            parsed = json.loads(cleaned)
            return A2UIPayload.model_validate(parsed)
        except Exception:
            pass

        # Attempt 2: regex-guided repair for malformed MarkdownBlock JSON.
        component_match = re.search(r'"componentName"\s*:\s*"([^"]+)"', cleaned, flags=re.IGNORECASE)
        component_name = component_match.group(1) if component_match else "MarkdownBlock"

        if component_name == "MarkdownBlock":
            markdown_match = re.search(
                r'"markdown"\s*:\s*"([\s\S]*?)"\s*}\s*,\s*"aguiActions"\s*:',
                cleaned,
                flags=re.IGNORECASE,
            ) or re.search(
                r'"markdown"\s*:\s*"([\s\S]*?)"\s*,\s*"aguiActions"\s*:',
                cleaned,
                flags=re.IGNORECASE,
            )
            if markdown_match:
                markdown = markdown_match.group(1)
                markdown = markdown.replace("\\n", "\n").replace('\\"', '"').strip()
                actions: list = []
                actions_match = re.search(r'"aguiActions"\s*:\s*(\[[\s\S]*\])', cleaned, flags=re.IGNORECASE)
                if actions_match:
                    try:
                        actions = json.loads(actions_match.group(1))
                    except Exception:
                        actions = []
                try:
                    return A2UIPayload.model_validate(
                        {
                            "type": "A2UI",
                            "componentName": "MarkdownBlock",
                            "componentData": {"markdown": markdown},
                            "aguiActions": actions,
                        }
                    )
                except Exception:
                    return None

        return None

    def _fallback_markdown(self, raw_text: str) -> StreamEvent:
        repaired = self._try_repair_payload(raw_text)
        if repaired is not None:
            return StreamEvent(event="a2ui", data=repaired.model_dump())

        payload = A2UIPayload(
            componentName="MarkdownBlock",
            componentData={"markdown": raw_text},
            aguiActions=[],
        )
        return StreamEvent(event="a2ui", data=payload.model_dump())

    def _parse_a2ui_block(self, block: str) -> StreamEvent:
        try:
            parsed = json.loads(block)
            validated = A2UIPayload.model_validate(parsed)
            return StreamEvent(event="a2ui", data=validated.model_dump())
        except Exception:
            return self._fallback_markdown(block)

    def _parse_chunk(self, chunk: str) -> List[StreamEvent]:
        self.buffer += chunk
        events: List[StreamEvent] = []

        while True:
            if self.mode == "text":
                a2ui_at, a2ui_end = self._find_open_tag(self.buffer, self.START_A2UI)
                thinking_at, thinking_end = self._find_open_tag(self.buffer, self.START_THINKING)
                starts = [p for p in (a2ui_at, thinking_at) if p >= 0]
                if not starts:
                    safe_length = max(0, len(self.buffer) - (self.MAX_TAG_LEN - 1))
                    if safe_length > 0:
                        text = self.buffer[:safe_length]
                        self.buffer = self.buffer[safe_length:]
                        if text:
                            events.append(StreamEvent(event="text_delta", data=text))
                    break

                pos = min(starts)
                if pos > 0:
                    prefix = self.buffer[:pos]
                    if prefix:
                        events.append(StreamEvent(event="text_delta", data=prefix))

                if pos == a2ui_at and a2ui_end > a2ui_at:
                    self.buffer = self.buffer[a2ui_end:]
                    self.mode = "a2ui"
                    self.capture = ""
                    continue
                if pos == thinking_at and thinking_end > thinking_at:
                    self.buffer = self.buffer[thinking_end:]
                    self.mode = "thinking"
                    self.capture = ""
                    continue
                break

            if self.mode == "a2ui":
                end_pos = self._find_close_tag(self.buffer, self.END_A2UI)
                if end_pos < 0:
                    self.capture += self.buffer
                    self.buffer = ""
                    break
                self.capture += self.buffer[:end_pos]
                self.buffer = self.buffer[end_pos + len(self.END_A2UI) :]
                events.append(self._parse_a2ui_block(self.capture.strip()))
                self.capture = ""
                self.mode = "text"
                continue

            if self.mode == "thinking":
                end_pos = self._find_close_tag(self.buffer, self.END_THINKING)
                if end_pos < 0:
                    self.capture += self.buffer
                    self.buffer = ""
                    break
                self.capture += self.buffer[:end_pos]
                self.buffer = self.buffer[end_pos + len(self.END_THINKING) :]
                events.append(StreamEvent(event="thinking", data=self.capture.strip() or "Thinking..."))
                self.capture = ""
                self.mode = "text"
                continue

        return events

    def flush(self) -> List[StreamEvent]:
        events: List[StreamEvent] = []
        if self.mode == "a2ui":
            raw = f"<a2ui>{self.capture}{self.buffer}"
            events.append(self._fallback_markdown(raw))
        elif self.mode == "thinking":
            data = (self.capture + self.buffer).strip() or "Thinking..."
            events.append(StreamEvent(event="thinking", data=data))
        elif self.buffer:
            events.append(StreamEvent(event="text_delta", data=self.buffer))

        self.mode = "text"
        self.buffer = ""
        self.capture = ""
        return events


async def build_stream_events(tokens: AsyncIterator[str]) -> AsyncIterator[StreamEvent]:
    parser = A2UIStreamParser()
    text_buffer = ""

    def flush_text_buffer() -> List[StreamEvent]:
        nonlocal text_buffer
        if not text_buffer:
            return []
        payload = A2UIPayload(
            componentName="MarkdownBlock",
            componentData={"markdown": text_buffer},
            aguiActions=[],
        )
        text_buffer = ""
        return [StreamEvent(event="a2ui", data=payload.model_dump())]

    async for token in tokens:
        for event in parser._parse_chunk(token):
            if event.event == "text_delta":
                text_buffer += str(event.data or "")
                continue

            for buffered in flush_text_buffer():
                yield buffered
            yield event

    for event in parser.flush():
        if event.event == "text_delta":
            text_buffer += str(event.data or "")
            continue
        for buffered in flush_text_buffer():
            yield buffered
        yield event

    for buffered in flush_text_buffer():
        yield buffered
