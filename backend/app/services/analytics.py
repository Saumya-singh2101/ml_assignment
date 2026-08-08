import json
import sqlite3
import math
from pathlib import Path
from datetime import datetime, timezone

from app.services.trace import write_trace


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "analytics.db"


# ============================================================
# CONFIG
# ============================================================

# Declared latency budget from the assignment.
LATENCY_BUDGET_MS = 8000.0


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    """
    Create the analytics database and migrate older databases
    when new metric columns are introduced.
    """

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE,
                created_at TEXT,
                success INTEGER,
                stroke_count INTEGER,
                image_size_bytes INTEGER,
                cv_latency_ms REAL,
                ai_latency_ms REAL,
                e2e_latency_ms REAL,
                ttfb_ms REAL,
                ttft_ms REAL,
                stream_ms REAL,
                input_tokens INTEGER,
                input_image_tokens INTEGER,
                output_tokens INTEGER,
                reasoning_tokens INTEGER,
                cache_read_tokens INTEGER,
                total_tokens INTEGER,
                cost_usd REAL,
                confidence REAL,
                outcome TEXT DEFAULT 'pending'
            )
            """
        )

        # --------------------------------------------------------
        # Migration for existing databases
        # --------------------------------------------------------

        existing_columns = {
            row[1]
            for row in cursor.execute(
                "PRAGMA table_info(analysis_metrics)"
            ).fetchall()
        }

        new_columns = {
            "ttfb_ms": "REAL",
            "ttft_ms": "REAL",
            "stream_ms": "REAL",
            "input_tokens": "INTEGER",
            "input_image_tokens": "INTEGER",
            "output_tokens": "INTEGER",
            "reasoning_tokens": "INTEGER",
            "cache_read_tokens": "INTEGER",
            "total_tokens": "INTEGER",
            "cost_usd": "REAL",
        }

        for column, data_type in new_columns.items():
            if column not in existing_columns:
                cursor.execute(
                    f"""
                    ALTER TABLE analysis_metrics
                    ADD COLUMN {column} {data_type}
                    """
                )

        conn.commit()

    finally:
        conn.close()


# ============================================================
# SAVE ANALYSIS METRIC
# ============================================================

def save_analysis_metric(
    request_id: str,
    success: bool,
    stroke_count: int,
    image_size_bytes: int,
    cv_latency_ms: float,
    ai_latency_ms: float,
    e2e_latency_ms: float,
    confidence: float,
    ttfb_ms: float = 0.0,
    ttft_ms: float = 0.0,
    stream_ms: float = 0.0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    cost_usd: float = 0.0,
    input_image_tokens: int = 0,
    reasoning_tokens: int = 0,
    cache_read_tokens: int = 0,
    trace: dict | None = None,
):
    """
    Save one analysis request's metrics.

    Supports:
    - latency
    - streaming metrics
    - token usage
    - image token usage
    - reasoning tokens
    - cache tokens
    - cost
    - confidence
    - trace information
    """

    init_db()

    conn = get_connection()
    created_at = datetime.now(timezone.utc).isoformat()

    initial_outcome = "pending" if success else "error"

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO analysis_metrics (
                request_id,
                created_at,
                success,
                stroke_count,
                image_size_bytes,
                cv_latency_ms,
                ai_latency_ms,
                e2e_latency_ms,
                ttfb_ms,
                ttft_ms,
                stream_ms,
                input_tokens,
                input_image_tokens,
                output_tokens,
                reasoning_tokens,
                cache_read_tokens,
                total_tokens,
                cost_usd,
                confidence,
                outcome
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                request_id,
                created_at,
                int(bool(success)),
                int(stroke_count or 0),
                int(image_size_bytes or 0),
                float(cv_latency_ms or 0.0),
                float(ai_latency_ms or 0.0),
                float(e2e_latency_ms or 0.0),
                float(ttfb_ms or 0.0),
                float(ttft_ms or 0.0),
                float(stream_ms or 0.0),
                int(input_tokens or 0),
                int(input_image_tokens or 0),
                int(output_tokens or 0),
                int(reasoning_tokens or 0),
                int(cache_read_tokens or 0),
                int(total_tokens or 0),
                float(cost_usd or 0.0),
                float(confidence or 0.0),
                initial_outcome,
            ),
        )

        conn.commit()

    finally:
        conn.close()

    # --------------------------------------------------------
    # TRACE
    # --------------------------------------------------------

    if trace is not None:
        trace_data = dict(trace)

        trace_data.setdefault(
            "request_id",
            request_id,
        )

        trace_data.setdefault(
            "ts_start",
            created_at,
        )

        trace_data.setdefault(
            "outcome",
            initial_outcome,
        )

        trace_data.setdefault(
            "error",
            None,
        )

        trace_data.setdefault(
            "retries",
            0,
        )

        try:
            write_trace(trace_data)

        except Exception as trace_error:
            # Trace failure should not break analytics.
            print(
                "Failed to write analytics trace:",
                trace_error,
            )


# ============================================================
# UPDATE OUTCOME
# ============================================================

def update_outcome(
    request_id: str,
    outcome: str,
):
    """
    Update the business outcome of an analysis request.

    Valid outcomes:
    - accepted
    - discarded
    - pending
    - cancelled
    - superseded
    - timeout
    - error
    """

    valid_outcomes = {
        "accepted",
        "discarded",
        "pending",
        "cancelled",
        "superseded",
        "timeout",
        "error",
    }

    if outcome not in valid_outcomes:
        raise ValueError(
            f"Invalid outcome: {outcome}"
        )

    init_db()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE analysis_metrics
            SET outcome = ?
            WHERE request_id = ?
            """,
            (
                outcome,
                request_id,
            ),
        )

        conn.commit()

    finally:
        conn.close()

    # Keep trace outcome synchronized.
    _update_trace_outcome(
        request_id,
        outcome,
    )


# ============================================================
# UPDATE TRACE OUTCOME
# ============================================================

def _update_trace_outcome(
    request_id: str,
    outcome: str,
):
    """
    Update the outcome of the corresponding trace.

    This is best-effort. Failure to update the trace should
    never break the main analytics request.
    """

    try:
        trace_file = (
            BASE_DIR
            / "traces"
            / "traces.jsonl"
        )

        if not trace_file.exists():
            return

        lines = trace_file.read_text(
            encoding="utf-8"
        ).splitlines()

        updated_lines = []

        for line in lines:

            if not line.strip():
                continue

            try:
                trace = json.loads(line)

            except Exception:
                updated_lines.append(line)
                continue

            if trace.get("request_id") == request_id:
                trace["outcome"] = outcome

            updated_lines.append(
                json.dumps(
                    trace,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )

        trace_file.write_text(
            "\n".join(updated_lines)
            + ("\n" if updated_lines else ""),
            encoding="utf-8",
        )

    except Exception as exc:
        print(
            "Failed to update trace outcome:",
            exc,
        )


# ============================================================
# PERCENTILE HELPER
# ============================================================

def percentile(
    values,
    percentile_value,
):
    """
    Calculate a percentile using linear interpolation.
    """

    if not values:
        return 0.0

    cleaned_values = []

    for value in values:

        if value is None:
            continue

        try:
            cleaned_values.append(
                float(value)
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

    if not cleaned_values:
        return 0.0

    values = sorted(cleaned_values)

    if len(values) == 1:
        return values[0]

    percentile_value = max(
        0.0,
        min(
            100.0,
            float(percentile_value),
        ),
    )

    rank = (
        percentile_value / 100.0
    ) * (len(values) - 1)

    lower = math.floor(rank)
    upper = math.ceil(rank)

    if lower == upper:
        return values[lower]

    weight = rank - lower

    return (
        values[lower]
        + weight
        * (
            values[upper]
            - values[lower]
        )
    )


# ============================================================
# LATENCY DISTRIBUTION
# ============================================================

def get_latency_statistics(
    cursor,
    column_name,
):
    """
    Return latency distribution statistics:

    p50
    p90
    p95
    p99
    max
    n
    """

    allowed_columns = {
        "cv_latency_ms",
        "ai_latency_ms",
        "ttfb_ms",
        "ttft_ms",
        "stream_ms",
        "e2e_latency_ms",
    }

    if column_name not in allowed_columns:
        raise ValueError(
            f"Invalid latency column: {column_name}"
        )

    cursor.execute(
        f"""
        SELECT {column_name}
        FROM analysis_metrics
        WHERE success = 1
        AND {column_name} IS NOT NULL
        AND {column_name} >= 0
        """
    )

    values = [
        row[0]
        for row in cursor.fetchall()
    ]

    return {
        "p50": round(
            percentile(values, 50),
            2,
        ),
        "p90": round(
            percentile(values, 90),
            2,
        ),
        "p95": round(
            percentile(values, 95),
            2,
        ),
        "p99": round(
            percentile(values, 99),
            2,
        ),
        "max": round(
            max(values)
            if values
            else 0.0,
            2,
        ),
        "n": len(values),
    }


# ============================================================
# ANALYTICS SUMMARY
# ============================================================

def get_analytics():
    """
    Return complete analytics and assignment KPIs.
    """

    init_db()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        # ====================================================
        # BASIC TOTALS
        # ====================================================

        cursor.execute(
            """
            SELECT
                COUNT(*),

                COALESCE(
                    SUM(success),
                    0
                ),

                COALESCE(
                    SUM(
                        CASE
                            WHEN outcome = 'accepted'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ),

                COALESCE(
                    SUM(
                        CASE
                            WHEN outcome = 'discarded'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ),

                COALESCE(
                    SUM(
                        CASE
                            WHEN outcome IN (
                                'discarded',
                                'cancelled',
                                'superseded',
                                'timeout',
                                'error'
                            )
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ),

                COALESCE(
                    SUM(input_tokens),
                    0
                ),

                COALESCE(
                    SUM(input_image_tokens),
                    0
                ),

                COALESCE(
                    SUM(output_tokens),
                    0
                ),

                COALESCE(
                    SUM(reasoning_tokens),
                    0
                ),

                COALESCE(
                    SUM(cache_read_tokens),
                    0
                ),

                COALESCE(
                    SUM(total_tokens),
                    0
                ),

                COALESCE(
                    SUM(cost_usd),
                    0
                ),

                COALESCE(
                    AVG(
                        CASE
                            WHEN success = 1
                            THEN confidence
                            ELSE NULL
                        END
                    ),
                    0
                )

            FROM analysis_metrics
            """
        )

        row = cursor.fetchone()

        (
            total_requests,
            successful_requests,
            accepted,
            discarded,
            wasted_requests,
            total_input_tokens,
            total_input_image_tokens,
            total_output_tokens,
            total_reasoning_tokens,
            total_cache_read_tokens,
            total_tokens,
            total_cost,
            avg_confidence,
        ) = row

        # ====================================================
        # DAR — DRAFT ACCEPTANCE RATE
        # ====================================================

        returned_drafts = (
            accepted + discarded
        )

        dar = (
            accepted / returned_drafts
            if returned_drafts > 0
            else 0.0
        )

        # ====================================================
        # CPAD — COST PER ACCEPTED DRAFT
        # ====================================================

        cpad = (
            total_cost / accepted
            if accepted > 0
            else 0.0
        )

        # ====================================================
        # WTR — WASTED TOKEN RATIO
        # ====================================================

        cursor.execute(
            """
            SELECT COALESCE(
                SUM(
                    CASE
                        WHEN outcome IN (
                            'discarded',
                            'cancelled',
                            'superseded',
                            'timeout',
                            'error'
                        )
                        THEN COALESCE(
                            total_tokens,
                            0
                        )
                        ELSE 0
                    END
                ),
                0
            )
            FROM analysis_metrics
            """
        )

        wasted_tokens = (
            cursor.fetchone()[0]
            or 0
        )

        wtr = (
            wasted_tokens / total_tokens
            if total_tokens > 0
            else 0.0
        )

        # ====================================================
        # BUDGET COMPLIANCE
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM analysis_metrics
            WHERE success = 1
            AND e2e_latency_ms IS NOT NULL
            AND e2e_latency_ms >= 0
            AND e2e_latency_ms <= ?
            """,
            (LATENCY_BUDGET_MS,),
        )

        requests_within_budget = (
            cursor.fetchone()[0]
            or 0
        )

        budget_compliance = (
            requests_within_budget
            / successful_requests
            if successful_requests > 0
            else 0.0
        )

        # ====================================================
        # LATENCY STATISTICS
        # ====================================================

        latency_columns = {
            "capture": "cv_latency_ms",
            "ai": "ai_latency_ms",
            "ttfb": "ttfb_ms",
            "ttft": "ttft_ms",
            "stream": "stream_ms",
            "e2e": "e2e_latency_ms",
        }

        latency_statistics = {}

        for name, column in (
            latency_columns.items()
        ):
            latency_statistics[name] = (
                get_latency_statistics(
                    cursor,
                    column,
                )
            )

        # ====================================================
        # AVERAGE LATENCIES
        # ====================================================

        cursor.execute(
            """
            SELECT

                COALESCE(
                    AVG(
                        CASE
                            WHEN success = 1
                            THEN cv_latency_ms
                            ELSE NULL
                        END
                    ),
                    0
                ),

                COALESCE(
                    AVG(
                        CASE
                            WHEN success = 1
                            THEN ai_latency_ms
                            ELSE NULL
                        END
                    ),
                    0
                ),

                COALESCE(
                    AVG(
                        CASE
                            WHEN success = 1
                            THEN e2e_latency_ms
                            ELSE NULL
                        END
                    ),
                    0
                ),

                COALESCE(
                    AVG(
                        CASE
                            WHEN success = 1
                            THEN ttfb_ms
                            ELSE NULL
                        END
                    ),
                    0
                ),

                COALESCE(
                    AVG(
                        CASE
                            WHEN success = 1
                            THEN ttft_ms
                            ELSE NULL
                        END
                    ),
                    0
                ),

                COALESCE(
                    AVG(
                        CASE
                            WHEN success = 1
                            THEN stream_ms
                            ELSE NULL
                        END
                    ),
                    0
                )

            FROM analysis_metrics
            """
        )

        averages = cursor.fetchone()

        (
            avg_cv,
            avg_ai,
            avg_e2e,
            avg_ttfb,
            avg_ttft,
            avg_stream,
        ) = averages

        # ====================================================
        # FINAL ANALYTICS RESPONSE
        # ====================================================

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,

            # ------------------------------------------------
            # LATENCY
            # ------------------------------------------------

            "latency": {
                "statistics": latency_statistics,

                "average": {
                    "capture_ms": round(
                        avg_cv,
                        2,
                    ),
                    "ai_ms": round(
                        avg_ai,
                        2,
                    ),
                    "e2e_ms": round(
                        avg_e2e,
                        2,
                    ),
                    "ttfb_ms": round(
                        avg_ttfb,
                        2,
                    ),
                    "ttft_ms": round(
                        avg_ttft,
                        2,
                    ),
                    "stream_ms": round(
                        avg_stream,
                        2,
                    ),
                },

                "budget_ms": (
                    LATENCY_BUDGET_MS
                ),
            },

            # ------------------------------------------------
            # TOKENS
            # ------------------------------------------------

            "tokens": {
                "input_text": (
                    total_input_tokens
                ),
                "input_image": (
                    total_input_image_tokens
                ),
                "output": (
                    total_output_tokens
                ),
                "reasoning": (
                    total_reasoning_tokens
                ),
                "cache_read": (
                    total_cache_read_tokens
                ),
                "total": total_tokens,
            },

            # ------------------------------------------------
            # COST
            # ------------------------------------------------

            "cost_usd": round(
                total_cost,
                8,
            ),

            # ------------------------------------------------
            # QUALITY
            # ------------------------------------------------

            "confidence": round(
                avg_confidence,
                3,
            ),

            "accepted": accepted,

            "discarded": discarded,

            "wasted_requests": (
                wasted_requests
            ),

            # ------------------------------------------------
            # ASSIGNMENT KPIs
            # ------------------------------------------------

            "kpis": {
                # Cost Per Accepted Draft
                "CPAD": round(
                    cpad,
                    8,
                ),

                # Draft Acceptance Rate
                "DAR": round(
                    dar,
                    4,
                ),

                # Wasted Token Ratio
                "WTR": round(
                    wtr,
                    4,
                ),

                # Budget Compliance
                "BC": round(
                    budget_compliance,
                    4,
                ),
            },

            # ------------------------------------------------
            # BUDGET
            # ------------------------------------------------

            "budget": {
                "latency_budget_ms": (
                    LATENCY_BUDGET_MS
                ),

                "requests_within_budget": (
                    requests_within_budget
                ),

                "budget_compliance": round(
                    budget_compliance,
                    4,
                ),
            },
        }

    finally:
        conn.close()