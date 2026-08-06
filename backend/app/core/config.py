import os

from dotenv import load_dotenv


load_dotenv()


APP_NAME = os.getenv(
    "APP_NAME",
    "SLATE Backend",
)

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "development",
)

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

TRACE_DIR = os.getenv(
    "TRACE_DIR",
    "traces",
)

LATENCY_BUDGET_MS = int(
    os.getenv(
        "LATENCY_BUDGET_MS",
        "8000",
    )
)

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "qwen/qwen3.6-27b",
)

INPUT_RATE_PER_MILLION = float(
    os.getenv(
        "INPUT_RATE_PER_MILLION",
        "0.60",
    )
)

OUTPUT_RATE_PER_MILLION = float(
    os.getenv(
        "OUTPUT_RATE_PER_MILLION",
        "3.00",
    )
)

IMAGE_TOKEN_RATE_MODE = os.getenv(
    "IMAGE_TOKEN_RATE_MODE",
    "estimated",
)


if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not configured. "
        "Add it to backend/.env"
    )