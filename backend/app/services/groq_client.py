import base64

from groq import Groq

from app.core.config import (
    GROQ_API_KEY,
    MODEL_NAME,
)


client = Groq(
    api_key=GROQ_API_KEY
)


def analyze_canvas(
    image_bytes: bytes,
    prompt: str,
):

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    response = client.chat.completions.create(

        model=MODEL_NAME,

        messages=[
            {
                "role": "system",
                "content": """
You are the AI assistant inside SLATE,
an AI-powered spatial canvas.

Analyze the user's canvas region.

The region may contain:
- handwriting
- equations
- diagrams
- arrows
- sketches
- notes
- mixed content

Return ONLY JSON:

{
    "title": "short title",
    "content": "useful response in markdown",
    "latex": null,
    "format": "markdown",
    "confidence": 0.0
}

Do not invent information that is not visible.
If the content is ambiguous, explicitly mention
the ambiguity.
"""
            },
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
                                f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],

        temperature=0.2,

        max_completion_tokens=1024,
    )

    return response