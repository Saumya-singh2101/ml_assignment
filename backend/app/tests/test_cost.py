from app.services.cost import calculate_cost


def test_cost_calculation():
    cost = calculate_cost(
        input_tokens=1000,
        output_tokens=500,
        reasoning_tokens=200,
        input_rate_per_million=1.0,
        output_rate_per_million=2.0,
    )

    expected = (
        1000 * 1.0 / 1_000_000
        + 500 * 2.0 / 1_000_000
        + 200 * 2.0 / 1_000_000
    )

    assert cost == round(expected, 8)