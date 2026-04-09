from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import json
import shutil
from typing import Any

import pandas as pd

from mgc_bt.backtest.plotting import save_equity_curve_png
from mgc_bt.config import Settings


def write_backtest_artifacts(settings: Settings, result: dict[str, Any]) -> dict[str, Path]:
    backtests_root = settings.paths.results_root / settings.backtest.results_subdir
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d_%H%M%S")
    run_dir = backtests_root / timestamp
    latest_dir = backtests_root / "latest"

    run_dir.mkdir(parents=True, exist_ok=False)
    summary_path = run_dir / "summary.json"
    trades_path = run_dir / "trades.csv"
    config_path = run_dir / "run_config.toml"
    plot_path = run_dir / "equity_curve.png"

    summary_payload = _summary_payload(result)
    summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    trades_frame = pd.DataFrame.from_records(result.get("trade_log", []))
    trades_frame.to_csv(trades_path, index=False)

    config_path.write_text(_render_run_config_toml(settings, result), encoding="utf-8")
    save_equity_curve_png(result["equity_curve"], plot_path)

    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    shutil.copytree(run_dir, latest_dir)

    return {
        "run_dir": run_dir,
        "latest_dir": latest_dir,
        "summary_path": summary_path,
        "trades_path": trades_path,
        "config_path": config_path,
        "plot_path": plot_path,
    }


def _summary_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": result["mode"],
        "instrument_id": result["instrument_id"],
        "segment_instruments": result["segment_instruments"],
        "segment_count": result["segment_count"],
        "start_date": result["start_date"],
        "end_date": result["end_date"],
        "total_pnl": result["total_pnl"],
        "sharpe_ratio": result["sharpe_ratio"],
        "win_rate": result["win_rate"],
        "max_drawdown": result["max_drawdown"],
        "max_drawdown_pct": result.get("max_drawdown_pct"),
        "total_trades": result["total_trades"],
        "parameters": result["parameters"],
        "strategy_parameters": result["parameters"],
        "segments": result["segments"],
    }


def _render_run_config_toml(settings: Settings, result: dict[str, Any]) -> str:
    params = result["parameters"]
    lines = [
        "[paths]",
        f'project_root = "{settings.paths.project_root.as_posix()}"',
        f'data_root = "{settings.paths.data_root.as_posix()}"',
        f'catalog_root = "{settings.paths.catalog_root.as_posix()}"',
        f'results_root = "{settings.paths.results_root.as_posix()}"',
        "",
        "[ingestion]",
        f'dataset = "{settings.ingestion.dataset}"',
        f'symbol = "{settings.ingestion.symbol}"',
        f'bar_schema = "{settings.ingestion.bar_schema}"',
        f'trade_schema = "{settings.ingestion.trade_schema}"',
        f'definition_schema = "{settings.ingestion.definition_schema}"',
        f"load_definitions = {_toml_bool(settings.ingestion.load_definitions)}",
        f"load_bars = {_toml_bool(settings.ingestion.load_bars)}",
        f"load_trades = {_toml_bool(settings.ingestion.load_trades)}",
        f"load_mbp1 = {_toml_bool(settings.ingestion.load_mbp1)}",
        f'definitions_glob = "{settings.ingestion.definitions_glob}"',
        f'bars_glob = "{settings.ingestion.bars_glob}"',
        f'trades_glob = "{settings.ingestion.trades_glob}"',
        f'mbp1_glob = "{settings.ingestion.mbp1_glob}"',
        "",
        "[backtest]",
        f'default_mode = "{settings.backtest.default_mode}"',
        f'venue_name = "{settings.backtest.venue_name}"',
        f'oms_type = "{settings.backtest.oms_type}"',
        f'account_type = "{settings.backtest.account_type}"',
        f'base_currency = "{settings.backtest.base_currency}"',
        f'starting_balance = "{settings.backtest.starting_balance}"',
        f"default_leverage = {settings.backtest.default_leverage}",
        f'trade_size = "{params["trade_size"]}"',
        f'results_subdir = "{settings.backtest.results_subdir}"',
        f'roll_preference = "{settings.backtest.roll_preference}"',
        f"calendar_roll_business_days = {settings.backtest.calendar_roll_business_days}",
        f'start_date = "{params["start_date"] or ""}"',
        f'end_date = "{params["end_date"] or ""}"',
        f"commission_per_side = {settings.backtest.commission_per_side}",
        f"slippage_ticks = {settings.backtest.slippage_ticks}",
        "",
        "[risk]",
        f'native_max_order_submit_rate = "{settings.risk.native_max_order_submit_rate}"',
        f'native_max_order_modify_rate = "{settings.risk.native_max_order_modify_rate}"',
        f"native_max_notional_per_order = {_render_notional_table(settings.risk.native_max_notional_per_order)}",
        f"max_loss_per_trade_dollars = {params['max_loss_per_trade_dollars']}",
        f"max_daily_trades = {params['max_daily_trades']}",
        f"max_daily_loss_dollars = {params['max_daily_loss_dollars']}",
        f"max_consecutive_losses = {params['max_consecutive_losses']}",
        f"max_drawdown_pct = {params['max_drawdown_pct']}",
        "",
        "[optimization]",
        f'study_name = "{settings.optimization.study_name}"',
        f'direction = "{settings.optimization.direction}"',
        "",
        "[run]",
        f'mode = "{result["mode"]}"',
        f'instrument_id = "{params["instrument_id"] or ""}"',
        f'roll_source = "{params["roll_source"]}"',
    ]
    return "\n".join(lines) + "\n"


def _toml_bool(value: bool) -> str:
    return "true" if value else "false"


def _render_notional_table(values: dict[str, int]) -> str:
    if not values:
        return "{}"
    inner = ", ".join(f'"{key}" = {value}' for key, value in sorted(values.items()))
    return "{ " + inner + " }"
