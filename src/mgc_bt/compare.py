from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import csv
import json
from typing import Any

from mgc_bt.backtest.artifacts import create_unique_timestamped_dir
from mgc_bt.backtest.artifacts import write_backtest_artifacts
from mgc_bt.backtest.runner import run_backtest
from mgc_bt.config import Settings
from mgc_bt.reporting.comparison import write_comparison_tearsheet


@dataclass(frozen=True)
class StrategySelector:
    label: str
    strategy: str
    strategy_class: str | None = None


def run_comparison(
    settings: Settings,
    *,
    strategy_a: str,
    strategy_b: str,
    strategy_class_a: str | None = None,
    strategy_class_b: str | None = None,
    instrument_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d_%H%M%S")
    comparisons_root = settings.paths.results_root / "comparisons"
    comparison_dir = create_unique_timestamped_dir(comparisons_root, timestamp)

    selector_a = StrategySelector(label="strategy_a", strategy=strategy_a, strategy_class=_optional_text(strategy_class_a))
    selector_b = StrategySelector(label="strategy_b", strategy=strategy_b, strategy_class=_optional_text(strategy_class_b))

    result_a, artifacts_a = _run_strategy_side(
        settings,
        selector=selector_a,
        timestamp=timestamp,
        instrument_id=instrument_id,
        start_date=start_date,
        end_date=end_date,
    )
    result_b, artifacts_b = _run_strategy_side(
        settings,
        selector=selector_b,
        timestamp=timestamp,
        instrument_id=instrument_id,
        start_date=start_date,
        end_date=end_date,
    )

    summary = {
        "schema_version": 1,
        "comparison_timestamp": timestamp,
        "strategy_a": {
            "strategy": selector_a.strategy,
            "strategy_class": selector_a.strategy_class,
            "run_dir": artifacts_a["run_dir"].as_posix(),
            "summary": _metrics_snapshot(result_a),
        },
        "strategy_b": {
            "strategy": selector_b.strategy,
            "strategy_class": selector_b.strategy_class,
            "run_dir": artifacts_b["run_dir"].as_posix(),
            "summary": _metrics_snapshot(result_b),
        },
    }
    summary_path = comparison_dir / "comparison_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    metrics_delta_path = comparison_dir / "metrics_delta.csv"
    _write_metrics_delta_csv(metrics_delta_path, result_a, result_b)

    tearsheet_path = write_comparison_tearsheet(
        comparison_dir=comparison_dir,
        strategy_a_run_dir=artifacts_a["run_dir"],
        strategy_b_run_dir=artifacts_b["run_dir"],
        strategy_a_label=_selector_label(selector_a),
        strategy_b_label=_selector_label(selector_b),
    )

    return {
        "comparison_dir": comparison_dir,
        "comparison_summary_path": summary_path,
        "metrics_delta_path": metrics_delta_path,
        "comparison_tearsheet_path": tearsheet_path,
        "strategy_a_run_dir": artifacts_a["run_dir"],
        "strategy_b_run_dir": artifacts_b["run_dir"],
    }


def _run_strategy_side(
    settings: Settings,
    *,
    selector: StrategySelector,
    timestamp: str,
    instrument_id: str | None,
    start_date: str | None,
    end_date: str | None,
) -> tuple[dict[str, Any], dict[str, Path | None]]:
    backtests_root = settings.paths.results_root / settings.backtest.results_subdir
    run_dir = create_unique_timestamped_dir(backtests_root, f"{timestamp}_{selector.label}")
    params = {
        "strategy": selector.strategy,
        "strategy_class": selector.strategy_class,
        "instrument_id": instrument_id,
        "start_date": start_date,
        "end_date": end_date,
        "_run_dir": run_dir.as_posix(),
    }
    result = run_backtest(settings, params)
    result.setdefault("parameters", {})
    result["parameters"]["strategy"] = selector.strategy
    result["parameters"]["strategy_class"] = selector.strategy_class
    result["strategy_name"] = _selector_label(selector)
    artifacts = write_backtest_artifacts(settings, result, refresh_latest=False, run_dir=run_dir)
    return result, artifacts


def _write_metrics_delta_csv(path: Path, result_a: dict[str, Any], result_b: dict[str, Any]) -> None:
    metrics = ["total_pnl", "sharpe_ratio", "win_rate", "max_drawdown", "total_trades"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "strategy_a", "strategy_b", "delta_b_minus_a"])
        writer.writeheader()
        for metric in metrics:
            value_a = _to_float(result_a.get(metric))
            value_b = _to_float(result_b.get(metric))
            writer.writerow(
                {
                    "metric": metric,
                    "strategy_a": value_a,
                    "strategy_b": value_b,
                    "delta_b_minus_a": value_b - value_a,
                },
            )


def _metrics_snapshot(result: dict[str, Any]) -> dict[str, float]:
    return {
        "total_pnl": _to_float(result.get("total_pnl")),
        "sharpe_ratio": _to_float(result.get("sharpe_ratio")),
        "win_rate": _to_float(result.get("win_rate")),
        "max_drawdown": _to_float(result.get("max_drawdown")),
        "total_trades": _to_float(result.get("total_trades")),
    }


def _selector_label(selector: StrategySelector) -> str:
    return selector.strategy_class or selector.strategy


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)
