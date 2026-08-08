import json
from pathlib import Path
from threading import Lock


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

TRACE_DIR = BASE_DIR / "traces"

TRACE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

TRACE_FILE = TRACE_DIR / "traces.jsonl"


# ============================================================
# THREAD SAFETY
# ============================================================

_trace_lock = Lock()


# ============================================================
# FORBIDDEN TRACE KEYS
# ============================================================

FORBIDDEN_KEYS = {
    "api_key",
    "groq_api_key",
    "authorization",
    "token",
    "secret",
    "password",
    "image_base64",
    "processed_image_base64",
}


# ============================================================
# SENSITIVE DATA CHECK
# ============================================================

def contains_forbidden_key(value):
    """
    Recursively check whether a trace contains
    sensitive credentials or raw image data.
    """

    if isinstance(value, dict):

        for key, child in value.items():

            if key.lower() in FORBIDDEN_KEYS:
                return True

            if contains_forbidden_key(child):
                return True

    elif isinstance(value, list):

        for child in value:

            if contains_forbidden_key(child):
                return True

    return False


# ============================================================
# TRACE WRITER
# ============================================================

def write_trace(trace: dict):
    """
    Append exactly one JSON object per line.

    IMPORTANT:
    - Never store API keys.
    - Never store authorization headers.
    - Never store raw image/base64 data.
    - Only store metadata and metrics.
    """

    if not isinstance(trace, dict):

        raise TypeError(
            "Trace must be a dictionary."
        )

    # --------------------------------------------------------
    # Security check
    # --------------------------------------------------------

    if contains_forbidden_key(trace):

        raise ValueError(
            "Trace contains potentially sensitive data."
        )

    # --------------------------------------------------------
    # Thread-safe append
    # --------------------------------------------------------

    with _trace_lock:

        with open(
            TRACE_FILE,
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                json.dumps(
                    trace,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )

            file.flush()
