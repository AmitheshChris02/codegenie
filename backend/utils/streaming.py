import json
from typing import Any, AsyncGenerator

from ag_ui.core import (
    EventType,
    RunAgentInput,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageStartEvent,
    TextMessageEndEvent,
    CustomEvent,
)
from ag_ui.encoder import EventEncoder

from backend.agents.a2ui_builder import StreamParser
from backend.agents.agui_event_builder import A2UISurfaceMessageBuilder, build_prompt_and_history
from backend.agents.strands_agent import stream_bedrock_tokens


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

    # Run started
    yield encoder.encode(
        RunStartedEvent(type=EventType.RUN_STARTED, run_id=run_id, thread_id=thread_id)
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
    a2ui_messages_batch: list[dict[str, Any]] = []

    async for token in stream_bedrock_tokens(prompt, history):
        for event_type, value in parser.feed(token):
            if event_type == "text_delta":
                yield encoder.encode(
                    TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=msg_id,
                        delta=value,
                    )
                )
            elif event_type == "a2ui":
                import sys
                print(f"[A2UI] componentName={value.componentName} componentData={json.dumps(value.componentData)[:300]}", file=sys.stderr, flush=True)
                msgs = surface_builder.build_messages(value)
                a2ui_messages_batch.extend(msgs)
                yield encoder.encode(
                    CustomEvent(
                        type=EventType.CUSTOM,
                        name="A2UI_MESSAGES",
                        value={"messages": msgs},
                    )
                )

    # Flush remaining buffer
    for event_type, value in parser.flush():
        if event_type == "text_delta" and value:
            yield encoder.encode(
                TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=msg_id,
                    delta=value,
                )
            )

    yield encoder.encode(
        TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=msg_id,
        )
    )

    yield encoder.encode(
        RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            run_id=run_id,
            thread_id=thread_id,
        )
    )
