from app.services.statistics import (
    percentile_summary,
)


def test_percentiles():
    result = percentile_summary(
        [1, 2, 3, 4, 5]
    )

    assert result["n"] == 5
    assert result["p50"] == 3
    assert result["max"] == 5