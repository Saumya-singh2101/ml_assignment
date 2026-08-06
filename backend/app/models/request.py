from pydantic import BaseModel
from typing import Optional


class CanvasContext(BaseModel):
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
    image_base64: str
    context: CanvasContext
    trigger: str = "explicit"