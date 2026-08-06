from typing import Optional, Any

from pydantic import BaseModel, Field


class DraftResponse(BaseModel):
    """
    AI-generated draft that can later become a canvas object.
    """

    title: str = "AI Response"

    content: str = ""

    latex: Optional[str] = None

    format: str = "markdown"

    confidence: float = 0.0

    # Canvas placement
    x: float = 0.0
    y: float = 0.0

    width: float = 400.0
    height: float = 250.0

    # Important distinction:
    # this is a draft until explicitly accepted.
    status: str = "draft"


class AnalyzeResponse(BaseModel):

    request_id: str

    draft: DraftResponse

    latency_ms: dict[str, float] = Field(
        default_factory=dict
    )

    tokens: dict[str, Any] = Field(
        default_factory=dict
    )

    cost_usd: float = 0.0