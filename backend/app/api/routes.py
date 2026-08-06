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


@router.get("/")
def root():
    return {
        "app": "SLATE Backend",
        "status": "running",
    }


@router.get("/health")
def health():
    return {
        "status": "healthy",
    }


@router.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
)
def analyze(request: AnalyzeRequest):

    request_id = str(uuid.uuid4())

    start = time.perf_counter()

    try:

        # -----------------------------
        # DECODE IMAGE
        # -----------------------------

        image_bytes = base64.b64decode(
            request.image_base64
        )

        # -----------------------------
        # GET CONTEXT
        # -----------------------------

        context = request.context

        prompt = (
            context.prompt
            or
            "Analyze this canvas region and help the user."
        )

        # -----------------------------
        # CALL GROQ
        # -----------------------------

        response = analyze_canvas(
            image_bytes=image_bytes,
            prompt=prompt,
        )

        # -----------------------------
        # LATENCY
        # -----------------------------

        end = time.perf_counter()

        latency = (
            (end - start) * 1000
        )

        # -----------------------------
        # GET MODEL RESPONSE
        # -----------------------------

        content = (
            response
            .choices[0]
            .message
            .content
        )

        # -----------------------------
        # ROBUST JSON PARSING
        # -----------------------------

        try:

            # Remove Qwen <think>...</think>
            # reasoning section
            clean_content = re.sub(
                r"<think>.*?</think>",
                "",
                content,
                flags=re.DOTALL,
            ).strip()

            # Remove markdown code fences
            # such as ```json ... ```
            clean_content = re.sub(
                r"```json\s*|\s*```",
                "",
                clean_content,
                flags=re.IGNORECASE,
            ).strip()

            # Find JSON object
            match = re.search(
                r"\{.*\}",
                clean_content,
                flags=re.DOTALL,
            )

            if not match:
                raise ValueError(
                    "No JSON object found in model response"
                )

            parsed = json.loads(
                match.group(0)
            )

        except (
            json.JSONDecodeError,
            ValueError,
        ):

            parsed = {
                "title": "AI Response",
                "content": content,
                "latex": None,
                "format": "markdown",
                "confidence": 0.5,
            }

        # -----------------------------
        # TOKEN METRICS
        # -----------------------------

        usage = response.usage

        tokens = {
            "input_text": getattr(
                usage,
                "prompt_tokens",
                0,
            ),
            "input_image": 0,
            "output": getattr(
                usage,
                "completion_tokens",
                0,
            ),
            "reasoning": 0,
            "cache_read": 0,
        }

        tokens["total"] = (
            tokens["input_text"]
            + tokens["output"]
        )

        # -----------------------------
        # RESPONSE
        # -----------------------------

        return AnalyzeResponse(

            request_id=request_id,

            draft=DraftResponse(
                **parsed
            ),

            latency_ms={
                "e2e": round(
                    latency,
                    2
                )
            },

            tokens=tokens,

            cost_usd=0.0,
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )