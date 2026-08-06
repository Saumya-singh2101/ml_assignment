
import asyncio

from fastapi import APIRouter
from groq import Groq

from app.core.config import settings
from app.core.ids import generate_request_id
from app.models.request import AnalyzeRequest
from app.models.response import AnalyzeResponse, DraftObject
from app.models.trace import (
    InputMetrics,
    LatencyMetrics,
    Outcome,
    TokenMetrics,
    TraceRecord,
)
from app.services.cost import calculate_cost
from app.services.instrumentation import InstrumentationTimer
from app.storage.traces import TraceStore


router = APIRouter(
    prefix="/api/ai",
    tags=["AI"],
)

trace_store = TraceStore(settings.trace_dir)

groq_client = Groq(
    api_key=settings.groq_api_key
)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
)
async def analyze(
    request: AnalyzeRequest,
):
    request_id = generate_request_id()

    timer = InstrumentationTimer()

    try:
        # -----------------------------
        # CAPTURE / ENCODE
        # -----------------------------

        timer.start_capture()

        await asyncio.sleep(0.01)

        timer.end_capture()

        # -----------------------------
        # DISPATCH
        # -----------------------------

        timer.start_dispatch()

        await asyncio.sleep(0.005)

        timer.end_dispatch()

        # -----------------------------
        # PROVIDER - GROQ VISION
        # -----------------------------

        timer.start_provider()

        response = groq_client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                request.prompt
                                or "Analyze this drawing and explain what it represents."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (
                                    f"data:{request.image_format};"
                                    f"base64,{request.image_base64}"
                                )
                            },
                        },
                    ],
                }
            ],
            max_completion_tokens=500,
        )

        timer.mark_first_byte()
        timer.mark_first_token()
        timer.mark_last_token()

        # -----------------------------
        # MOCK RESPONSE
        # -----------------------------

        draft = DraftObject(
            id=f"draft_{request_id}",
            x=200,
            y=200,
            width=400,
            height=250,
            markdown=(
                "### AI Draft\n\n"
                "This is a placeholder response."
            ),
            latex="",
            source_request_id=request_id,
        )

        timer.mark_render_complete()

        # -----------------------------
        # TOKENS
        # -----------------------------

        input_text_tokens = max(
            1,
            len(request.prompt) // 4,
        )

        output_tokens = 12

        input_image_tokens = 0

        total_tokens = (
            input_text_tokens
            + input_image_tokens
            + output_tokens
        )

        token_metrics = TokenMetrics(
            input_text=input_text_tokens,
            input_image=input_image_tokens,
            input_image_source="estimated",
            output=output_tokens,
            reasoning=0,
            cache_read=0,
            total=total_tokens,
        )

        # -----------------------------
        # COST
        # -----------------------------

        cost = calculate_cost(
            input_tokens=input_text_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=0,
            input_rate_per_million=settings.input_rate_per_million,
            output_rate_per_million=settings.output_rate_per_million,
        )

        # -----------------------------
        # TRACE
        # -----------------------------

        trace = TraceRecord(
            request_id=request_id,
            session_id=request.session_id,
            ts_start=timer.started_at,
            trigger=request.trigger,
            provider=settings.model_provider,
            model=settings.model_name,
            effort=request.effort,
            config_id=request.config_id,
            input=InputMetrics(
                crop_px=[
                    request.crop_width,
                    request.crop_height,
                ],
                format=request.image_format,
                bytes=request.image_bytes,
                zoom=request.zoom,
                stroke_count=request.stroke_count,
                prompt_chars=len(request.prompt),
            ),
            latency_ms=LatencyMetrics(
                **timer.latency()
            ),
            tokens=token_metrics,
            cost_usd=cost,
            outcome=Outcome.DISCARDED,
            error=None,
            retries=0,
        )

        trace_store.append(trace)

        return AnalyzeResponse(
            request_id=request_id,
            status="completed",
            draft=draft,
        )

    except Exception as exc:
        latency = timer.latency()

        trace = TraceRecord(
            request_id=request_id,
            session_id=request.session_id,
            ts_start=timer.started_at,
            trigger=request.trigger,
            provider=settings.model_provider,
            model=settings.model_name,
            config_id=request.config_id,
            input=InputMetrics(
                crop_px=[
                    request.crop_width,
                    request.crop_height,
                ],
                format=request.image_format,
                bytes=request.image_bytes,
                zoom=request.zoom,
                stroke_count=request.stroke_count,
                prompt_chars=len(request.prompt),
            ),
            latency_ms=LatencyMetrics(
                **latency
            ),
            tokens=TokenMetrics(),
            cost_usd=0.0,
            outcome=Outcome.ERROR,
            error=str(exc),
            retries=0,
        )

        trace_store.append(trace)

        raise
