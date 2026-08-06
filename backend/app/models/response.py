from pydantic import BaseModel
from typing import Optional


class DraftResponse(BaseModel):
    title: str

    content: str

    latex: Optional[str] = None

    format: str = "markdown"

    confidence: float = 0.0


class AnalyzeResponse(BaseModel):
    request_id: str

    draft: DraftResponse

    latency_ms: dict

    tokens: dict

    cost_usd: float