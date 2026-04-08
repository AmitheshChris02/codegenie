from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ag_ui.core import RunAgentInput

from backend.utils.streaming import chat_event_stream

router = APIRouter()


@router.post("/chat")
async def chat(input_data: RunAgentInput):
    return StreamingResponse(
        chat_event_stream(input_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
