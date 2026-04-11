from __future__ import annotations

from dataclasses import dataclass
import contextlib
import json
import multiprocessing
from pathlib import Path
from queue import Empty
import sys
from typing import Any

import optuna
import psutil

from mgc_bt.backtest.runner import run_backtest
from mgc_bt.config import Settings
from mgc_bt.config import load_settings
from mgc_bt.optimization.search_space import sample_trial_params

OBJECTIVE_PENALTY = -10.0
TRIAL_TIMEOUT_SECONDS = 600
_SCALAR_RESULT_KEYS = (
    "mode",
    "instrument_id",
    "segment_instruments",
    "segment_count",
    "start_date",
    "end_date",
    "total_pnl",
    "sharpe_ratio",
    "win_rate",
    "max_drawdown",
    "max_drawdown_pct",
    "total_trades",
)
_PAYLOAD_RESULT_KEYS = (
    "segments",
    "trade_log",
    "analytics_trade_log",
    "equity_curve",
)


def _run_backtest_worker(
    config_path: str,
    params: dict[str, Any],
    payload_path: str | None,
    queue: multiprocessing.queues.Queue,
) -> None:
    try:
        settings = load_settings(config_path)
        result = run_backtest(settings, params)
        payload = {key: result.get(key) for key in _PAYLOAD_RESULT_KEYS}
        scalar_result = {key: result.get(key) for key in _SCALAR_RESULT_KEYS}
        scalar_result["parameters"] = result.get("parameters", params)
        if payload_path is not None:
            payload_file = Path(payload_path)
            payload_file.parent.mkdir(parents=True, exist_ok=True)
            payload_file.write_text(json.dumps(payload), encoding="utf-8")
            scalar_result["payload_path"] = payload_file.as_posix()
        queue.put({"ok": True, "result": scalar_result})
    except Exception as exc:  # pragma: no cover - exercised from parent process
        queue.put({"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def run_backtest_trial_subprocess(
    settings: Settings,
    params: dict[str, Any],
    *,
    start_date: str,
    end_date: str,
    evaluation_window: str,
    payload_path: Path | None = None,
    timeout_seconds: int = TRIAL_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if payload_path is not None and payload_path.exists():
        payload_path.unlink()

    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    process = ctx.Process(
        target=_run_backtest_worker,
        args=(str(settings.config_path), params, payload_path.as_posix() if payload_path is not None else None, queue),
    )
    process.start()
    process.join(timeout_seconds)

    error: str | None = None
    try:
        if process.is_alive():
            cleanup_method = _cleanup_timed_out_process(process, timeout_seconds=timeout_seconds)
            error = (
                f"TimeoutError: evaluation exceeded {timeout_seconds} seconds "
                f"(cleanup={cleanup_method})"
            )
        else:
            try:
                message = queue.get(timeout=1)
            except Empty:
                message = None
            if message is None:
                error = f"RuntimeError: evaluation process exited with code {process.exitcode}"
            elif not message.get("ok", False):
                error = str(message.get("error", "RuntimeError: unknown subprocess error"))
            else:
                result = dict(message["result"])
                result["evaluation_window"] = evaluation_window
                return result
    finally:
        _close_queue_safely(queue)
        _close_process_safely(process)

    return {
        "mode": "evaluation_failed",
        "instrument_id": None,
        "segment_instruments": [],
        "segment_count": 0,
        "start_date": start_date,
        "end_date": end_date,
        "total_pnl": 0.0,
        "sharpe_ratio": OBJECTIVE_PENALTY,
        "win_rate": 0.0,
        "max_drawdown": 0.0,
        "max_drawdown_pct": 100.0,
        "total_trades": 0,
        "parameters": dict(params),
        "evaluation_window": evaluation_window,
        "error": error,
        "payload_path": payload_path.as_posix() if payload_path is not None else None,
    }


def _cleanup_timed_out_process(
    process: multiprocessing.Process,
    *,
    timeout_seconds: int,
    terminate_wait_seconds: int = 5,
    kill_wait_seconds: int = 5,
) -> str:
    pid = process.pid
    _log_timeout_event(
        f"Trial subprocess timed out after {timeout_seconds}s (pid={pid}); attempting terminate().",
    )
    process.terminate()
    process.join(terminate_wait_seconds)
    if not process.is_alive():
        _log_timeout_event(f"Trial subprocess pid={pid} exited after terminate().")
        return "terminate"

    _log_timeout_event(
        f"Trial subprocess pid={pid} did not exit after terminate(); killing process tree via psutil.",
    )
    try:
        parent = psutil.Process(pid)
        descendants = parent.children(recursive=True)
        for child in descendants:
            with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                child.kill()
        with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            parent.kill()
        psutil.wait_procs([*descendants, parent], timeout=kill_wait_seconds)
    except (psutil.Error, ProcessLookupError) as exc:
        _log_timeout_event(
            f"psutil cleanup fallback for pid={pid} hit {type(exc).__name__}: {exc}; attempting kill().",
        )
    with contextlib.suppress(Exception):
        if process.is_alive():
            process.kill()
            process.join(kill_wait_seconds)
    if process.is_alive():
        _log_timeout_event(f"Trial subprocess pid={pid} remained alive after kill attempts.")
        return "cleanup_failed"
    _log_timeout_event(f"Trial subprocess pid={pid} killed via psutil process-tree cleanup.")
    return "psutil_kill"


def _log_timeout_event(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _close_queue_safely(queue: multiprocessing.queues.Queue) -> None:
    with contextlib.suppress(Exception):
        queue.cancel_join_thread()
    with contextlib.suppress(Exception):
        queue.close()


def _close_process_safely(process: multiprocessing.Process) -> None:
    with contextlib.suppress(Exception):
        process.close()


def evaluate_params(
    settings: Settings,
    params: dict[str, Any],
    *,
    start_date: str,
    end_date: str,
    evaluation_window: str,
    payload_path: Path | None = None,
) -> dict[str, Any]:
    run_params = dict(params)
    run_params.update(
        {
            "instrument_id": None,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
    result = run_backtest_trial_subprocess(
        settings,
        run_params,
        start_date=start_date,
        end_date=end_date,
        evaluation_window=evaluation_window,
        payload_path=payload_path,
    )
    result.setdefault("parameters", run_params)
    result["evaluation_window"] = evaluation_window
    return result


def apply_result_user_attrs(
    trial: optuna.trial.Trial | optuna.trial.FrozenTrial,
    result: dict[str, Any],
    *,
    objective_score: float,
    evaluation_window: str,
) -> None:
    trial.set_user_attr("mode", result.get("mode", "auto_roll"))
    trial.set_user_attr("evaluation_window", evaluation_window)
    trial.set_user_attr("objective_score", objective_score)
    trial.set_user_attr("sharpe_ratio", result.get("sharpe_ratio"))
    trial.set_user_attr("total_pnl", float(result.get("total_pnl", 0.0)))
    trial.set_user_attr("win_rate", float(result.get("win_rate", 0.0)))
    trial.set_user_attr("max_drawdown_pct", float(result.get("max_drawdown_pct") or 0.0))
    trial.set_user_attr("max_drawdown", float(result.get("max_drawdown") or 0.0))
    trial.set_user_attr("total_trades", int(result.get("total_trades", 0)))
    trial.set_user_attr("start_date", result.get("start_date"))
    trial.set_user_attr("end_date", result.get("end_date"))
    trial.set_user_attr("instrument_id", result.get("instrument_id"))


def compute_objective_score(result: dict[str, Any]) -> float:
    total_trades = int(result.get("total_trades", 0))
    max_drawdown_pct = float(result.get("max_drawdown_pct") or 0.0)
    if total_trades < 30:
        return OBJECTIVE_PENALTY
    if max_drawdown_pct > 25.0:
        return OBJECTIVE_PENALTY
    sharpe_ratio = result.get("sharpe_ratio")
    if sharpe_ratio is None:
        return 0.0
    return float(sharpe_ratio)


@dataclass
class TrialEvaluator:
    settings: Settings
    start_date: str | None = None
    end_date: str | None = None
    evaluation_window: str = "in_sample"

    def __call__(self, trial: optuna.trial.Trial) -> float:
        sampled_params = sample_trial_params(trial)
        result = evaluate_params(
            self.settings,
            sampled_params,
            start_date=self.start_date or self.settings.optimization.in_sample_start,
            end_date=self.end_date or self.settings.optimization.in_sample_end,
            evaluation_window=self.evaluation_window,
        )
        if result.get("error"):
            trial.set_user_attr("error", result["error"])

        objective_score = compute_objective_score(result)
        apply_result_user_attrs(
            trial,
            result,
            objective_score=objective_score,
            evaluation_window=self.evaluation_window,
        )
        return objective_score
