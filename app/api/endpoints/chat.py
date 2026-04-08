from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ag_ui.core import RunAgentInput, RunErrorEvent
from ag_ui.encoder import EventEncoder

from app.utils.streaming import chat_event_stream

router = APIRouter()


@router.post("/chat")
async def chat_endpoint(request: RunAgentInput) -> StreamingResponse:
    encoder = EventEncoder()

    async def event_generator():
        try:
            async for event in chat_event_stream(request):
                yield encoder.encode(event)
        except Exception as exc:
            yield encoder.encode(RunErrorEvent(message=str(exc)))

    return StreamingResponse(event_generator(), media_type=encoder.get_content_type())
