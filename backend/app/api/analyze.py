
import base64
import json
import re
import time
import uuid

from fastapi import APIRouter, HTTPException

from app.services.image_processor import preprocess_canvas
from app.services.analytics import save_analysis_metric

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

    # Direct JSON
    try:
        return json.loads(content)

    except json.JSONDecodeError:
        pass

    # JSON inside surrounding text
    match = re.search(
        r"\{.*\}",
        content,
        flags=re.DOTALL,
    )

    if match:
        try:
            return json.loads(
                match.group(0)
            )

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

    total_start = time.perf_counter()

    try:

        # =====================================================
        # 1. IMAGE CAPTURE / DECODE
        # =====================================================

        capture_start = time.perf_counter()

        image_bytes = base64.b64decode(
            request.image_base64
        )

        capture_end = time.perf_counter()

        t_capture = (
            capture_end - capture_start
        ) * 1000


        # =====================================================
        # 2. COMPUTER VISION PREPROCESSING
        # =====================================================

        cv_start = time.perf_counter()

        processed_image_bytes = (
            preprocess_canvas(
                image_bytes
            )
        )

        processed_image_base64 = (
            base64.b64encode(
                processed_image_bytes
            ).decode("utf-8")
        )

        cv_end = time.perf_counter()

        t_cv = (
            cv_end - cv_start
        ) * 1000


        # =====================================================
        # 3. DISPATCH / CONTEXT PREPARATION
        # =====================================================

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


        # =====================================================
        # 4. AI PROVIDER
        # =====================================================

        provider_start = time.perf_counter()

        response = analyze_canvas(
            image_base64=processed_image_base64,
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


        # =====================================================
        # 5. PARSE AI RESPONSE
        # =====================================================

        parsed = response

        if not isinstance(
            parsed,
            dict,
        ):

            parsed = {
                "title": "AI Response",
                "content": str(parsed),
                "latex": None,
                "format": "markdown",
                "confidence": 0.5,
            }


        # =====================================================
        # 6. CONFIDENCE
        # =====================================================

        confidence = float(
            parsed.get(
                "confidence",
                0.5,
            )
        )

        # Keep confidence between 0 and 1
        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )


        # =====================================================
        # 7. DRAFT CREATION
        # =====================================================

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

            confidence=confidence,

            x=parsed.get(
                "x",
                context.region_x
                + context.region_width
                + 30,
            ),

            y=parsed.get(
                "y",
                context.region_y,
            ),

            width=parsed.get(
                "width",
                400,
            ),

            height=parsed.get(
                "height",
                250,
            ),

            status="draft",
        )


        # =====================================================
        # 8. RENDER / RESPONSE PREPARATION
        # =====================================================

        render_start = time.perf_counter()

        # Backend response construction.
        # Actual rendering happens in React.

        render_end = time.perf_counter()

        t_render = (
            render_end - render_start
        ) * 1000


        # =====================================================
        # 9. TOTAL END-TO-END LATENCY
        # =====================================================

        total_end = time.perf_counter()

        e2e = (
            total_end - total_start
        ) * 1000


        # =====================================================
        # 10. KPI CALCULATIONS
        # =====================================================

        processing_time = (
            t_capture
            + t_cv
            + t_dispatch
            + t_render
        )

        ai_percentage = 0.0

        if e2e > 0:

            ai_percentage = (
                provider_time / e2e
            ) * 100


        # =====================================================
        # 11. TOKEN INFORMATION
        # =====================================================

        provider_usage = response.get(
        "usage",
        {}
        )

        input_text = provider_usage.get(
        "input_text",
        0
        )

        input_image = provider_usage.get(
        "input_image",
        0
        )

        output_tokens = provider_usage.get(
        "output",
        0
        )

        reasoning = provider_usage.get(
        "reasoning",
        0
        )

        cache_read = provider_usage.get(
        "cache_read",
        0
        )

        total_tokens = provider_usage.get(
        "total",
        input_text
        + input_image
        + output_tokens
        + reasoning
        + cache_read
        )

        tokens = {

        "input_text": input_text,

        "input_image": input_image,

        "input_image_source":
            provider_usage.get(
                "input_image_source",
                "included_in_provider_usage"
            ),

        "output": output_tokens,

        "reasoning": reasoning,

        "cache_read": cache_read,

        "total": total_tokens,
        }

        # =====================================================
        # 12. FINAL KPI OBJECT
        # =====================================================

        kpis = {

            "request_id": request_id,

            "success": True,

            "confidence": round(
                confidence,
                3,
            ),

            "latency": {

                "capture_ms": round(
                    t_capture,
                    2,
                ),

                "computer_vision_ms": round(
                    t_cv,
                    2,
                ),

                "dispatch_ms": round(
                    t_dispatch,
                    2,
                ),

                "ai_ms": round(
                    provider_time,
                    2,
                ),

                "render_ms": round(
                    t_render,
                    2,
                ),

                "end_to_end_ms": round(
                    e2e,
                    2,
                ),
            },

            "ai_time_percentage": round(
                ai_percentage,
                2,
            ),

            "processing_time_ms": round(
                processing_time,
                2,
            ),

            "image": {

                "original_bytes": len(
                    image_bytes
                ),

                "processed_bytes": len(
                    processed_image_bytes
                ),

                "compression_ratio": round(
                    len(processed_image_bytes)
                    /
                    max(
                        len(image_bytes),
                        1,
                    ),
                    3,
                ),
            },

            "canvas": {

                "stroke_count":
                    context.stroke_count,

                "zoom":
                    context.zoom,

                "region_width":
                    context.region_width,

                "region_height":
                    context.region_height,
            },

            "tokens": tokens,

            "cost_usd": 0.0,
        }


        # =====================================================
        # 13. SAVE KPI TO DATABASE
        # =====================================================

        save_analysis_metric(

            request_id=request_id,

            success=True,

            stroke_count=context.stroke_count,

            image_size_bytes=len(
                image_bytes
            ),

            cv_latency_ms=t_cv,

            ai_latency_ms=provider_time,

            e2e_latency_ms=e2e,

            confidence=confidence,
        )


        # =====================================================
        # 14. TERMINAL KPI LOG
        # =====================================================

        print(
            "\n========== ANALYSIS KPI =========="
        )

        print(
            f"Request ID       : {request_id}"
        )

        print(
            "Success          : True"
        )

        print(
            f"CV Time          : {t_cv:.2f} ms"
        )

        print(
            f"AI Time          : {provider_time:.2f} ms"
        )

        print(
            f"Total Time       : {e2e:.2f} ms"
        )

        print(
            f"Confidence       : {confidence:.2f}"
        )

        print(
            f"AI Time %        : {ai_percentage:.2f}%"
        )

        print(
            "==================================\n"
        )


        # =====================================================
        # 15. FINAL RESPONSE
        # =====================================================

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

