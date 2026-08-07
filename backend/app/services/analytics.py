import sqlite3
from pathlib import Path
from datetime import datetime, timezone


# Database location
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "analytics.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


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

            confidence REAL,

            outcome TEXT DEFAULT 'pending'
        )
        """
    )

    conn.commit()
    conn.close()


def save_analysis_metric(
    request_id: str,
    success: bool,
    stroke_count: int,
    image_size_bytes: int,
    cv_latency_ms: float,
    ai_latency_ms: float,
    e2e_latency_ms: float,
    confidence: float,
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
            confidence,
            outcome
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            confidence,
            "pending",
        ),
    )

    conn.commit()
    conn.close()


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