from __future__ import annotations

from mgc_bt.optimization.monte_carlo import run_monte_carlo_analysis


def _trade_log() -> list[dict[str, float]]:
    return [
        {"realized_pnl": 120.0},
        {"realized_pnl": -40.0},
        {"realized_pnl": 80.0},
        {"realized_pnl": -20.0},
        {"realized_pnl": 60.0},
    ]


def test_run_monte_carlo_analysis_is_deterministic_for_permutation_and_bootstrap() -> None:
    first = run_monte_carlo_analysis(
        _trade_log(),
        simulations=64,
        seed=10042,
        percentiles=(5, 25, 50, 75, 95),
        confidence_level=0.95,
    )
    second = run_monte_carlo_analysis(
        _trade_log(),
        simulations=64,
        seed=10042,
        percentiles=(5, 25, 50, 75, 95),
        confidence_level=0.95,
    )

    assert first == second
    assert first["status"] == "completed"
    assert first["permutation"]["method"] == "permutation"
    assert first["bootstrap"]["method"] == "bootstrap"
    assert first["permutation"]["sample_size"] == 5
    assert first["bootstrap"]["sample_size"] == 5
    assert first["permutation"]["p_value"] == 1.0
    assert first["permutation"]["pass_95"] is False
    assert first["bootstrap"]["p_value"] == 0.078125
    assert first["bootstrap"]["pass_95"] is False


def test_run_monte_carlo_analysis_reports_skip_for_tiny_trade_logs() -> None:
    result = run_monte_carlo_analysis(
        [{"realized_pnl": 10.0}],
        simulations=10,
        seed=10042,
        percentiles=(5, 25, 50, 75, 95),
        confidence_level=0.95,
    )

    assert result["status"] == "skipped"
    assert result["skipped_reason"] == "insufficient_trades"
