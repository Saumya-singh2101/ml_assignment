import base64
import json
import os
import re

from groq import Groq

from app.core.config import GROQ_API_KEY, MODEL_NAME


client = Groq(api_key=GROQ_API_KEY)


def clean_model_output(text: str) -> str:
    """
    Remove Qwen reasoning/thinking blocks from the response.
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

    # Remove any accidental leftover tags
    text = re.sub(
        r"</?think>",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


def extract_json(text: str):
    """
    Extract JSON object from model response.
    """

    text = clean_model_output(text)

    # Direct JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # JSON inside markdown code block
    match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        flags=re.DOTALL,
    )

    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Find first {...}
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        try:
            return json.loads(
                text[start : end + 1]
            )
        except Exception:
            pass

    return None


def analyze_canvas(
    image_base64: str,
    context: dict,
):
    prompt = f"""
You are an AI whiteboard assistant.

Analyze the handwritten canvas image.

Identify:
- equations
- mathematical expressions
- diagrams
- handwritten ideas
- text

If there is an equation, solve it step by step.

Return ONLY valid JSON.

Do NOT include:
- <think>
- </think>
- reasoning outside JSON
- markdown code fences

Use exactly this structure:

{{
    "title": "short title",
    "content": "clear step-by-step explanation",
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

{json.dumps(context)}
"""

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
                            "url": (
                                "data:image/png;base64,"
                                + image_base64
                            )
                        },
                    },
                ],
            }
        ],
        temperature=0.1,
    )

    raw = response.choices[0].message.content or ""

    print("RAW AI RESPONSE:")
    print(raw)

    result = extract_json(raw)

    if result is None:
        return {
            "title": "AI Analysis",
            "content": clean_model_output(raw),
            "latex": None,
            "format": "markdown",
            "confidence": 0.5,
            "x": 530,
            "y": 100,
            "width": 400,
            "height": 250,
            "status": "draft",
        }

    return result