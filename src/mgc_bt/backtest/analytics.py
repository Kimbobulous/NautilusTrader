from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from csv import DictWriter
from csv import writer as csv_writer
from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
import csv
import json
import math
import statistics
from typing import Any

import pandas as pd

from mgc_bt.backtest.state import ArmedAuditSnapshot

AUDIT_HEADERS = [
    "record_type",
    "timestamp",
    "instrument_id",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "supertrend_direction",
    "supertrend_value",
    "volatility_cluster",
    "vwap_value",
    "price_vs_vwap",
    "wavetrend_zscore",
    "wavetrend_divergence_detected",
    "delta_value",
    "delta_threshold",
    "delta_pass",
    "volume_avg",
    "volume_pass",
    "absorption_detected",
    "candle_formation",
    "optional_confirmation_count",
    "entry_fired",
    "entry_rejected_reason",
    "entry_timestamp",
    "exit_timestamp",
    "entry_price",
    "exit_price",
    "direction",
    "pnl",
    "pnl_dollars",
    "exit_reason",
    "max_favorable_excursion",
    "max_adverse_excursion",
    "bars_held",
    "volatility_cluster_at_entry",
    "session_at_entry",
]

BREAKDOWN_FILENAMES = {
    "session": "by_session.csv",
    "volatility_regime": "by_volatility_regime.csv",
    "month": "by_month.csv",
    "year": "by_year.csv",
    "day_of_week": "by_day_of_week.csv",
    "hour": "by_hour.csv",
}


class AuditLogWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle = None
        self._writer = None

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        should_write_header = not self.path.exists() or self.path.stat().st_size == 0
        self._handle = self.path.open("a", encoding="utf-8", newline="")
        self._writer = csv_writer(self._handle)
        if should_write_header:
            self._writer.writerow(AUDIT_HEADERS)
            self._handle.flush()

    def write_armed_bar(self, snapshot: ArmedAuditSnapshot) -> None:
        self.write_row({"record_type": "armed_bar", **asdict(snapshot)})

    def write_trade(self, row: dict[str, Any]) -> None:
        self.write_row({"record_type": "executed_trade", **row})

    def write_row(self, row: dict[str, Any]) -> None:
        if self._writer is None or self._handle is None:
            raise RuntimeError("AuditLogWriter must be opened before writing.")
        normalized = [row.get(field) for field in AUDIT_HEADERS]
        self._writer.writerow(normalized)
        self._handle.flush()

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
        self._handle = None
        self._writer = None


@dataclass(frozen=True)
class BacktestAnalyticsBundle:
    files: list[Path]
    summary_updates: dict[str, Any]


def ensure_audit_log_file(path: Path) -> Path:
    writer = AuditLogWriter(path)
    writer.open()
    writer.close()
    return path


def read_trade_metadata(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            rows.append(json.loads(text))
    return rows


def append_trade_metadata(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(row) + "\n")


def write_backtest_analytics(result: dict[str, Any], run_dir: Path) -> BacktestAnalyticsBundle:
    analytics_dir = run_dir / "analytics"
    breakdowns_dir = analytics_dir / "breakdowns"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    breakdowns_dir.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []

    audit_path = analytics_dir / "audit_log.csv"
    if not audit_path.exists():
        ensure_audit_log_file(audit_path)
    files.append(audit_path)

    trades = list(result.get("analytics_trade_log") or result.get("trade_log") or [])
    breakdown_files = write_trade_breakdowns(trades, breakdowns_dir)
    files.extend(breakdown_files)

    drawdown = compute_drawdown_analysis(result.get("equity_curve", []))
    underwater_path = analytics_dir / "underwater_curve.csv"
    with underwater_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["timestamp", "equity", "running_peak", "underwater_dollars", "underwater_pct"]
        writer = DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in drawdown["underwater_curve"]:
            writer.writerow(row)
    files.append(underwater_path)

    episodes_path = analytics_dir / "drawdown_episodes.csv"
    with episodes_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "episode_start",
            "episode_end",
            "episode_duration_bars",
            "episode_duration_days",
            "drawdown_pct",
            "drawdown_dollars",
            "recovery_start",
            "recovery_end",
            "recovery_duration_bars",
            "recovery_duration_days",
            "recovered",
        ]
        writer = DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in drawdown["episodes"]:
            writer.writerow(row)
    files.append(episodes_path)

    return BacktestAnalyticsBundle(files=files, summary_updates=drawdown["summary"])


def write_trade_breakdowns(trades: list[dict[str, Any]], breakdowns_dir: Path) -> list[Path]:
    rows = normalize_trade_analytics_rows(trades)
    outputs: list[Path] = []
    breakdown_specs = {
        "session": lambda row: row["session_at_entry"],
        "volatility_regime": lambda row: row["volatility_regime_label"],
        "month": lambda row: row["entry_month"],
        "year": lambda row: row["entry_year"],
        "day_of_week": lambda row: row["entry_day_of_week"],
        "hour": lambda row: row["entry_hour"],
    }
    for key, grouper in breakdown_specs.items():
        output_path = breakdowns_dir / BREAKDOWN_FILENAMES[key]
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            fieldnames = [
                "bucket",
                "trade_count",
                "win_rate",
                "total_pnl",
                "average_pnl_per_trade",
                "sharpe_ratio",
                "max_drawdown",
            ]
            writer = DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in build_breakdown_rows(rows, grouper):
                writer.writerow(row)
        outputs.append(output_path)
    return outputs


def normalize_trade_analytics_rows(trades: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for trade in trades:
        opened_at = trade.get("opened_at") or trade.get("entry_timestamp")
        if not opened_at:
            continue
        ts = pd.Timestamp(opened_at, tz="UTC")
        session = trade.get("session_at_entry") or classify_session(ts)
        regime = trade.get("volatility_cluster_at_entry")
        normalized.append(
            {
                **trade,
                "opened_at": opened_at,
                "realized_pnl": float(trade.get("realized_pnl", trade.get("pnl_dollars", trade.get("pnl", 0.0)))),
                "session_at_entry": session,
                "volatility_cluster_at_entry": regime,
                "volatility_regime_label": str(regime) if regime is not None else "unknown",
                "entry_month": ts.strftime("%b"),
                "entry_year": int(ts.year),
                "entry_day_of_week": ts.strftime("%a"),
                "entry_hour": int(ts.hour),
            },
        )
    return normalized


def build_breakdown_rows(
    rows: list[dict[str, Any]],
    bucket_getter,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(bucket_getter(row))].append(row)
    return [
        {
            "bucket": bucket,
            **compute_trade_metrics(items),
        }
        for bucket, items in sorted(grouped.items(), key=lambda item: item[0])
    ]


def compute_trade_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [float(item.get("realized_pnl", 0.0)) for item in trades]
    wins = [value for value in pnls if value > 0]
    equity = []
    running = 0.0
    for pnl in pnls:
        running += pnl
        equity.append(running)
    return {
        "trade_count": len(trades),
        "win_rate": round((len(wins) / len(trades)) * 100.0, 4) if trades else 0.0,
        "total_pnl": round(sum(pnls), 4),
        "average_pnl_per_trade": round(sum(pnls) / len(pnls), 4) if pnls else 0.0,
        "sharpe_ratio": round(_trade_pnl_sharpe(pnls), 6) if len(pnls) > 1 else 0.0,
        "max_drawdown": round(_trade_pnl_max_drawdown(equity), 4),
    }


def compute_drawdown_analysis(equity_curve: list[dict[str, Any]]) -> dict[str, Any]:
    if not equity_curve:
        empty_summary = {
            "max_drawdown_pct": 0.0,
            "max_drawdown_dollars": 0.0,
            "avg_drawdown_pct": 0.0,
            "avg_drawdown_dollars": 0.0,
            "max_drawdown_duration_days": 0.0,
            "avg_drawdown_duration_days": 0.0,
            "max_recovery_duration_days": 0.0,
            "avg_recovery_duration_days": 0.0,
            "total_drawdown_episodes": 0,
            "pct_time_in_drawdown": 0.0,
        }
        return {"underwater_curve": [], "episodes": [], "summary": empty_summary}

    frame = pd.DataFrame.from_records(equity_curve)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["running_peak"] = frame["equity"].cummax()
    frame["underwater_dollars"] = frame["equity"] - frame["running_peak"]
    peaks = frame["running_peak"].replace(0, pd.NA)
    frame["underwater_pct"] = ((frame["equity"] - frame["running_peak"]) / peaks).fillna(0.0) * 100.0

    underwater_curve = [
        {
            "timestamp": row.timestamp.isoformat(),
            "equity": round(float(row.equity), 4),
            "running_peak": round(float(row.running_peak), 4),
            "underwater_dollars": round(float(row.underwater_dollars), 4),
            "underwater_pct": round(float(row.underwater_pct), 4),
        }
        for row in frame.itertuples(index=False)
    ]

    episodes: list[dict[str, Any]] = []
    in_episode = False
    start_idx = 0
    episode_peak_time = None
    for idx, row in enumerate(frame.itertuples(index=False)):
        is_drawdown = float(row.underwater_dollars) < 0.0
        if is_drawdown and not in_episode:
            in_episode = True
            start_idx = idx
            episode_peak_time = frame.iloc[max(idx - 1, 0)]["timestamp"]
        if in_episode and (not is_drawdown or idx == len(frame) - 1):
            end_idx = idx if not is_drawdown else idx
            episode_frame = frame.iloc[start_idx : end_idx + 1]
            trough_idx = int(episode_frame["underwater_dollars"].idxmin())
            trough = frame.loc[trough_idx]
            episode_end_ts = frame.iloc[end_idx]["timestamp"]
            recovered = not is_drawdown
            recovery_end = episode_end_ts if recovered else None
            recovery_start = frame.loc[trough_idx]["timestamp"]
            episodes.append(
                {
                    "episode_start": frame.iloc[start_idx]["timestamp"].isoformat(),
                    "episode_end": episode_end_ts.isoformat(),
                    "episode_duration_bars": len(episode_frame),
                    "episode_duration_days": round(_duration_days(frame.iloc[start_idx]["timestamp"], episode_end_ts), 6),
                    "drawdown_pct": round(abs(float(trough["underwater_pct"])), 4),
                    "drawdown_dollars": round(abs(float(trough["underwater_dollars"])), 4),
                    "recovery_start": recovery_start.isoformat(),
                    "recovery_end": recovery_end.isoformat() if recovery_end is not None else None,
                    "recovery_duration_bars": max(end_idx - trough_idx, 0) if recovered else 0,
                    "recovery_duration_days": round(_duration_days(recovery_start, recovery_end), 6) if recovered else 0.0,
                    "recovered": recovered,
                },
            )
            in_episode = False if not is_drawdown else True

    summary = summarize_drawdown_episodes(frame, episodes)
    return {"underwater_curve": underwater_curve, "episodes": episodes, "summary": summary}


def summarize_drawdown_episodes(frame: pd.DataFrame, episodes: list[dict[str, Any]]) -> dict[str, Any]:
    if not episodes:
        return {
            "max_drawdown_pct": 0.0,
            "max_drawdown_dollars": 0.0,
            "avg_drawdown_pct": 0.0,
            "avg_drawdown_dollars": 0.0,
            "max_drawdown_duration_days": 0.0,
            "avg_drawdown_duration_days": 0.0,
            "max_recovery_duration_days": 0.0,
            "avg_recovery_duration_days": 0.0,
            "total_drawdown_episodes": 0,
            "pct_time_in_drawdown": 0.0,
        }

    drawdown_pcts = [float(item["drawdown_pct"]) for item in episodes]
    drawdown_dollars = [float(item["drawdown_dollars"]) for item in episodes]
    durations = [float(item["episode_duration_days"]) for item in episodes]
    recoveries = [float(item["recovery_duration_days"]) for item in episodes if item["recovered"]]
    pct_time_in_drawdown = round(float((frame["underwater_dollars"] < 0.0).mean() * 100.0), 4)
    return {
        "max_drawdown_pct": round(max(drawdown_pcts), 4),
        "max_drawdown_dollars": round(max(drawdown_dollars), 4),
        "avg_drawdown_pct": round(statistics.mean(drawdown_pcts), 4),
        "avg_drawdown_dollars": round(statistics.mean(drawdown_dollars), 4),
        "max_drawdown_duration_days": round(max(durations), 6),
        "avg_drawdown_duration_days": round(statistics.mean(durations), 6),
        "max_recovery_duration_days": round(max(recoveries), 6) if recoveries else 0.0,
        "avg_recovery_duration_days": round(statistics.mean(recoveries), 6) if recoveries else 0.0,
        "total_drawdown_episodes": len(episodes),
        "pct_time_in_drawdown": pct_time_in_drawdown,
    }


def classify_session(timestamp: pd.Timestamp | datetime) -> str:
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    hour = ts.hour
    minute = ts.minute
    total_minutes = (hour * 60) + minute
    if 13 * 60 + 30 <= total_minutes < 20 * 60:
        return "rth"
    if 0 <= total_minutes < 7 * 60:
        return "asian"
    if 7 * 60 <= total_minutes < 13 * 60 + 30:
        return "london"
    return "globex_overnight"


def timestamp_from_ns(value: int) -> str:
    return datetime.fromtimestamp(value / 1_000_000_000, tz=UTC).isoformat()


def _duration_days(start: pd.Timestamp | None, end: pd.Timestamp | None) -> float:
    if start is None or end is None:
        return 0.0
    return (end - start).total_seconds() / 86_400.0


def _trade_pnl_sharpe(pnls: list[float]) -> float:
    if len(pnls) < 2:
        return 0.0
    std = statistics.pstdev(pnls)
    if std == 0 or math.isnan(std):
        return 0.0
    return statistics.mean(pnls) / std


def _trade_pnl_max_drawdown(equity: list[float]) -> float:
    running_peak = float("-inf")
    max_drawdown = 0.0
    for value in equity:
        running_peak = max(running_peak, value)
        max_drawdown = max(max_drawdown, running_peak - value)
    return max_drawdown
