from __future__ import annotations

from pathlib import Path
import json

from mgc_bt.backtest.runner import run_backtest
from mgc_bt.config import load_settings


def test_mgc_strategy_matches_golden_fixture_exactly() -> None:
    fixture = json.loads(Path("tests/fixtures/mgc_golden_output.json").read_text(encoding="utf-8"))
    settings = load_settings("configs/settings.toml")

    result = run_backtest(
        settings,
        {
            "instrument_id": fixture["instrument_id"],
            "start_date": fixture["start_date"],
            "end_date": fixture["end_date"],
        },
    )

    assert result["total_pnl"] == fixture["metrics"]["total_pnl"]
    assert result["sharpe_ratio"] == fixture["metrics"]["sharpe_ratio"]
    assert result["total_trades"] == fixture["metrics"]["total_trades"]
    assert result["win_rate"] == fixture["metrics"]["win_rate"]
    assert result["max_drawdown"] == fixture["metrics"]["max_drawdown"]
