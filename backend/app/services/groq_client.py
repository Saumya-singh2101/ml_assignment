import json
import os
import re
import time

from groq import Groq
from groq import (
    APIConnectionError,
    APIStatusError,
    RateLimitError,
)

from app.core.config import (
    GROQ_API_KEY,
    MODEL_NAME,
)


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

INPUT_PRICE_PER_1M = float(
    os.getenv(
        "INPUT_RATE_PER_MILLION",
        "0",
    )
)

OUTPUT_PRICE_PER_1M = float(
    os.getenv(
        "OUTPUT_RATE_PER_MILLION",
        "0",
    )
)


# ============================================================
# CLEAN MODEL OUTPUT
# ============================================================

def clean_model_output(text: str) -> str:
    """
    Remove reasoning/thinking blocks from model output.

    Handles:
    - <think>...</think>
    - stray <think>
    - stray </think>
    """

    if not text:
        return ""

    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

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
    - markdown JSON blocks
    - surrounding text
    - thinking blocks
    """

    text = clean_model_output(
        text
    )

    if not text:
        return None

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:
        parsed = json.loads(
            text
        )

        if isinstance(
            parsed,
            dict,
        ):
            return parsed

    except (
        json.JSONDecodeError,
        TypeError,
    ):
        pass

    # --------------------------------------------------------
    # Markdown JSON code block
    # --------------------------------------------------------

    match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if match:

        try:
            parsed = json.loads(
                match.group(1)
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except (
            json.JSONDecodeError,
            TypeError,
        ):
            pass

    # --------------------------------------------------------
    # JSON object surrounded by text
    # --------------------------------------------------------

    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
    )

    if (
        start != -1
        and end != -1
        and end > start
    ):

        try:
            parsed = json.loads(
                text[
                    start:end + 1
                ]
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except (
            json.JSONDecodeError,
            TypeError,
        ):
            pass

    return None


# ============================================================
# COST CALCULATION
# ============================================================

def calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """
    Calculate estimated AI cost using configured
    per-million-token rates.
    """

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
    """
    Fallback response when model output cannot
    be parsed as JSON.
    """

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
# SAFE USAGE HELPERS
# ============================================================

def get_usage_value(
    usage,
    attribute: str,
    default: int = 0,
) -> int:
    """
    Safely read an integer usage field from
    the Groq usage object.
    """

    if usage is None:
        return default

    value = getattr(
        usage,
        attribute,
        default,
    )

    try:
        return int(
            value or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


def get_nested_usage_value(
    usage,
    parent_attribute: str,
    child_attribute: str,
    default: int = 0,
) -> int:
    """
    Safely read nested usage information such as:

        usage.prompt_tokens_details.cached_tokens

    or

        usage.completion_tokens_details.reasoning_tokens
    """

    if usage is None:
        return default

    parent = getattr(
        usage,
        parent_attribute,
        None,
    )

    if parent is None:
        return default

    value = getattr(
        parent,
        child_attribute,
        default,
    )

    try:
        return int(
            value or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


# ============================================================
# ANALYZE CANVAS
# ============================================================

def analyze_canvas(
    image_base64: str,
    context: dict,
):
    """
    Send a processed canvas image to the Groq vision model.

    Returns:

    {
        "result": {...},

        "usage": {
            "input_text": ...,
            "input_image": ...,
            "input_image_source": ...,
            "output": ...,
            "reasoning": ...,
            "cache_read": ...,
            "total": ...
        },

        "latency": {
            "provider_ms": ...,
            "ttfb_ms": ...,
            "ttft_ms": ...,
            "stream_ms": ...,
            "attempt": ...
        },

        "cost_usd": ...
    }
    """

    # ========================================================
    # PROMPT
    # ========================================================

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
    ensure_ascii=False,
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

        request_start = (
            time.perf_counter()
        )

        try:

            # =================================================
            # STREAMING REQUEST
            # =================================================

            stream = client.chat.completions.create(
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
                                        + image_base64,
                                },
                            },
                        ],
                    }
                ],

                temperature=0.1,

                # Groq supports streamed responses.
                stream=True,

            )
            # =================================================
            # STREAM METRICS
            # =================================================

            first_chunk_time = None

            first_text_time = None

            chunks = []

            usage = None

            # =================================================
            # READ STREAM
            # =================================================

            for chunk in stream:

                current_time = (
                    time.perf_counter()
                )

                # -------------------------------------------------
                # FIRST STREAM CHUNK = TTFB
                # -------------------------------------------------

                if first_chunk_time is None:

                    first_chunk_time = (
                        current_time
                        - request_start
                    ) * 1000

                # -------------------------------------------------
                # USAGE
                # -------------------------------------------------
                #
                # Usage can arrive in the final streamed
                # chunk when include_usage=True.
                #

                chunk_usage = getattr(
                    chunk,
                    "usage",
                    None,
                )

                if chunk_usage is not None:

                    usage = (
                        chunk_usage
                    )

                # -------------------------------------------------
                # EXTRACT STREAMED TEXT
                # -------------------------------------------------

                choices = getattr(
                    chunk,
                    "choices",
                    None,
                )

                if not choices:
                    continue

                delta = getattr(
                    choices[0],
                    "delta",
                    None,
                )

                if delta is None:
                    continue

                content = getattr(
                    delta,
                    "content",
                    None,
                )

                if content:

                    # First actual text token/content = TTFT
                    if first_text_time is None:

                        first_text_time = (
                            current_time
                            - request_start
                        ) * 1000

                    chunks.append(
                        content
                    )

            # =================================================
            # STREAM FINISHED
            # =================================================

            request_end = (
                time.perf_counter()
            )

            provider_latency = (
                request_end
                - request_start
            ) * 1000

            # =================================================
            # TTFB
            # =================================================

            if first_chunk_time is None:

                ttfb = provider_latency

            else:

                ttfb = first_chunk_time

            # =================================================
            # TTFT
            # =================================================

            if first_text_time is None:

                ttft = ttfb

            else:

                ttft = first_text_time

            # =================================================
            # STREAM TIME
            # =================================================

            stream_latency = max(
                provider_latency
                - ttfb,
                0.0,
            )

            # =================================================
            # COMBINE RESPONSE
            # =================================================

            raw = "".join(
                chunks
            )

            print(
                "\n=============================="
            )

            print(
                "RAW AI RESPONSE:"
            )

            print(
                raw
            )

            print(
                "==============================\n"
            )

            # =================================================
            # STREAMING DEBUG
            # =================================================

            print(
                "\n========== GROQ STREAM DEBUG =========="
            )

            print(
                f"Attempt: {attempt}"
            )

            print(
                f"TTFB: {ttfb:.2f} ms"
            )

            print(
                f"TTFT: {ttft:.2f} ms"
            )

            print(
                f"Stream time: {stream_latency:.2f} ms"
            )

            print(
                f"Provider time: {provider_latency:.2f} ms"
            )

            print(
                "=======================================\n"
            )

            # =================================================
            # PARSE RESPONSE
            # =================================================

            result = extract_json(
                raw
            )

            if result is None:

                result = fallback_result(
                    raw
                )

            # =================================================
            # TOKEN INFORMATION
            # =================================================

            prompt_tokens = (
                get_usage_value(
                    usage,
                    "prompt_tokens",
                )
            )

            completion_tokens = (
                get_usage_value(
                    usage,
                    "completion_tokens",
                )
            )

            total_tokens = (
                get_usage_value(
                    usage,
                    "total_tokens",
                    prompt_tokens
                    + completion_tokens,
                )
            )

            # -------------------------------------------------
            # CACHED TOKENS
            # -------------------------------------------------

            cache_read_tokens = (
                get_nested_usage_value(
                    usage,
                    "prompt_tokens_details",
                    "cached_tokens",
                )
            )

            # -------------------------------------------------
            # REASONING TOKENS
            # -------------------------------------------------

            reasoning_tokens = (
                get_nested_usage_value(
                    usage,
                    "completion_tokens_details",
                    "reasoning_tokens",
                )
            )

            # -------------------------------------------------
            # IMAGE TOKENS
            # -------------------------------------------------
            #
            # Groq's standard usage response reports total
            # prompt tokens. It does not reliably expose a
            # separate image-token count in the documented
            # usage structure.
            #
            # Therefore we DO NOT invent an image-token value.
            #

            input_image_tokens = 0

            # -------------------------------------------------
            # DEBUG USAGE
            # -------------------------------------------------

            print(
                "\n========== GROQ USAGE DEBUG =========="
            )

            print(
                "usage object:",
                usage,
            )

            print(
                "prompt_tokens:",
                prompt_tokens,
            )

            print(
                "completion_tokens:",
                completion_tokens,
            )

            print(
                "cached_tokens:",
                cache_read_tokens,
            )

            print(
                "reasoning_tokens:",
                reasoning_tokens,
            )

            print(
                "total_tokens:",
                total_tokens,
            )

            print(
                "image_tokens:",
                input_image_tokens,
            )

            print(
                "======================================\n"
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

                    "input_image":
                        input_image_tokens,

                    "input_image_source":
                        "not_separately_reported_by_provider",

                    "output":
                        completion_tokens,

                    "reasoning":
                        reasoning_tokens,

                    "cache_read":
                        cache_read_tokens,

                    "total":
                        total_tokens,
                },

                "latency": {
                    "provider_ms":
                        round(
                            provider_latency,
                            2,
                        ),

                    "ttfb_ms":
                        round(
                            ttfb,
                            2,
                        ),

                    "ttft_ms":
                        round(
                            ttft,
                            2,
                        ),

                    "stream_ms":
                        round(
                            stream_latency,
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

        # ========================================================
        # RATE LIMIT ERROR
        # ========================================================

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

        # ========================================================
        # CONNECTION ERROR
        # ========================================================

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

        # ========================================================
        # API STATUS ERROR
        # ========================================================

        except APIStatusError as exc:

            status_code = getattr(
                exc,
                "status_code",
                None,
            )

            # ----------------------------------------------------
            # Authentication / authorization errors
            # should NOT be retried.
            # ----------------------------------------------------

            if status_code in (
                401,
                403,
            ):

                raise

            last_error = exc

            print(
                f"Groq API error "
                f"(status={status_code}). "
                f"Attempt {attempt}/{MAX_RETRIES}"
            )

            if attempt < MAX_RETRIES:

                time.sleep(
                    2 ** attempt
                )

        # ========================================================
        # UNKNOWN ERROR
        # ========================================================

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