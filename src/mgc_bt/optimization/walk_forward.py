from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
import gc
import json
import os
from pathlib import Path
from typing import Any, TextIO

import optuna
from pandas import DateOffset
from pandas import Timestamp
import pyarrow.parquet as pq
from nautilus_trader.model.data import Bar
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from mgc_bt.backtest.contracts import resolve_contract_selection
from mgc_bt.config import Settings
from mgc_bt.optimization.objective import TrialEvaluator
from mgc_bt.optimization.objective import evaluate_params


@dataclass(frozen=True)
class WalkForwardWindow:
    index: int
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str


@dataclass(frozen=True)
class WalkForwardWindowResult:
    window_index: int
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    status: str
    skipped_reason: str | None
    inconclusive: bool
    training_bar_count: int
    training_completed_trials: int
    training_sharpe: float | None
    validation_sharpe: float | None
    validation_max_drawdown_pct: float | None
    validation_total_pnl: float | None
    test_sharpe: float | None
    test_total_pnl: float | None
    test_total_trades: int
    test_bar_count: int
    selected_params: dict[str, Any]


@dataclass(frozen=True)
class WalkForwardAggregateSummary:
    completed_window_count: int
    skipped_window_count: int
    inconclusive_window_count: int
    aggregated_oos_sharpe: float | None
    aggregated_oos_total_pnl: float
    aggregated_equity_curve: list[dict[str, Any]]
    selected_params: list[dict[str, Any]]
    status: str
    aggregated_trade_log: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _AggregateBuffers:
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
    trade_log: list[dict[str, Any]] = field(default_factory=list)
    best_run_result: dict[str, Any] | None = None


def build_walk_forward_windows(settings: Settings) -> list[WalkForwardWindow]:
    train_start = Timestamp(settings.optimization.in_sample_start, tz="UTC")
    available_end = Timestamp(settings.optimization.holdout_end, tz="UTC") - DateOffset(
        months=settings.walk_forward.final_test_months,
    )
    windows: list[WalkForwardWindow] = []
    index = 1
    while True:
        train_end = train_start + DateOffset(months=settings.walk_forward.train_months)
        validation_end = train_end + DateOffset(months=settings.walk_forward.validation_months)
        test_end = validation_end + DateOffset(months=settings.walk_forward.test_months)
        if test_end > available_end:
            break
        windows.append(
            WalkForwardWindow(
                index=index,
                train_start=train_start.isoformat(),
                train_end=train_end.isoformat(),
                validation_start=train_end.isoformat(),
                validation_end=validation_end.isoformat(),
                test_start=validation_end.isoformat(),
                test_end=test_end.isoformat(),
            ),
        )
        train_start = train_start + DateOffset(months=settings.walk_forward.step_months)
        index += 1
    return windows


def run_walk_forward_optimization(
    settings: Settings,
    *,
    study_name: str,
    max_trials: int,
    output: TextIO,
    final_test: bool,
    temp_root: Path,
) -> dict[str, Any]:
    catalog = ParquetDataCatalog(str(settings.paths.catalog_root))
    temp_root.mkdir(parents=True, exist_ok=True)
    windows = build_walk_forward_windows(settings)
    runtime_warning = _RuntimeWarningState()
    window_results: list[WalkForwardWindowResult] = []
    failed_trials: list[dict[str, Any]] = []
    training_trials: list[optuna.trial.FrozenTrial] = []
    aggregate_buffers = _AggregateBuffers()
    temp_result_paths: dict[int, Path] = {}
    cumulative_oos_pnl = 0.0

    for window in windows:
        training_bar_count = _count_window_bars(catalog, settings, window.train_start, window.train_end)
        if training_bar_count < settings.walk_forward.min_training_bars:
            skipped = WalkForwardWindowResult(
                window_index=window.index,
                train_start=window.train_start,
                train_end=window.train_end,
                validation_start=window.validation_start,
                validation_end=window.validation_end,
                test_start=window.test_start,
                test_end=window.test_end,
                status="skipped",
                skipped_reason="insufficient_training_bars",
                inconclusive=False,
                training_bar_count=training_bar_count,
                training_completed_trials=0,
                training_sharpe=None,
                validation_sharpe=None,
                validation_max_drawdown_pct=None,
                validation_total_pnl=None,
                test_sharpe=None,
                test_total_pnl=None,
                test_total_trades=0,
                test_bar_count=0,
                selected_params={},
            )
            window_results.append(skipped)
            _write_window_progress(output, skipped, cumulative_oos_pnl)
            continue

        study = optuna.create_study(
            direction=settings.optimization.direction,
            sampler=optuna.samplers.TPESampler(seed=settings.optimization.seed + window.index),
        )
        evaluator = TrialEvaluator(
            settings,
            start_date=window.train_start,
            end_date=window.train_end,
            evaluation_window="training",
        )
        callbacks = [
            _walk_forward_runtime_callback(
                output=output,
                runtime_state=runtime_warning,
                settings=settings,
                total_windows=len(windows),
                current_window_index=window.index,
                max_trials=max_trials,
            ),
            _window_early_stop_callback(
                window=settings.optimization.early_stop_window,
                min_improvement=settings.optimization.early_stop_min_improvement,
                output=output,
            ),
        ]
        study.optimize(
            evaluator,
            n_trials=max_trials,
            timeout=settings.optimization.max_runtime_seconds,
            callbacks=callbacks,
            catch=(Exception,),
        )
        failed_trials.extend(_failed_trial_rows(window.index, study))
        completed_trials = [trial for trial in study.trials if trial.state == optuna.trial.TrialState.COMPLETE]
        training_trials.extend(completed_trials)
        if not completed_trials:
            skipped = WalkForwardWindowResult(
                window_index=window.index,
                train_start=window.train_start,
                train_end=window.train_end,
                validation_start=window.validation_start,
                validation_end=window.validation_end,
                test_start=window.test_start,
                test_end=window.test_end,
                status="skipped",
                skipped_reason="no_completed_training_trials",
                inconclusive=False,
                training_bar_count=training_bar_count,
                training_completed_trials=0,
                training_sharpe=None,
                validation_sharpe=None,
                validation_max_drawdown_pct=None,
                validation_total_pnl=None,
                test_sharpe=None,
                test_total_pnl=None,
                test_total_trades=0,
                test_bar_count=0,
                selected_params={},
            )
            window_results.append(skipped)
            _write_window_progress(output, skipped, cumulative_oos_pnl)
            continue

        best_training_trial = max(
            completed_trials,
            key=lambda trial: float(trial.value) if trial.value is not None else float("-inf"),
        )
        selected = _select_validation_candidate(
            settings,
            completed_trials,
            window=window,
        )
        test_result = evaluate_params(
            settings,
            selected["params"],
            start_date=window.test_start,
            end_date=window.test_end,
            evaluation_window="test",
        )
        test_bar_count = _count_window_bars(catalog, settings, window.test_start, window.test_end)
        inconclusive = int(test_result.get("total_trades", 0)) < settings.walk_forward.min_test_trades
        status = "inconclusive" if inconclusive else "completed"
        temp_result_paths[window.index] = _write_window_temp_result(temp_root, window.index, test_result)
        if not inconclusive:
            cumulative_oos_pnl += float(test_result.get("total_pnl", 0.0))
            if aggregate_buffers.best_run_result is None:
                aggregate_buffers.best_run_result = _read_window_temp_result(temp_result_paths[window.index])
        result = WalkForwardWindowResult(
            window_index=window.index,
            train_start=window.train_start,
            train_end=window.train_end,
            validation_start=window.validation_start,
            validation_end=window.validation_end,
            test_start=window.test_start,
            test_end=window.test_end,
            status=status,
            skipped_reason=None,
            inconclusive=inconclusive,
            training_bar_count=training_bar_count,
            training_completed_trials=len(completed_trials),
            training_sharpe=_float_or_none(best_training_trial.user_attrs.get("sharpe_ratio")),
            validation_sharpe=_float_or_none(selected["validation_result"].get("sharpe_ratio")),
            validation_max_drawdown_pct=_float_or_none(selected["validation_result"].get("max_drawdown_pct")),
            validation_total_pnl=_float_or_none(selected["validation_result"].get("total_pnl")),
            test_sharpe=_float_or_none(test_result.get("sharpe_ratio")),
            test_total_pnl=_float_or_none(test_result.get("total_pnl")),
            test_total_trades=int(test_result.get("total_trades", 0)),
            test_bar_count=test_bar_count,
            selected_params=selected["params"],
        )
        window_results.append(result)
        _write_window_progress(output, result, cumulative_oos_pnl)
        del test_result
        del study
        del completed_trials
        gc.collect()

    del catalog
    gc.collect()

    aggregate = _aggregate_walk_forward(window_results, aggregate_buffers, temp_result_paths)
    final_test_result = None
    if final_test:
        final_test_result = _run_final_test(settings, window_results)

    return {
        "windows": windows,
        "window_results": window_results,
        "aggregate": aggregate,
        "failed_trials": failed_trials,
        "final_test_result": final_test_result,
        "training_trials": training_trials,
        "best_run_result": aggregate_buffers.best_run_result,
        "temp_root": temp_root,
        "temp_result_paths": temp_result_paths,
    }


@dataclass
class _RuntimeWarningState:
    warned: bool = False
    checked: bool = False


def _select_validation_candidate(
    settings: Settings,
    completed_trials: list[optuna.trial.FrozenTrial],
    *,
    window: WalkForwardWindow,
) -> dict[str, Any]:
    top_trials = sorted(
        completed_trials,
        key=lambda trial: (
            -(float(trial.value) if trial.value is not None else float("-inf")),
            -(_float_or_none(trial.user_attrs.get("sharpe_ratio")) or float("-inf")),
            _float_or_none(trial.user_attrs.get("max_drawdown_pct")) or float("inf"),
        ),
    )[: settings.walk_forward.validation_top_n]
    candidates: list[dict[str, Any]] = []
    for trial in top_trials:
        validation_result = evaluate_params(
            settings,
            dict(trial.params),
            start_date=window.validation_start,
            end_date=window.validation_end,
            evaluation_window="validation",
        )
        candidates.append(
            {
                "params": dict(trial.params),
                "validation_result": validation_result,
                "validation_sharpe": _float_or_none(validation_result.get("sharpe_ratio")) or float("-inf"),
                "validation_max_drawdown_pct": _float_or_none(validation_result.get("max_drawdown_pct")) or float("inf"),
                "validation_total_pnl": _float_or_none(validation_result.get("total_pnl")) or float("-inf"),
            },
        )
    candidates.sort(
        key=lambda item: (
            -item["validation_sharpe"],
            item["validation_max_drawdown_pct"],
            -item["validation_total_pnl"],
        ),
    )
    return candidates[0]


def _aggregate_walk_forward(
    window_results: list[WalkForwardWindowResult],
    buffers: _AggregateBuffers,
    temp_result_paths: dict[int, Path],
) -> WalkForwardAggregateSummary:
    conclusive = [result for result in window_results if result.status == "completed"]
    weighted_total = sum(
        (result.test_sharpe or 0.0) * max(result.test_bar_count, 0)
        for result in conclusive
        if result.test_sharpe is not None
    )
    weight_sum = sum(result.test_bar_count for result in conclusive if result.test_sharpe is not None)
    aggregated_sharpe = round(weighted_total / weight_sum, 6) if weight_sum > 0 else None
    aggregated_total_pnl = round(sum(result.test_total_pnl or 0.0 for result in conclusive), 4)
    selected_params = [
        {
            "window_index": result.window_index,
            **result.selected_params,
        }
        for result in window_results
        if result.selected_params
    ]
    completed_count = len(conclusive)
    skipped_count = sum(1 for result in window_results if result.status == "skipped")
    inconclusive_count = sum(1 for result in window_results if result.status == "inconclusive")
    status = "completed" if completed_count > 0 else "no_conclusive_windows"
    for result in conclusive:
        temp_path = temp_result_paths.get(result.window_index)
        if temp_path is None:
            continue
        temp_result = _read_window_temp_result(temp_path)
        _extend_aggregated_equity_curve(buffers.equity_curve, temp_result.get("equity_curve", []))
        buffers.trade_log.extend(temp_result.get("trade_log", []))

    return WalkForwardAggregateSummary(
        completed_window_count=completed_count,
        skipped_window_count=skipped_count,
        inconclusive_window_count=inconclusive_count,
        aggregated_oos_sharpe=aggregated_sharpe,
        aggregated_oos_total_pnl=aggregated_total_pnl,
        aggregated_equity_curve=buffers.equity_curve or _empty_equity_curve(),
        selected_params=selected_params,
        status=status,
        aggregated_trade_log=buffers.trade_log,
    )


def _run_final_test(settings: Settings, window_results: list[WalkForwardWindowResult]) -> dict[str, Any] | None:
    selected_results = [result for result in window_results if result.selected_params]
    if not selected_results:
        return None
    latest = selected_results[-1]
    final_end = Timestamp(settings.optimization.holdout_end, tz="UTC")
    final_start = final_end - DateOffset(months=settings.walk_forward.final_test_months)
    return evaluate_params(
        settings,
        latest.selected_params,
        start_date=final_start.isoformat(),
        end_date=final_end.isoformat(),
        evaluation_window="final_test",
    )


def _count_window_bars(
    catalog: ParquetDataCatalog,
    settings: Settings,
    start_date: str,
    end_date: str,
) -> int:
    selection = resolve_contract_selection(
        catalog=catalog,
        symbol_root=settings.ingestion.symbol,
        default_mode=settings.backtest.default_mode,
        requested_instrument_id=None,
        start=start_date,
        end=end_date,
        roll_preference=settings.backtest.roll_preference,
        calendar_roll_business_days=settings.backtest.calendar_roll_business_days,
    )
    total = 0
    for segment in selection.windows:
        total += _count_bar_rows_from_metadata(catalog, segment.bar_type, segment.start, segment.end)
    return total


def _count_bar_rows_from_metadata(
    catalog: ParquetDataCatalog,
    bar_type: str,
    start: datetime,
    end: datetime,
) -> int:
    directory = catalog._make_path(Bar, identifier=bar_type)
    total_rows = 0
    requested_start_ns = int(start.timestamp() * 1_000_000_000)
    requested_end_ns = int(end.timestamp() * 1_000_000_000)
    for path in catalog.fs.glob(os.path.join(directory, "*.parquet")):
        interval = _file_interval_ns(path)
        if interval is None:
            continue
        file_start_ns, file_end_ns = interval
        if file_end_ns < requested_start_ns or file_start_ns > requested_end_ns:
            continue
        total_rows += pq.ParquetFile(path, filesystem=catalog.fs).metadata.num_rows
    return total_rows


def _file_interval_ns(path: str) -> tuple[int, int] | None:
    name = os.path.basename(path)
    stem, suffix = os.path.splitext(name)
    if suffix != ".parquet":
        return None
    try:
        start_ns, end_ns = stem.split("-", maxsplit=1)
    except ValueError:
        return None
    return int(start_ns), int(end_ns)


def _extend_aggregated_equity_curve(
    destination: list[dict[str, Any]],
    points: list[dict[str, Any]],
) -> None:
    seen = {(str(item["timestamp"]), float(item["equity"])) for item in destination}
    for point in points:
        key = (str(point["timestamp"]), float(point["equity"]))
        if key in seen:
            continue
        seen.add(key)
        destination.append({"timestamp": key[0], "equity": round(key[1], 4)})
    destination.sort(key=lambda item: item["timestamp"])


def _empty_equity_curve() -> list[dict[str, Any]]:
    return [
        {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "equity": 0.0,
        },
    ]


def _write_window_temp_result(temp_root: Path, window_index: int, result: dict[str, Any]) -> Path:
    payload = {
        "mode": result.get("mode"),
        "instrument_id": result.get("instrument_id"),
        "segment_instruments": result.get("segment_instruments", []),
        "segment_count": result.get("segment_count"),
        "start_date": result.get("start_date"),
        "end_date": result.get("end_date"),
        "total_pnl": result.get("total_pnl"),
        "sharpe_ratio": result.get("sharpe_ratio"),
        "win_rate": result.get("win_rate"),
        "max_drawdown": result.get("max_drawdown"),
        "max_drawdown_pct": result.get("max_drawdown_pct"),
        "total_trades": result.get("total_trades"),
        "parameters": result.get("parameters", {}),
        "segments": result.get("segments", []),
        "trade_log": result.get("trade_log", []),
        "analytics_trade_log": result.get("analytics_trade_log", []),
        "equity_curve": result.get("equity_curve", []),
    }
    path = temp_root / f"window_{window_index:02d}_result.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _read_window_temp_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_window_progress(output: TextIO, result: WalkForwardWindowResult, cumulative_oos_pnl: float) -> None:
    output.write(
        "Window "
        f"{result.window_index} | "
        f"train={result.train_start}->{result.train_end} | "
        f"validation={result.validation_start}->{result.validation_end} | "
        f"test={result.test_start}->{result.test_end} | "
        f"training_sharpe={_format_metric(result.training_sharpe)} | "
        f"validation_sharpe={_format_metric(result.validation_sharpe)} | "
        f"test_sharpe={_format_metric(result.test_sharpe)} | "
        f"cumulative_oos_pnl={cumulative_oos_pnl:.4f}\n",
    )
    output.flush()


def _format_metric(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.4f}"


def _failed_trial_rows(window_index: int, study: optuna.study.Study) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trial in study.trials:
        if trial.state != optuna.trial.TrialState.FAIL:
            continue
        rows.append(
            {
                "window_index": window_index,
                "trial_number": trial.number,
                "params": dict(trial.params),
                "error": trial.user_attrs.get("error", "Unknown error"),
            },
        )
    return rows


def _walk_forward_runtime_callback(
    *,
    output: TextIO,
    runtime_state: _RuntimeWarningState,
    settings: Settings,
    total_windows: int,
    current_window_index: int,
    max_trials: int,
):
    def callback(study: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:
        if runtime_state.checked or current_window_index != 1:
            return
        completed = [item for item in study.trials if item.state == optuna.trial.TrialState.COMPLETE and item.duration is not None]
        if len(completed) < 3:
            return
        mean_seconds = sum(item.duration.total_seconds() for item in completed[:3]) / 3.0
        remaining_windows = max(total_windows - current_window_index, 0)
        remaining_trials = max(max_trials - len(completed), 0) + (remaining_windows * max_trials)
        estimate_seconds = mean_seconds * remaining_trials
        runtime_state.checked = True
        warning_seconds = settings.walk_forward.runtime_warning_minutes * 60
        if estimate_seconds > warning_seconds:
            completion = datetime.now(tz=UTC).timestamp() + estimate_seconds
            completion_text = datetime.fromtimestamp(completion, tz=UTC).isoformat()
            output.write(
                "Warning: estimated walk-forward runtime "
                f"{_format_duration(estimate_seconds)} exceeds 00:30:00; estimated completion {completion_text}.\n",
            )
            output.flush()
            runtime_state.warned = True

    return callback


def _window_early_stop_callback(window: int, min_improvement: float, output: TextIO):
    def callback(study: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:
        completed = sorted(
            [item for item in study.trials if item.state == optuna.trial.TrialState.COMPLETE],
            key=lambda item: item.number,
        )
        if len(completed) < window:
            return
        best_history: list[float] = []
        running_best = float("-inf")
        for item in completed:
            running_best = max(running_best, float(item.value))
            best_history.append(running_best)
        improvement = best_history[-1] - best_history[-window]
        if improvement <= min_improvement:
            output.write(
                "Early stopping triggered: best objective improved by "
                f"{improvement:.4f} over the last {window} completed trials.\n",
            )
            output.flush()
            study.stop()

    return callback


def _format_duration(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
