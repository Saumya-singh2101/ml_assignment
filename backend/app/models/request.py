from typing import Optional

from pydantic import BaseModel, Field


class CanvasContext(BaseModel):
    """
    Spatial and interaction context sent with an AI request.
    """

    zoom: float = 1.0

    pan_x: float = 0.0
    pan_y: float = 0.0

    stroke_count: int = 0

    region_x: float = 0.0
    region_y: float = 0.0

    region_width: float = 0.0
    region_height: float = 0.0

    prompt: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """
    Request sent from the canvas to the AI backend.
    """

    image_base64: str = Field(
        ...,
        description="Base64 encoded canvas crop"
    )

    context: CanvasContext

    trigger: str = Field(
        default="explicit",
        description="explicit | idle_pause | refine"
    )

    session_id: Optional[str] = None

    effort: Optional[str] = "medium"

    config_id: Optional[str] = "default"