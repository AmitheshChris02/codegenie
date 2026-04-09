from typing import Any, AsyncGenerator

from ag_ui.core import (
    CustomEvent,
    EventType,
    ReasoningEndEvent,
    ReasoningMessageContentEvent,
    ReasoningMessageEndEvent,
    ReasoningMessageStartEvent,
    ReasoningStartEvent,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StepFinishedEvent,
    StepStartedEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from ag_ui.encoder import EventEncoder

from backend.agents.a2ui_builder import StreamParser, _parse_a2ui_block
from backend.agents.agui_event_builder import A2UISurfaceMessageBuilder, build_prompt_and_history
from backend.agents.strands_agent import stream_bedrock_tokens
from backend.models.ui_protocols import A2UIPayload


async def chat_event_stream(
    input_data: RunAgentInput,
) -> AsyncGenerator[bytes, None]:
    encoder = EventEncoder()
    run_id = input_data.run_id or "run-default"
    thread_id = input_data.thread_id or "thread-default"

    forwarded_props: dict[str, Any] = {}
    if input_data.forwarded_props:
        forwarded_props = dict(input_data.forwarded_props)

    messages = [m.model_dump() for m in (input_data.messages or [])]
    prompt, history = build_prompt_and_history(messages, forwarded_props)

    yield encoder.encode(
        RunStartedEvent(type=EventType.RUN_STARTED, run_id=run_id, thread_id=thread_id)
    )
    yield encoder.encode(
        StepStartedEvent(type=EventType.STEP_STARTED, step_name="model_generation")
    )

    msg_id = f"msg-{run_id}"
    yield encoder.encode(
        TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id=msg_id,
            role="assistant",
        )
    )

    parser = StreamParser()
    surface_builder = A2UISurfaceMessageBuilder(run_id)

    # Custom components rendered directly; built-ins go through A2UI protocol
    _CUSTOM_COMPONENTS = {
        "MarkdownBlock", "CodeViewer", "DiffViewer", "RechartGraph", "ActionCard", "ThinkingBubble"
    }

    saw_a2ui = False
    buffered_text_chunks: list[str] = []
    run_error_message: str | None = None
    reasoning_counter = 0

    def _buffer_text(value: Any) -> None:
        text = str(value or "")
        if text:
            buffered_text_chunks.append(text)

    def _emit_component(payload: A2UIPayload) -> bytes:
        if payload.componentName in _CUSTOM_COMPONENTS:
            # Custom components: send raw payload, frontend renders via A2UIResolver
            return encoder.encode(
                CustomEvent(
                    type=EventType.CUSTOM,
                    name="CODEGENIE_COMPONENT",
                    value={
                        "componentName": payload.componentName,
                        "componentData": payload.componentData,
                        "aguiActions": payload.aguiActions,
                    },
                )
            )
        else:
            # Built-in A2UI components: send via A2UI protocol, frontend renders via A2UIRenderer
            msgs = surface_builder.build_messages(payload)
            return encoder.encode(
                CustomEvent(
                    type=EventType.CUSTOM,
                    name="A2UI_MESSAGES",
                    value={"messages": msgs},
                )
            )

    async for token in stream_bedrock_tokens(prompt, history):
        for event_type, value in parser.feed(token):
            if event_type == "text_delta":
                _buffer_text(value)
                continue

            if event_type == "thinking":
                reasoning_text = str(value or "").strip()
                if not reasoning_text:
                    continue
                reasoning_counter += 1
                reasoning_id = f"reasoning-{run_id}-{reasoning_counter}"

                yield encoder.encode(
                    ReasoningStartEvent(
                        type=EventType.REASONING_START,
                        message_id=reasoning_id,
                    )
                )
                yield encoder.encode(
                    ReasoningMessageStartEvent(
                        type=EventType.REASONING_MESSAGE_START,
                        message_id=reasoning_id,
                        role="reasoning",
                    )
                )
                yield encoder.encode(
                    ReasoningMessageContentEvent(
                        type=EventType.REASONING_MESSAGE_CONTENT,
                        message_id=reasoning_id,
                        delta=reasoning_text,
                    )
                )
                yield encoder.encode(
                    ReasoningMessageEndEvent(
                        type=EventType.REASONING_MESSAGE_END,
                        message_id=reasoning_id,
                    )
                )
                yield encoder.encode(
                    ReasoningEndEvent(
                        type=EventType.REASONING_END,
                        message_id=reasoning_id,
                    )
                )
                continue

            if event_type == "a2ui":
                saw_a2ui = True
                yield _emit_component(value)

    for event_type, value in parser.flush():
        if event_type == "text_delta" and value:
            _buffer_text(value)

    buffered_text = "".join(buffered_text_chunks).strip()
    if "Error calling Bedrock:" in buffered_text:
        run_error_message = buffered_text

    if run_error_message:
        yield _emit_component(A2UIPayload(
            componentName="ActionCard",
            componentData={
                "title": "Model Error",
                "description": run_error_message,
                "aguiActions": [{"label": "Retry", "intent": "RETRY_LAST_REQUEST", "parameters": {}, "style": "primary"}],
            },
            aguiActions=[],
        ))
    elif buffered_text:
        def _looks_like_protocol_text(text: str) -> bool:
            lowered = text.lower()
            return "componentname" in lowered and "componentdata" in lowered

        # The model sometimes emits bare JSON blobs without <a2ui> tags.
        # Split the buffer into component blobs and plain text segments,
        # while ignoring braces inside quoted strings.
        segments: list[tuple[str, str]] = []
        last = 0
        depth = 0
        blob_start: int | None = None
        quote_char: str | None = None
        escape = False

        for i, ch in enumerate(buffered_text):
            if quote_char is not None:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == quote_char:
                    quote_char = None
                continue

            if ch in {'\"', "'"}:
                quote_char = ch
                continue

            if ch == "{":
                if depth == 0:
                    if i > last:
                        segments.append(("text", buffered_text[last:i]))
                    blob_start = i
                depth += 1
            elif ch == "}" and depth > 0:
                depth -= 1
                if depth == 0 and blob_start is not None:
                    segments.append(("json", buffered_text[blob_start:i + 1]))
                    last = i + 1
                    blob_start = None

        if last < len(buffered_text):
            segments.append(("text", buffered_text[last:]))

        for kind, content in segments:
            content = content.strip()
            if not content:
                continue

            payload: A2UIPayload | None = None
            if kind == "json" or _looks_like_protocol_text(content):
                payload = _parse_a2ui_block(content)

            if payload and payload.componentName != "MarkdownBlock":
                saw_a2ui = True
                yield _emit_component(payload)
                continue

            # Avoid showing raw protocol/schema blobs to end users.
            if _looks_like_protocol_text(content):
                continue

            yield _emit_component(A2UIPayload(
                componentName="MarkdownBlock",
                componentData={"markdown": content},
                aguiActions=[],
            ))

    if not saw_a2ui and not buffered_text and not run_error_message:
        empty_payload = A2UIPayload(
            componentName="ActionCard",
            componentData={
                "title": "Need More Detail",
                "description": "I could not produce a structured response for that follow-up. Please retry or ask the same request with one extra detail.",
                "aguiActions": [
                    {
                        "label": "Retry",
                        "intent": "RETRY_LAST_REQUEST",
                        "parameters": {},
                        "style": "primary",
                    }
                ],
            },
            aguiActions=[],
        )
        yield _emit_component(empty_payload)

    if run_error_message:
        yield encoder.encode(
            RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=run_error_message,
            )
        )

    yield encoder.encode(
        TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=msg_id,
        )
    )

    yield encoder.encode(
        StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="model_generation")
    )
    yield encoder.encode(
        RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            run_id=run_id,
            thread_id=thread_id,
        )
    )
