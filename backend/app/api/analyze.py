import base64
import time
import uuid
import json
import re

from fastapi import APIRouter, HTTPException

from app.models.request import AnalyzeRequest
from app.models.response import (
    AnalyzeResponse,
    DraftResponse,
)

from app.services.groq_client import analyze_canvas


router = APIRouter()


def clean_model_json(content: str) -> dict:
    """
    Convert model output into a JSON object.

    Handles:
    - normal JSON
    - markdown code fences
    - <think> blocks
    - extra text surrounding JSON
    """

    if not content:
        raise ValueError(
            "Model returned empty content."
        )

    # Remove Qwen thinking blocks
    content = re.sub(
        r"<think>.*?</think>",
        "",
        content,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()

    # Remove markdown fences
    content = re.sub(
        r"```json\s*",
        "",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"```\s*$",
        "",
        content,
    ).strip()

    # Try direct JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try finding JSON inside surrounding text
    match = re.search(
        r"\{.*\}",
        content,
        flags=re.DOTALL,
    )

    if match:
        candidate = match.group(0)

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Fallback
    return {
        "title": "AI Response",
        "content": content,
        "latex": None,
        "format": "markdown",
        "confidence": 0.5,
    }


@router.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
)
def analyze(request: AnalyzeRequest):

    request_id = str(uuid.uuid4())

    start = time.perf_counter()

    try:

        # ==========================================
        # CAPTURE / DECODE
        # ==========================================

        capture_start = time.perf_counter()

        image_bytes = base64.b64decode(
            request.image_base64
        )

        capture_end = time.perf_counter()

        t_capture = (
            capture_end - capture_start
        ) * 1000

        # ==========================================
        # DISPATCH
        # ==========================================

        dispatch_start = time.perf_counter()

        context = request.context

        prompt = (
            context.prompt
            or
            "Analyze this canvas region and help the user."
        )

        dispatch_end = time.perf_counter()

        t_dispatch = (
            dispatch_end - dispatch_start
        ) * 1000

        # ==========================================
        # PROVIDER
        # ==========================================

        provider_start = time.perf_counter()

        response = analyze_canvas(
            image_base64=request.image_base64,
            context={
                "zoom": context.zoom,
                "pan_x": context.pan_x,
                "pan_y": context.pan_y,
                "stroke_count": context.stroke_count,
                "region_x": context.region_x,
                "region_y": context.region_y,
                "region_width": context.region_width,
                "region_height": context.region_height,
                "prompt": prompt,
            },
        )

        provider_end = time.perf_counter()

        provider_time = (
            provider_end - provider_start
        ) * 1000

        # ==========================================
        # RESPONSE FROM GROQ CLIENT
        # ==========================================

        # analyze_canvas() already returns a dictionary.
        parsed = response

        # Safety fallback
        if not isinstance(parsed, dict):
            parsed = {
                "title": "AI Response",
                "content": str(parsed),
                "latex": None,
                "format": "markdown",
                "confidence": 0.5,
            }

        # ==========================================
        # DRAFT
        # ==========================================

        draft = DraftResponse(

            title=parsed.get(
                "title",
                "AI Response",
            ),

            content=parsed.get(
                "content",
                "",
            ),

            latex=parsed.get(
                "latex",
                None,
            ),

            format=parsed.get(
                "format",
                "markdown",
            ),

            confidence=float(
                parsed.get(
                    "confidence",
                    0.5,
                )
            ),

            # Position beside the canvas content
            x=(
                parsed.get(
                    "x",
                    context.region_x
                    + context.region_width
                    + 30,
                )
            ),

            y=(
                parsed.get(
                    "y",
                    context.region_y,
                )
            ),

            width=(
                parsed.get(
                    "width",
                    400,
                )
            ),

            height=(
                parsed.get(
                    "height",
                    250,
                )
            ),

            status="draft",
        )

        # ==========================================
        # RENDER TIMING
        # ==========================================

        render_start = time.perf_counter()

        # Backend response construction
        # is the current render boundary.

        render_end = time.perf_counter()

        t_render = (
            render_end - render_start
        ) * 1000

        # ==========================================
        # TOTAL LATENCY
        # ==========================================

        end = time.perf_counter()

        e2e = (
            end - start
        ) * 1000

        # ==========================================
        # TOKENS
        # ==========================================

        # groq_client currently returns the parsed
        # result instead of the raw Groq response,
        # so token usage may not be available here.

        input_text = 0
        input_image = 0
        output = 0
        reasoning = 0
        cache_read = 0

        total = (
            input_text
            + input_image
            + output
            + reasoning
            + cache_read
        )

        tokens = {

            "input_text": input_text,

            "input_image": input_image,

            "input_image_source": "estimated",

            "output": output,

            "reasoning": reasoning,

            "cache_read": cache_read,

            "total": total,
        }

        # ==========================================
        # FINAL RESPONSE
        # ==========================================

        return AnalyzeResponse(

            request_id=request_id,

            draft=draft,

            latency_ms={

                "t_capture": round(
                    t_capture,
                    2,
                ),

                "t_dispatch": round(
                    t_dispatch,
                    2,
                ),

                "ttfb": round(
                    provider_time,
                    2,
                ),

                "ttft": round(
                    provider_time,
                    2,
                ),

                "t_stream": 0.0,

                "t_render": round(
                    t_render,
                    2,
                ),

                "e2e": round(
                    e2e,
                    2,
                ),
            },

            tokens=tokens,

            cost_usd=0.0,
        )

    except Exception as exc:

        import traceback

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )