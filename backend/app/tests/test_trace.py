from datetime import datetime, timezone

from app.models.trace import (
    InputMetrics,
    LatencyMetrics,
    Outcome,
    TokenMetrics,
    TraceRecord,
)


def test_trace_round_trip():
    trace = TraceRecord(
        request_id="req_test",
        session_id="ses_test",
        ts_start=datetime.now(timezone.utc),
        trigger="explicit",
        provider="test",
        model="test-model",
        input=InputMetrics(
            crop_px=[1024, 768],
            format="webp",
            bytes=1000,
            zoom=1.0,
            stroke_count=20,
            prompt_chars=100,
        ),
        latency_ms=LatencyMetrics(
            t_capture=10,
            t_dispatch=20,
            ttfb=100,
            ttft=150,
            t_stream=500,
            t_render=20,
            e2e=700,
        ),
        tokens=TokenMetrics(
            input_text=100,
            input_image=200,
            output=50,
            reasoning=0,
            cache_read=0,
            total=350,
        ),
        cost_usd=0.001,
        outcome=Outcome.ACCEPTED,
    )

    payload = trace.model_dump(
        mode="json"
    )

    restored = TraceRecord.model_validate(
        payload
    )

    assert restored.request_id == "req_test"
    assert restored.tokens.total == 350
    assert restored.latency_ms.e2e == 700