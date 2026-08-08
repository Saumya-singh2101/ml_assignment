
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# DATABASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "analytics.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    conn = get_connection()
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
            output_tokens INTEGER,
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
        "output_tokens": "INTEGER",
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
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO analysis_metrics (
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
            output_tokens,
            total_tokens,

            cost_usd,

            confidence,
            outcome
        )
        VALUES (
            ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?,
            ?, ?
        )
        """,
        (
            request_id,
            datetime.now(timezone.utc).isoformat(),
            int(success),

            stroke_count,
            image_size_bytes,

            cv_latency_ms,
            ai_latency_ms,
            e2e_latency_ms,

            ttfb_ms,
            ttft_ms,
            stream_ms,

            input_tokens,
            output_tokens,
            total_tokens,

            cost_usd,

            confidence,
            "pending",
        ),
    )

    conn.commit()
    conn.close()


# ============================================================
# UPDATE OUTCOME
# ============================================================

def update_outcome(
    request_id: str,
    outcome: str,
):

    if outcome not in {
        "accepted",
        "discarded",
        "pending",
    }:
        raise ValueError(
            "Invalid outcome."
        )

    conn = get_connection()
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
    conn.close()


# ============================================================
# ANALYTICS SUMMARY
# ============================================================

def get_analytics():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            COUNT(*) AS total_requests,

            COALESCE(
                SUM(success),
                0
            ) AS successful_requests,

            COALESCE(
                AVG(cv_latency_ms),
                0
            ) AS avg_cv_latency_ms,

            COALESCE(
                AVG(ai_latency_ms),
                0
            ) AS avg_ai_latency_ms,

            COALESCE(
                AVG(e2e_latency_ms),
                0
            ) AS avg_e2e_latency_ms,

            COALESCE(
                AVG(ttfb_ms),
                0
            ) AS avg_ttfb_ms,

            COALESCE(
                AVG(ttft_ms),
                0
            ) AS avg_ttft_ms,

            COALESCE(
                AVG(stream_ms),
                0
            ) AS avg_stream_ms,

            COALESCE(
                SUM(input_tokens),
                0
            ) AS total_input_tokens,

            COALESCE(
                SUM(output_tokens),
                0
            ) AS total_output_tokens,

            COALESCE(
                SUM(total_tokens),
                0
            ) AS total_tokens,

            COALESCE(
                SUM(cost_usd),
                0
            ) AS total_cost_usd,

            COALESCE(
                AVG(confidence),
                0
            ) AS avg_confidence,

            COALESCE(
                SUM(
                    CASE
                        WHEN outcome = 'accepted'
                        THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS accepted,

            COALESCE(
                SUM(
                    CASE
                        WHEN outcome = 'discarded'
                        THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS discarded

        FROM analysis_metrics
        """
    )

    row = cursor.fetchone()

    conn.close()

    (
        total,
        successful,
        avg_cv,
        avg_ai,
        avg_e2e,

        avg_ttfb,
        avg_ttft,
        avg_stream,

        total_input_tokens,
        total_output_tokens,
        total_tokens,

        total_cost,

        avg_confidence,

        accepted,
        discarded,
    ) = row

    decided = accepted + discarded

    acceptance_rate = (
        accepted / decided
        if decided > 0
        else 0
    )

    return {
        "total_requests": total,

        "successful_requests": successful,

        "latency": {
            "average_cv_latency_ms": round(
                avg_cv,
                2,
            ),

            "average_ai_latency_ms": round(
                avg_ai,
                2,
            ),

            "average_e2e_latency_ms": round(
                avg_e2e,
                2,
            ),

            "average_ttfb_ms": round(
                avg_ttfb,
                2,
            ),

            "average_ttft_ms": round(
                avg_ttft,
                2,
            ),

            "average_stream_ms": round(
                avg_stream,
                2,
            ),
        },

        "tokens": {
            "total_input_tokens": total_input_tokens,

            "total_output_tokens": total_output_tokens,

            "total_tokens": total_tokens,
        },

        "cost_usd": round(
            total_cost,
            8,
        ),

        "average_confidence": round(
            avg_confidence,
            3,
        ),

        "accepted": accepted,

        "discarded": discarded,

        "acceptance_rate": round(
            acceptance_rate,
            3,
        ),
    }
