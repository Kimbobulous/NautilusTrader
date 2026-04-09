from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import csv
import json
import shutil
import sys
from typing import Any, Iterable

from mgc_bt.backtest.analytics import BacktestAnalyticsBundle
from mgc_bt.backtest.analytics import write_backtest_analytics
from mgc_bt.backtest.plotting import save_equity_curve_png
from mgc_bt.config import Settings
from mgc_bt.reporting import write_tearsheet


def write_backtest_artifacts(
    settings: Settings,
    result: dict[str, Any],
    *,
    refresh_latest: bool = True,
    run_dir: Path | None = None,
) -> dict[str, Path | None]:
    backtests_root = settings.paths.results_root / settings.backtest.results_subdir
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d_%H%M%S")
    run_dir = run_dir or create_unique_timestamped_dir(backtests_root, timestamp)
    latest_dir = backtests_root / "latest"

    summary_path = run_dir / "summary.json"
    trades_path = run_dir / "trades.csv"
    config_path = run_dir / "run_config.toml"
    plot_path = run_dir / "equity_curve.png"
    manifest_path = run_dir / "manifest.json"

    persist_backtest_bundle(
        settings=settings,
        result=result,
        run_dir=run_dir,
    )

    analytics_files: list[Path] = []
    try:
        analytics_bundle = write_backtest_analytics(result, run_dir)
        analytics_files = analytics_bundle.files
    except Exception as exc:
        print(f"Warning: analytics generation failed for backtest run: {exc}", file=sys.stderr)

    tearsheet_path: Path | None = None
    try:
        tearsheet_path = write_tearsheet(run_dir)
    except FileNotFoundError as exc:
        print(f"Warning: tearsheet generation failed for backtest run: {exc}", file=sys.stderr)
    except Exception as exc:
        print(f"Warning: tearsheet generation failed for backtest run: {exc}", file=sys.stderr)

    write_manifest(
        run_dir,
        [summary_path, trades_path, config_path, plot_path, *analytics_files, *([tearsheet_path] if tearsheet_path else [])],
        latest_refreshed=refresh_latest,
    )
    refreshed_latest_dir = refresh_latest_dir(run_dir, refresh_latest=refresh_latest)

    return {
        "run_dir": run_dir,
        "latest_dir": refreshed_latest_dir,
        "summary_path": summary_path,
        "trades_path": trades_path,
        "config_path": config_path,
        "plot_path": plot_path,
        "tearsheet_path": tearsheet_path,
        "manifest_path": manifest_path,
    }


def persist_backtest_bundle(
    settings: Settings,
    result: dict[str, Any],
    run_dir: Path,
    summary_filename: str = "summary.json",
    trades_filename: str = "trades.csv",
    plot_filename: str = "equity_curve.png",
    config_filename: str = "run_config.toml",
) -> dict[str, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / summary_filename
    trades_path = run_dir / trades_filename
    config_path = run_dir / config_filename
    plot_path = run_dir / plot_filename

    summary_path.write_text(json.dumps(backtest_summary_payload(result), indent=2), encoding="utf-8")

    _write_csv(trades_path, result.get("trade_log", []))

    config_path.write_text(render_run_config_toml(settings, result), encoding="utf-8")
    save_equity_curve_png(result["equity_curve"], plot_path)
    write_manifest(
        run_dir,
        [summary_path, trades_path, config_path, plot_path],
        latest_refreshed=None,
    )
    return {
        "summary_path": summary_path,
        "trades_path": trades_path,
        "config_path": config_path,
        "plot_path": plot_path,
        "manifest_path": run_dir / "manifest.json",
    }


def backtest_summary_payload(result: dict[str, Any]) -> dict[str, Any]:
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
        "max_drawdown_dollars": result.get("max_drawdown_dollars", result["max_drawdown"]),
        "avg_drawdown_pct": result.get("avg_drawdown_pct"),
        "avg_drawdown_dollars": result.get("avg_drawdown_dollars"),
        "max_drawdown_duration_days": result.get("max_drawdown_duration_days"),
        "avg_drawdown_duration_days": result.get("avg_drawdown_duration_days"),
        "max_recovery_duration_days": result.get("max_recovery_duration_days"),
        "avg_recovery_duration_days": result.get("avg_recovery_duration_days"),
        "total_drawdown_episodes": result.get("total_drawdown_episodes"),
        "pct_time_in_drawdown": result.get("pct_time_in_drawdown"),
        "total_trades": result["total_trades"],
        "parameters": result["parameters"],
        "strategy_parameters": result["parameters"],
        "segments": result["segments"],
    }


def render_run_config_toml(settings: Settings, result: dict[str, Any]) -> str:
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
        f'strategy = "{params.get("strategy", settings.backtest.strategy)}"',
        f'strategy_class = "{params.get("strategy_class") or ""}"',
        f'venue_name = "{settings.backtest.venue_name}"',
        f'oms_type = "{settings.backtest.oms_type}"',
        f'account_type = "{settings.backtest.account_type}"',
        f'base_currency = "{settings.backtest.base_currency}"',
        f'starting_balance = "{settings.backtest.starting_balance}"',
        f"default_leverage = {settings.backtest.default_leverage}",
        f"trade_size = \"{params.get('trade_size', settings.backtest.trade_size)}\"",
        f'results_subdir = "{settings.backtest.results_subdir}"',
        f'roll_preference = "{settings.backtest.roll_preference}"',
        f"calendar_roll_business_days = {settings.backtest.calendar_roll_business_days}",
        f"start_date = \"{params.get('start_date') or ''}\"",
        f"end_date = \"{params.get('end_date') or ''}\"",
        f"commission_per_side = {settings.backtest.commission_per_side}",
        f"slippage_ticks = {settings.backtest.slippage_ticks}",
        "",
        "[risk]",
        f'native_max_order_submit_rate = "{settings.risk.native_max_order_submit_rate}"',
        f'native_max_order_modify_rate = "{settings.risk.native_max_order_modify_rate}"',
        f"native_max_notional_per_order = {_render_notional_table(settings.risk.native_max_notional_per_order)}",
        f"max_loss_per_trade_dollars = {params.get('max_loss_per_trade_dollars', settings.risk.max_loss_per_trade_dollars)}",
        f"max_daily_trades = {params.get('max_daily_trades', settings.risk.max_daily_trades)}",
        f"max_daily_loss_dollars = {params.get('max_daily_loss_dollars', settings.risk.max_daily_loss_dollars)}",
        f"max_consecutive_losses = {params.get('max_consecutive_losses', settings.risk.max_consecutive_losses)}",
        f"max_drawdown_pct = {params.get('max_drawdown_pct', settings.risk.max_drawdown_pct)}",
        "",
        "[optimization]",
        f'study_name = "{settings.optimization.study_name}"',
        f'direction = "{settings.optimization.direction}"',
        f'results_subdir = "{settings.optimization.results_subdir}"',
        f'storage_filename = "{settings.optimization.storage_filename}"',
        f"seed = {settings.optimization.seed}",
        f"max_trials = {settings.optimization.max_trials}",
        f"max_runtime_seconds = {settings.optimization.max_runtime_seconds}",
        f"early_stop_window = {settings.optimization.early_stop_window}",
        f"early_stop_min_improvement = {settings.optimization.early_stop_min_improvement}",
        f'in_sample_start = "{settings.optimization.in_sample_start}"',
        f'in_sample_end = "{settings.optimization.in_sample_end}"',
        f'holdout_start = "{settings.optimization.holdout_start}"',
        f'holdout_end = "{settings.optimization.holdout_end}"',
        "",
        "[run]",
        f'mode = "{result["mode"]}"',
        f"instrument_id = \"{params.get('instrument_id') or ''}\"",
        f"roll_source = \"{params.get('roll_source', '')}\"",
    ]
    return "\n".join(lines) + "\n"


def _toml_bool(value: bool) -> str:
    return "true" if value else "false"


def _render_notional_table(values: dict[str, int]) -> str:
    if not values:
        return "{}"
    inner = ", ".join(f'"{key}" = {value}' for key, value in sorted(values.items()))
    return "{ " + inner + " }"


def create_unique_timestamped_dir(root: Path, timestamp: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    candidate = root / timestamp
    suffix = 1
    while candidate.exists():
        candidate = root / f"{timestamp}_{suffix:02d}"
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def refresh_latest_dir(run_dir: Path, *, refresh_latest: bool) -> Path | None:
    if not refresh_latest:
        return None

    latest_dir = run_dir.parent / "latest"
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    shutil.copytree(run_dir, latest_dir)
    return latest_dir


def write_manifest(
    run_dir: Path,
    files: Iterable[Path],
    *,
    latest_refreshed: bool | None,
) -> Path:
    manifest_path = run_dir / "manifest.json"
    payload: dict[str, Any] = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "files": sorted(str(path.relative_to(run_dir).as_posix()) for path in files),
    }
    if latest_refreshed is not None:
        payload["latest_refreshed"] = latest_refreshed
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not fieldnames:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
