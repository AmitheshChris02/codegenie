from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class AGUIPayload(BaseModel):
    protocol: Literal["AGUI"] = "AGUI"
    interaction_type: str
    intent: str
    context: Dict[str, Any] = Field(default_factory=dict)


class TextMessage(BaseModel):
    type: Literal["TEXT"]
    content: str


class A2UIAction(BaseModel):
    label: str
    intent: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    style: Optional[Literal["primary", "danger", "default"]] = "default"


class A2UIPayload(BaseModel):
    type: Literal["A2UI"] = "A2UI"
    componentName: Literal[
        "MarkdownBlock",
        "CodeViewer",
        "ActionCard",
        "RechartGraph",
        "DiffViewer",
        "ThinkingBubble",
    ]
    componentData: Dict[str, Any] = Field(default_factory=dict)
    aguiActions: List[A2UIAction] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: Union[str, AGUIPayload]
    conversation_id: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)


class StreamEvent(BaseModel):
    event: Literal["text_delta", "a2ui", "done", "error", "thinking"]
    data: Any

