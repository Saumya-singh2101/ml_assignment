
import base64
import json
import os
import re
import time

from groq import Groq
from groq import APIConnectionError, APIStatusError, RateLimitError

from app.core.config import GROQ_API_KEY, MODEL_NAME


# ============================================================
# GROQ CLIENT
# ============================================================

client = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# CONFIG
# ============================================================

MAX_RETRIES = 3

# Keep these configurable because pricing can change.
# Set them in .env if required.
INPUT_PRICE_PER_1M = float(
    os.getenv(
        "INPUT_RATE_PER_MILLION",
        "0"
    )
)

OUTPUT_PRICE_PER_1M = float(
    os.getenv(
        "OUTPUT_RATE_PER_MILLION",
        "0"
    )
)

# ============================================================
# CLEAN MODEL OUTPUT
# ============================================================

def clean_model_output(text: str) -> str:
    """
    Remove Qwen/Groq reasoning blocks and
    accidental markdown wrappers.
    """

    if not text:
        return ""

    # Remove <think>...</think>
    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Remove leftover think tags
    text = re.sub(
        r"</?think>",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(text: str):
    """
    Extract JSON from model response.

    Handles:
    - pure JSON
    - markdown JSON
    - surrounding text
    - thinking blocks
    """

    text = clean_model_output(text)

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:
        return json.loads(text)

    except Exception:
        pass

    # --------------------------------------------------------
    # Markdown code block
    # --------------------------------------------------------

    match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if match:
        try:
            return json.loads(
                match.group(1)
            )

        except Exception:
            pass

    # --------------------------------------------------------
    # Find JSON object
    # --------------------------------------------------------

    start = text.find("{")
    end = text.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):
        try:
            return json.loads(
                text[start:end + 1]
            )

        except Exception:
            pass

    return None


# ============================================================
# COST CALCULATION
# ============================================================

def calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
) -> float:

    input_cost = (
        prompt_tokens
        / 1_000_000
        * INPUT_PRICE_PER_1M
    )

    output_cost = (
        completion_tokens
        / 1_000_000
        * OUTPUT_PRICE_PER_1M
    )

    return (
        input_cost
        + output_cost
    )


# ============================================================
# FALLBACK RESPONSE
# ============================================================

def fallback_result(
    raw: str,
):
    return {
        "title": "AI Analysis",

        "content": clean_model_output(
            raw
        ),

        "latex": None,

        "format": "markdown",

        "confidence": 0.5,

        "x": 530,

        "y": 100,

        "width": 400,

        "height": 250,

        "status": "draft",
    }


# ============================================================
# ANALYZE CANVAS
# ============================================================

def analyze_canvas(
    image_base64: str,
    context: dict,
):
    """
    Send processed canvas image to Groq vision model.

    Returns:

    {
        "result": {...},
        "usage": {...},
        "latency": {...},
        "cost_usd": ...
    }
    """

    prompt = f"""
You are an AI whiteboard assistant.

Analyze the handwritten canvas image.

Identify:
- equations
- mathematical expressions
- diagrams
- handwritten ideas
- text
- symbols

If there is an equation:
1. Identify the equation.
2. Solve it step by step.
3. Give the final answer.

If there is a diagram:
- describe the important components
- explain relationships between them

If there is handwriting:
- transcribe it where possible
- explain the meaning if appropriate

Return ONLY valid JSON.

Do NOT include:
- <think>
- </think>
- reasoning outside JSON
- markdown code fences

Use exactly this structure:

{{
    "title": "short title",
    "content": "clear useful explanation",
    "latex": "final mathematical expression or null",
    "format": "markdown",
    "confidence": 0.0,
    "x": 530,
    "y": 100,
    "width": 400,
    "height": 250,
    "status": "draft"
}}

Canvas context:

{json.dumps(
    context,
    ensure_ascii=False
)}
"""

    # ========================================================
    # RETRY LOOP
    # ========================================================

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        request_start = time.perf_counter()

        try:

            response = client.chat.completions.create(
                model=MODEL_NAME,

                messages=[
                    {
                        "role": "user",

                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },

                            {
                                "type": "image_url",

                                "image_url": {
                                    "url":
                                        "data:image/png;base64,"
                                        + image_base64
                                },
                            },
                        ],
                    }
                ],

                temperature=0.1,
            )

            request_end = time.perf_counter()

            provider_latency = (
                request_end
                - request_start
            ) * 1000

            # =================================================
            # RAW RESPONSE
            # =================================================

            raw = (
                response
                .choices[0]
                .message
                .content
                or ""
            )

            print(
                "\n=============================="
            )

            print(
                "RAW AI RESPONSE:"
            )

            print(raw)

            print(
                "==============================\n"
            )

            # =================================================
            # PARSE
            # =================================================

            result = extract_json(
                raw
            )

            if result is None:
                result = fallback_result(
                    raw
                )

            # =================================================
            # USAGE
            # =================================================

            usage = getattr(
                response,
                "usage",
                None,
            )

            # DEBUG USAGE
            print(
                "\n========== GROQ USAGE DEBUG =========="
            )

            print(
                "usage object:",
                usage
            )

            print(
                "prompt_tokens:",
                getattr(
                    usage,
                    "prompt_tokens",
                    None,
                )
            )

            print(
                "completion_tokens:",
                getattr(
                    usage,
                    "completion_tokens",
                    None,
                )
            )

            print(
                "total_tokens:",
                getattr(
                    usage,
                    "total_tokens",
                    None,
                )
            )

            print(
                "======================================\n"
            )

            prompt_tokens = int(
                getattr(
                    usage,
                    "prompt_tokens",
                    0,
                )
                or 0
            )

            completion_tokens = int(
                getattr(
                    usage,
                    "completion_tokens",
                    0,
                )
                or 0
            )

            total_tokens = int(
                getattr(
                    usage,
                    "total_tokens",
                    prompt_tokens
                    + completion_tokens,
                )
                or 0
            )

            # =================================================
            # COST
            # =================================================

            cost = calculate_cost(
                prompt_tokens,
                completion_tokens,
            )

            # =================================================
            # RETURN EVERYTHING
            # =================================================

            return {
                "result": result,

                "usage": {
                    "input_text":
                        prompt_tokens,

                    "input_image": 0,

                    "input_image_source":
                        "included_in_provider_usage",

                    "output":
                        completion_tokens,

                    "reasoning": 0,

                    "cache_read": 0,

                    "total":
                        total_tokens,
                },

                "latency": {
                    "provider_ms":
                        round(
                            provider_latency,
                            2,
                        ),

                    "attempt":
                        attempt,
                },

                "cost_usd":
                    round(
                        cost,
                        8,
                    ),
            }

        # =====================================================
        # RATE LIMIT
        # =====================================================

        except RateLimitError as exc:

            last_error = exc

            print(
                f"Groq rate limit. "
                f"Attempt {attempt}/{MAX_RETRIES}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(
                    2 ** attempt
                )

        # =====================================================
        # CONNECTION ERROR
        # =====================================================

        except APIConnectionError as exc:

            last_error = exc

            print(
                f"Groq connection error. "
                f"Attempt {attempt}/{MAX_RETRIES}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(
                    2 ** attempt
                )

        # =====================================================
        # API STATUS ERROR
        # =====================================================

        except APIStatusError as exc:

            # Do NOT retry authentication errors.
            if getattr(
                exc,
                "status_code",
                None
            ) in [
                401,
                403,
            ]:
                raise

            last_error = exc

            print(
                f"Groq API error. "
                f"Attempt {attempt}/{MAX_RETRIES}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(
                    2 ** attempt
                )

        # =====================================================
        # UNKNOWN ERROR
        # =====================================================

        except Exception as exc:

            last_error = exc

            print(
                f"Unexpected Groq error. "
                f"Attempt {attempt}/{MAX_RETRIES}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(
                    2 ** attempt
                )

    # ========================================================
    # ALL RETRIES FAILED
    # ========================================================

    raise RuntimeError(
        f"Groq request failed after "
        f"{MAX_RETRIES} attempts: "
        f"{last_error}"
    )
