from typing import Iterable

import numpy as np


def percentile_summary(
    values: Iterable[float],
) -> dict[str, float | int]:
    values = list(values)

    if not values:
        return {
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "max": 0.0,
            "n": 0,
        }

    array = np.array(values, dtype=float)

    return {
        "p50": float(np.percentile(array, 50)),
        "p90": float(np.percentile(array, 90)),
        "p95": float(np.percentile(array, 95)),
        "p99": float(np.percentile(array, 99)),
        "max": float(np.max(array)),
        "n": int(len(array)),
    }


def latency_statistics(
    traces,
) -> dict[str, dict]:
    return {
        "t_capture": percentile_summary(
            trace.latency_ms.t_capture
            for trace in traces
        ),
        "t_dispatch": percentile_summary(
            trace.latency_ms.t_dispatch
            for trace in traces
        ),
        "ttfb": percentile_summary(
            trace.latency_ms.ttfb
            for trace in traces
        ),
        "ttft": percentile_summary(
            trace.latency_ms.ttft
            for trace in traces
        ),
        "t_stream": percentile_summary(
            trace.latency_ms.t_stream
            for trace in traces
        ),
        "t_render": percentile_summary(
            trace.latency_ms.t_render
            for trace in traces
        ),
        "e2e": percentile_summary(
            trace.latency_ms.e2e
            for trace in traces
        ),
    }