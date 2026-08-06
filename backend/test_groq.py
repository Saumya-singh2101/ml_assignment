from app.services.groq_client import client
from app.core.config import MODEL_NAME


response = client.chat.completions.create(
    model=MODEL_NAME,
    messages=[
        {
            "role": "user",
            "content": "Explain what SLATE is in one sentence."
        }
    ],
    max_completion_tokens=100,
)


print(response.choices[0].message.content)