from datetime import datetime, timezone

from app.models.trace import (
    InputMetrics,
    LatencyMetrics,
    Outcome,
    TokenMetrics,
    TraceRecord,
)
from app.services.kpis import (
    calculate_all_kpis,
)


def make_trace(
    outcome: Outcome,
    cost: float,
    tokens: int,
    e2e: float,
):
    return TraceRecord(
        request_id="req_test",
        session_id="ses_test",
        ts_start=datetime.now(timezone.utc),
        trigger="explicit",
        provider="test",
        model="test",
        input=InputMetrics(),
        latency_ms=LatencyMetrics(
            e2e=e2e
        ),
        tokens=TokenMetrics(
            total=tokens
        ),
        cost_usd=cost,
        outcome=outcome,
    )


def test_kpis():
    traces = [
        make_trace(
            Outcome.ACCEPTED,
            1.0,
            100,
            5000,
        ),
        make_trace(
            Outcome.DISCARDED,
            0.5,
            100,
            9000,
        ),
        make_trace(
            Outcome.CANCELLED,
            0.25,
            50,
            3000,
        ),
    ]

    kpis = calculate_all_kpis(
        traces,
        budget_ms=8000,
    )

    assert kpis["cpad_usd"] == 1.75

    assert kpis["dar"] == 0.5

    assert kpis["wtr"] == 0.5

    assert kpis["bc"] == 2 / 3