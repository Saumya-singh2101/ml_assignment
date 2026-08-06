from fastapi import APIRouter

from app.core.config import settings
from app.services.kpis import calculate_all_kpis
from app.services.statistics import latency_statistics
from app.storage.traces import TraceStore


router = APIRouter(
    prefix="/api/metrics",
    tags=["Metrics"],
)

trace_store = TraceStore(
    settings.trace_dir
)


@router.get("")
def get_metrics():
    traces = trace_store.read_all()

    total_cost = sum(
        trace.cost_usd
        for trace in traces
    )

    total_tokens = sum(
        trace.tokens.total
        for trace in traces
    )

    return {
        "session": {
            "requests": len(traces),
            "total_tokens": total_tokens,
            "total_cost_usd": round(
                total_cost,
                8,
            ),
        },
        "latency": latency_statistics(
            traces
        ),
        "kpis": calculate_all_kpis(
            traces,
            settings.latency_budget_ms,
        ),
        "latency_budget_ms": (
            settings.latency_budget_ms
        ),
    }


@router.get("/traces")
def get_traces():
    traces = trace_store.read_all()

    return {
        "count": len(traces),
        "traces": [
            trace.model_dump(
                mode="json"
            )
            for trace in traces
        ],
    }