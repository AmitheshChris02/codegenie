from __future__ import annotations

from typing import AsyncIterator

from ag_ui.core import (
    CustomEvent,
    ReasoningEndEvent,
    ReasoningMessageContentEvent,
    ReasoningMessageEndEvent,
    ReasoningMessageStartEvent,
    ReasoningStartEvent,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)

from app.agents.agui_event_builder import (
    A2UI_CUSTOM_EVENT_NAME,
    A2UISurfaceMessageBuilder,
    a2ui_payload_to_text,
    build_prompt_and_history,
)
from app.agents.a2ui_builder import build_stream_events
from app.agents.strands_agent import get_agent_client
from app.models.ui_protocols import A2UIPayload


async def chat_event_stream(request: RunAgentInput):
    thread_id = request.thread_id
    run_id = request.run_id
    assistant_message_id = f"assistant-{run_id}"
    reasoning_message_id = f"reasoning-{run_id}"
    surface_builder = A2UISurfaceMessageBuilder(surface_id=f"surface-{run_id}")

    prompt, history = build_prompt_and_history(request)
    yield RunStartedEvent(thread_id=thread_id, run_id=run_id)
    yield TextMessageStartEvent(message_id=assistant_message_id, role="assistant")

    reasoning_started = False

    try:
        token_stream = get_agent_client().stream_response(message=prompt, history=history)
        async for event in build_stream_events(token_stream):
            if event.event == "thinking":
                thinking_text = str(event.data or "").strip()
                if not reasoning_started:
                    reasoning_started = True
                    yield ReasoningStartEvent(message_id=reasoning_message_id)
                    yield ReasoningMessageStartEvent(message_id=reasoning_message_id, role="reasoning")
                if thinking_text:
                    yield ReasoningMessageContentEvent(message_id=reasoning_message_id, delta=thinking_text)
                continue

            if event.event == "text_delta":
                delta = str(event.data or "")
                if delta:
                    yield TextMessageContentEvent(message_id=assistant_message_id, delta=delta)
                continue

            if event.event == "a2ui":
                payload = A2UIPayload.model_validate(event.data)
                a2ui_messages = surface_builder.append_payload(payload)
                yield CustomEvent(name=A2UI_CUSTOM_EVENT_NAME, value={"messages": a2ui_messages})

                readable_text = a2ui_payload_to_text(payload).strip()
                if readable_text:
                    yield TextMessageContentEvent(message_id=assistant_message_id, delta=f"{readable_text}\n\n")

        if reasoning_started:
            yield ReasoningMessageEndEvent(message_id=reasoning_message_id)
            yield ReasoningEndEvent(message_id=reasoning_message_id)

        yield TextMessageEndEvent(message_id=assistant_message_id)
        yield RunFinishedEvent(thread_id=thread_id, run_id=run_id)
    except Exception as exc:
        if reasoning_started:
            yield ReasoningMessageEndEvent(message_id=reasoning_message_id)
            yield ReasoningEndEvent(message_id=reasoning_message_id)
        yield RunErrorEvent(message=str(exc))
