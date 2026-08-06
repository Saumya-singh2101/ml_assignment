def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int,
    input_rate_per_million: float,
    output_rate_per_million: float,
) -> float:
    input_cost = (
        input_tokens * input_rate_per_million
    ) / 1_000_000

    output_cost = (
        output_tokens * output_rate_per_million
    ) / 1_000_000

    reasoning_cost = (
        reasoning_tokens * output_rate_per_million
    ) / 1_000_000

    return round(
        input_cost + output_cost + reasoning_cost,
        8,
    )