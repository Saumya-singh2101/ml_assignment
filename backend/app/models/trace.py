from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Trigger(str, Enum):
    IDLE_PAUSE = "idle_pause"
    EXPLICIT = "explicit"
    REFINE = "refine"


class Outcome(str, Enum):
    ACCEPTED = "accepted"
    DISCARDED = "discarded"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
    TIMEOUT = "timeout"
    ERROR = "error"


class InputMetrics(BaseModel):
    crop_px: list[int] = Field(default_factory=lambda: [0, 0])
    format: str = "webp"
    bytes: int = 0
    zoom: float = 1.0
    stroke_count: int = 0
    prompt_chars: int = 0


class LatencyMetrics(BaseModel):
    t_capture: float = 0.0
    t_dispatch: float = 0.0
    ttfb: float = 0.0
    ttft: float = 0.0
    t_stream: float = 0.0
    t_render: float = 0.0
    e2e: float = 0.0


class TokenMetrics(BaseModel):
    input_text: int = 0
    input_image: int = 0
    input_image_source: str = "reported"
    output: int = 0
    reasoning: int = 0
    cache_read: int = 0
    total: int = 0


class TraceRecord(BaseModel):
    request_id: str
    session_id: str

    ts_start: datetime

    trigger: Trigger

    provider: str
    model: str
    effort: str = "default"
    config_id: str = "default"

    input: InputMetrics
    latency_ms: LatencyMetrics
    tokens: TokenMetrics

    cost_usd: float = 0.0

    outcome: Outcome

    error: str | None = None
    retries: int = 0