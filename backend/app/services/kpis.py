from typing import Iterable

from app.models.trace import Outcome, TraceRecord


def calculate_cpad(
    traces: Iterable[TraceRecord],
) -> float:
    traces = list(traces)

    total_spend = sum(
        trace.cost_usd
        for trace in traces
    )

    accepted = sum(
        trace.outcome == Outcome.ACCEPTED
        for trace in traces
    )

    if accepted == 0:
        return 0.0

    return total_spend / accepted


def calculate_dar(
    traces: Iterable[TraceRecord],
) -> float:
    traces = list(traces)

    returned = sum(
        trace.outcome
        in {
            Outcome.ACCEPTED,
            Outcome.DISCARDED,
        }
        for trace in traces
    )

    accepted = sum(
        trace.outcome == Outcome.ACCEPTED
        for trace in traces
    )

    if returned == 0:
        return 0.0

    return accepted / returned


def calculate_wtr(
    traces: Iterable[TraceRecord],
) -> float:
    traces = list(traces)

    total_tokens = sum(
        trace.tokens.total
        for trace in traces
    )

    wasted_outcomes = {
        Outcome.DISCARDED,
        Outcome.CANCELLED,
        Outcome.SUPERSEDED,
        Outcome.TIMEOUT,
        Outcome.ERROR,
    }

    wasted_tokens = sum(
        trace.tokens.total
        for trace in traces
        if trace.outcome in wasted_outcomes
    )

    if total_tokens == 0:
        return 0.0

    return wasted_tokens / total_tokens


def calculate_budget_compliance(
    traces: Iterable[TraceRecord],
    budget_ms: float,
) -> float:
    traces = list(traces)

    if not traces:
        return 0.0

    within_budget = sum(
        trace.latency_ms.e2e <= budget_ms
        for trace in traces
    )

    return within_budget / len(traces)


def calculate_all_kpis(
    traces: Iterable[TraceRecord],
    budget_ms: float,
) -> dict[str, float]:
    traces = list(traces)

    return {
        "cpad_usd": calculate_cpad(traces),
        "dar": calculate_dar(traces),
        "wtr": calculate_wtr(traces),
        "bc": calculate_budget_compliance(
            traces,
            budget_ms,
        ),
    }