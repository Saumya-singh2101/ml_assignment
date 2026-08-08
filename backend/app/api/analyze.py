import base64
import json
import re
import time
import uuid
import traceback
from datetime import datetime, timezone

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


# ============================================================
# CLEAN MODEL JSON
# ============================================================

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

    # --------------------------------------------------------
    # Remove Qwen thinking blocks
    # --------------------------------------------------------

    content = re.sub(
        r"<think>.*?</think>",
        "",
        content,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()

    # --------------------------------------------------------
    # Remove markdown code fences
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:
        parsed = json.loads(content)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # JSON inside surrounding text
    # --------------------------------------------------------

    match = re.search(
        r"\{.*\}",
        content,
        flags=re.DOTALL,
    )

    if match:
        try:
            parsed = json.loads(
                match.group(0)
            )

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    return {
        "title": "AI Response",
        "content": content,
        "latex": None,
        "format": "markdown",
        "confidence": 0.5,
    }


# ============================================================
# UTC TIMESTAMP HELPER
# ============================================================

def utc_now_iso() -> str:
    """
    Return current UTC timestamp in ISO-8601 format.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# SAFE INTEGER
# ============================================================

def safe_int(value, default=0) -> int:
    """
    Safely convert a value to int.
    """

    try:
        return int(value or default)

    except (
        TypeError,
        ValueError,
    ):
        return default


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0) -> float:
    """
    Safely convert a value to float.
    """

    try:
        return float(value or default)

    except (
        TypeError,
        ValueError,
    ):
        return default


# ============================================================
# ANALYZE CANVAS
# ============================================================

@router.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
)
def analyze(request: AnalyzeRequest):

    # ========================================================
    # REQUEST ID
    # ========================================================

    request_id = str(
        uuid.uuid4()
    )

    # High-resolution timer for latency measurement.
    total_start = time.perf_counter()

    # Real timestamp for tracing.
    ts_start = utc_now_iso()

    # ========================================================
    # DEFAULT VALUES
    # ========================================================

    image_bytes = b""
    processed_image_bytes = b""

    t_capture = 0.0
    t_cv = 0.0
    t_dispatch = 0.0
    t_render = 0.0

    provider_time = 0.0

    ttfb = 0.0
    ttft = 0.0
    stream_time = 0.0

    # Token metrics
    input_text = 0
    input_image = 0
    output_tokens = 0
    reasoning = 0
    cache_read = 0
    total_tokens = 0

    # Cost
    ai_cost = 0.0

    # Provider attempt information
    attempt = 1

    # Context safely initialized for
    # error handling.
    context = None

    # ========================================================
    # MAIN PROCESSING
    # ========================================================

    try:

        # ====================================================
        # 1. IMAGE CAPTURE / DECODE
        # ====================================================

        capture_start = time.perf_counter()

        image_bytes = base64.b64decode(
            request.image_base64
        )

        capture_end = time.perf_counter()

        t_capture = (
            capture_end
            - capture_start
        ) * 1000

        # ====================================================
        # 2. COMPUTER VISION PREPROCESSING
        # ====================================================

        cv_start = time.perf_counter()

        processed_image_bytes = (
            preprocess_canvas(
                image_bytes
            )
        )

        # Convert processed image to base64
        # ONLY for provider request.
        #
        # IMPORTANT:
        # This value is never stored in analytics
        # or trace.

        processed_image_base64 = (
            base64.b64encode(
                processed_image_bytes
            ).decode("utf-8")
        )

        cv_end = time.perf_counter()

        t_cv = (
            cv_end
            - cv_start
        ) * 1000

        # ====================================================
        # 3. DISPATCH / CONTEXT PREPARATION
        # ====================================================

        dispatch_start = time.perf_counter()

        context = request.context

        prompt = (
            context.prompt
            or "Analyze this canvas region and help the user."
        )

        dispatch_end = time.perf_counter()

        t_dispatch = (
            dispatch_end
            - dispatch_start
        ) * 1000

        # ====================================================
        # 4. AI PROVIDER
        # ====================================================

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
            provider_end
            - provider_start
        ) * 1000

        # Make sure provider response is a dict.
        if not isinstance(
            response,
            dict,
        ):
            raise ValueError(
                "Invalid response received from AI provider."
            )

        # ====================================================
        # 5. PROVIDER LATENCY METRICS
        # ====================================================

        provider_latency = response.get(
            "latency",
            {},
        )

        if not isinstance(
            provider_latency,
            dict,
        ):
            provider_latency = {}

        ttfb = safe_float(
            provider_latency.get(
                "ttfb_ms",
                provider_time,
            ),
            provider_time,
        )

        ttft = safe_float(
            provider_latency.get(
                "ttft_ms",
                provider_time,
            ),
            provider_time,
        )

        stream_time = safe_float(
            provider_latency.get(
                "stream_ms",
                max(
                    provider_time - ttfb,
                    0.0,
                ),
            ),
            0.0,
        )

        attempt = max(
            safe_int(
                provider_latency.get(
                    "attempt",
                    1,
                ),
                1,
            ),
            1,
        )

        # ====================================================
        # 6. TOKEN INFORMATION
        # ====================================================

        provider_usage = response.get(
            "usage",
            {},
        )

        if not isinstance(
            provider_usage,
            dict,
        ):
            provider_usage = {}

        input_text = safe_int(
            provider_usage.get(
                "input_text",
                0,
            )
        )

        input_image = safe_int(
            provider_usage.get(
                "input_image",
                0,
            )
        )

        output_tokens = safe_int(
            provider_usage.get(
                "output",
                0,
            )
        )

        reasoning = safe_int(
            provider_usage.get(
                "reasoning",
                0,
            )
        )

        cache_read = safe_int(
            provider_usage.get(
                "cache_read",
                0,
            )
        )

        calculated_total = (
            input_text
            + input_image
            + output_tokens
            + reasoning
            + cache_read
        )

        total_tokens = safe_int(
            provider_usage.get(
                "total",
                calculated_total,
            ),
            calculated_total,
        )

        tokens = {
            "input_text": input_text,

            "input_image": input_image,

            "input_image_source": (
                provider_usage.get(
                    "input_image_source",
                    "included_in_provider_usage",
                )
            ),

            "output": output_tokens,

            "reasoning": reasoning,

            "cache_read": cache_read,

            "total": total_tokens,
        }

        # ====================================================
        # 7. COST
        # ====================================================

        ai_cost = safe_float(
            response.get(
                "cost_usd",
                0.0,
            )
        )

        # ====================================================
        # 8. PARSE AI RESPONSE
        # ====================================================

        parsed = response.get(
            "result",
            {},
        )

        if isinstance(
            parsed,
            str,
        ):
            parsed = clean_model_json(
                parsed
            )

        elif not isinstance(
            parsed,
            dict,
        ):
            parsed = {
                "title": "AI Response",

                "content": str(
                    parsed
                ),

                "latex": None,

                "format": "markdown",

                "confidence": 0.5,
            }

        # ====================================================
        # 9. CONFIDENCE
        # ====================================================

        confidence = safe_float(
            parsed.get(
                "confidence",
                0.5,
            ),
            0.5,
        )

        # Keep confidence between 0 and 1.
        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        # ====================================================
        # 10. DRAFT CREATION
        # ====================================================

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

        # ====================================================
        # 11. RENDER / RESPONSE PREPARATION
        # ====================================================

        render_start = time.perf_counter()

        # Actual rendering happens on React/frontend.
        # Here we only construct the backend response.

        render_end = time.perf_counter()

        t_render = (
            render_end
            - render_start
        ) * 1000

        # ====================================================
        # 12. TOTAL END-TO-END LATENCY
        # ====================================================

        total_end = time.perf_counter()

        e2e = (
            total_end
            - total_start
        ) * 1000

        # ====================================================
        # 13. KPI CALCULATIONS
        # ====================================================

        processing_time = (
            t_capture
            + t_cv
            + t_dispatch
            + t_render
        )

        ai_percentage = 0.0

        if e2e > 0:

            ai_percentage = (
                provider_time
                / e2e
            ) * 100

        # ====================================================
        # 14. KPI OBJECT
        # ====================================================

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

                "ttfb_ms": round(
                    ttfb,
                    2,
                ),

                "ttft_ms": round(
                    ttft,
                    2,
                ),

                "stream_ms": round(
                    stream_time,
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
                    len(
                        processed_image_bytes
                    )
                    / max(
                        len(image_bytes),
                        1,
                    ),
                    3,
                ),
            },

            "canvas": {
                "stroke_count": (
                    context.stroke_count
                ),

                "zoom": context.zoom,

                "region_width": (
                    context.region_width
                ),

                "region_height": (
                    context.region_height
                ),
            },

            "tokens": tokens,

            "cost_usd": ai_cost,
        }

        # Prevent unused-variable confusion.
        # KPI object can later be returned from a
        # dedicated analytics endpoint if required.
        _ = kpis

        # ====================================================
        # 15. TRACE OBJECT
        # ====================================================
        #
        # IMPORTANT:
        #
        # NEVER store:
        # - image_base64
        # - processed_image_base64
        # - API keys
        # - authorization headers
        # - raw canvas image
        #
        # Only metadata is stored.
        #

        trace = {
            "request_id": request_id,

            "ts_start": ts_start,

            "success": True,

            "outcome": "pending",

            "error": None,

            "retries": max(
                attempt - 1,
                0,
            ),

            "attempt": attempt,

            "latency": {
                "capture_ms": round(
                    t_capture,
                    2,
                ),

                "cv_ms": round(
                    t_cv,
                    2,
                ),

                "dispatch_ms": round(
                    t_dispatch,
                    2,
                ),

                "provider_ms": round(
                    provider_time,
                    2,
                ),

                "ttfb_ms": round(
                    ttfb,
                    2,
                ),

                "ttft_ms": round(
                    ttft,
                    2,
                ),

                "stream_ms": round(
                    stream_time,
                    2,
                ),

                "render_ms": round(
                    t_render,
                    2,
                ),

                "e2e_ms": round(
                    e2e,
                    2,
                ),
            },

            "tokens": {
                "input_text": input_text,

                "input_image": input_image,

                "output": output_tokens,

                "reasoning": reasoning,

                "cache_read": cache_read,

                "total": total_tokens,
            },

            "cost_usd": ai_cost,

            "confidence": round(
                confidence,
                3,
            ),

            "canvas": {
                "stroke_count": (
                    context.stroke_count
                ),

                "zoom": context.zoom,

                "region_width": (
                    context.region_width
                ),

                "region_height": (
                    context.region_height
                ),
            },

            "image": {
                "original_bytes": len(
                    image_bytes
                ),

                "processed_bytes": len(
                    processed_image_bytes
                ),
            },
        }

        # ====================================================
        # 16. SAVE KPI + TRACE
        # ====================================================

        save_analysis_metric(
            request_id=request_id,

            success=True,

            stroke_count=(
                context.stroke_count
            ),

            image_size_bytes=len(
                image_bytes
            ),

            cv_latency_ms=t_cv,

            ai_latency_ms=provider_time,

            e2e_latency_ms=e2e,

            confidence=confidence,

            # Streaming metrics
            ttfb_ms=ttfb,

            ttft_ms=ttft,

            stream_ms=stream_time,

            # Token metrics
            input_tokens=input_text,

            input_image_tokens=input_image,

            output_tokens=output_tokens,

            reasoning_tokens=reasoning,

            cache_read_tokens=cache_read,

            total_tokens=total_tokens,

            # Cost
            cost_usd=ai_cost,

            # Trace
            trace=trace,
        )

        # ====================================================
        # 17. TERMINAL KPI LOG
        # ====================================================

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
            f"Attempt          : {attempt}"
        )

        print(
            f"Retries          : {max(attempt - 1, 0)}"
        )

        print(
            f"CV Time          : {t_cv:.2f} ms"
        )

        print(
            f"AI Time          : {provider_time:.2f} ms"
        )

        print(
            f"TTFB             : {ttfb:.2f} ms"
        )

        print(
            f"TTFT             : {ttft:.2f} ms"
        )

        print(
            f"Stream Time      : {stream_time:.2f} ms"
        )

        print(
            f"Total Time       : {e2e:.2f} ms"
        )

        print(
            f"Input Text       : {input_text}"
        )

        print(
            f"Input Image      : {input_image}"
        )

        print(
            f"Output Tokens    : {output_tokens}"
        )

        print(
            f"Reasoning Tokens : {reasoning}"
        )

        print(
            f"Cache Read       : {cache_read}"
        )

        print(
            f"Total Tokens     : {total_tokens}"
        )

        print(
            f"Confidence       : {confidence:.2f}"
        )

        print(
            f"AI Time %        : {ai_percentage:.2f}%"
        )

        print(
            f"Cost USD         : {ai_cost:.8f}"
        )

        print(
            "==================================\n"
        )

        # ====================================================
        # 18. FINAL RESPONSE
        # ====================================================

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
                    ttfb,
                    2,
                ),

                "ttft": round(
                    ttft,
                    2,
                ),

                "t_stream": round(
                    stream_time,
                    2,
                ),

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

            cost_usd=ai_cost,
        )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as exc:

        traceback.print_exc()

        # ====================================================
        # FAILED E2E LATENCY
        # ====================================================

        failed_e2e = (
            time.perf_counter()
            - total_start
        ) * 1000

        # ====================================================
        # SAFE CONTEXT VALUES
        # ====================================================

        if context is not None:

            failed_stroke_count = (
                context.stroke_count
            )

        else:

            failed_stroke_count = 0

        # ====================================================
        # FAILED TRACE
        # ====================================================

        failed_trace = {
            "request_id": request_id,

            "ts_start": ts_start,

            "success": False,

            "outcome": "error",

            "error": str(exc),

            "retries": max(
                attempt - 1,
                0,
            ),

            "attempt": attempt,

            "latency": {
                "capture_ms": round(
                    t_capture,
                    2,
                ),

                "cv_ms": round(
                    t_cv,
                    2,
                ),

                "dispatch_ms": round(
                    t_dispatch,
                    2,
                ),

                "provider_ms": round(
                    provider_time,
                    2,
                ),

                "ttfb_ms": round(
                    ttfb,
                    2,
                ),

                "ttft_ms": round(
                    ttft,
                    2,
                ),

                "stream_ms": round(
                    stream_time,
                    2,
                ),

                "e2e_ms": round(
                    failed_e2e,
                    2,
                ),
            },

            "tokens": {
                "input_text": input_text,

                "input_image": input_image,

                "output": output_tokens,

                "reasoning": reasoning,

                "cache_read": cache_read,

                "total": total_tokens,
            },

            "cost_usd": ai_cost,

            "confidence": 0.0,

            "canvas": {
                "stroke_count": (
                    failed_stroke_count
                ),
            },

            "image": {
                "original_bytes": len(
                    image_bytes
                ),

                "processed_bytes": len(
                    processed_image_bytes
                ),
            },
        }

        # ====================================================
        # SAVE FAILED ANALYTICS
        # ====================================================

        try:

            save_analysis_metric(
                request_id=request_id,

                success=False,

                stroke_count=(
                    failed_stroke_count
                ),

                image_size_bytes=len(
                    image_bytes
                ),

                cv_latency_ms=t_cv,

                ai_latency_ms=provider_time,

                e2e_latency_ms=failed_e2e,

                confidence=0.0,

                # Streaming metrics
                ttfb_ms=ttfb,

                ttft_ms=ttft,

                stream_ms=stream_time,

                # Token metrics
                input_tokens=input_text,

                input_image_tokens=input_image,

                output_tokens=output_tokens,

                reasoning_tokens=reasoning,

                cache_read_tokens=cache_read,

                total_tokens=total_tokens,

                # Cost
                cost_usd=ai_cost,

                # Failed trace
                trace=failed_trace,
            )

        except Exception as analytics_error:

            print(
                "Failed to save error analytics:",
                analytics_error,
            )

        # ====================================================
        # RETURN HTTP 500
        # ====================================================

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )