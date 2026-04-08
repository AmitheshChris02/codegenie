from pydantic import BaseModel
from typing import Any


class A2UIPayload(BaseModel):
    componentName: str
    componentData: dict[str, Any] = {}
    aguiActions: list[dict[str, Any]] = []
