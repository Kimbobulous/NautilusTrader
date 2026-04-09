from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
import math
from typing import Any

import pandas as pd
from nautilus_trader.backtest.results import BacktestResult


@dataclass(frozen=True)
class SegmentExecutionResult:
    instrument_id: str
    start_date: str
    end_date: str
    total_pnl: float
    sharpe_ratio: float | None
    win_rate: float
    max_drawdown: float
    max_drawdown_pct: float
    total_trades: int
    trade_log: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]


def build_segment_execution_result(
    result: BacktestResult,
    instrument_id: str,
    start_date: str,
    end_date: str,
    fills_report: pd.DataFrame,
    positions_report: pd.DataFrame,
    account_report: pd.DataFrame,
) -> SegmentExecutionResult:
    closed_positions = _closed_positions_frame(positions_report)
    equity_frame = _equity_frame(account_report)

    return SegmentExecutionResult(
        instrument_id=instrument_id,
        start_date=start_date,
        end_date=end_date,
        total_pnl=_result_total_pnl(result),
        sharpe_ratio=_compute_sharpe_ratio(equity_frame),
        win_rate=_compute_win_rate(closed_positions),
        max_drawdown=_compute_max_drawdown(equity_frame),
        max_drawdown_pct=_compute_max_drawdown_pct(equity_frame),
        total_trades=len(closed_positions),
        trade_log=_trade_log_records(closed_positions, fills_report),
        equity_curve=_equity_curve_records(equity_frame),
    )


def aggregate_execution_results(
    mode: str,
    symbol_root: str,
    parameters: dict[str, Any],
    segments: list[SegmentExecutionResult],
) -> dict[str, Any]:
    combined_trades = [trade for segment in segments for trade in segment.trade_log]
    equity_frame = _combine_equity_curves(segments)
    instrument_id = segments[0].instrument_id if mode == "single_contract" and segments else f"AUTO_ROLL:{symbol_root}"

    summary = {
        "mode": mode,
        "instrument_id": instrument_id,
        "segment_instruments": [segment.instrument_id for segment in segments],
        "segment_count": len(segments),
        "start_date": segments[0].start_date if segments else None,
        "end_date": segments[-1].end_date if segments else None,
        "total_pnl": float(sum(segment.total_pnl for segment in segments)),
        "sharpe_ratio": _compute_sharpe_ratio(equity_frame),
        "win_rate": _compute_aggregate_win_rate(combined_trades),
        "max_drawdown": _compute_max_drawdown(equity_frame),
        "max_drawdown_pct": _compute_max_drawdown_pct(equity_frame),
        "total_trades": len(combined_trades),
        "parameters": parameters,
        "segments": [
            {
                "instrument_id": segment.instrument_id,
                "start_date": segment.start_date,
                "end_date": segment.end_date,
                "total_pnl": segment.total_pnl,
                "total_trades": segment.total_trades,
                "roll_reason": parameters.get("roll_source"),
            }
            for segment in segments
        ],
        "trade_log": combined_trades,
        "equity_curve": _equity_curve_records(equity_frame),
    }
    return summary


def _result_total_pnl(result: BacktestResult) -> float:
    pnl_buckets = next(iter(result.stats_pnls.values()), {})
    return float(pnl_buckets.get("PnL (total)", 0.0))


def _closed_positions_frame(positions_report: pd.DataFrame) -> pd.DataFrame:
    if positions_report.empty:
        return positions_report.copy()
    frame = positions_report.copy()
    return frame[frame["side"] == "FLAT"].copy()


def _equity_frame(account_report: pd.DataFrame) -> pd.DataFrame:
    if account_report.empty:
        raise RuntimeError("Backtest account report was empty.")
    frame = account_report.copy()
    frame["equity"] = frame["total"].map(_money_text_to_float)
    return frame[["equity"]]


def _compute_win_rate(closed_positions: pd.DataFrame) -> float:
    if closed_positions.empty:
        return 0.0
    pnls = closed_positions["realized_pnl"].map(_money_text_to_float)
    return round(float((pnls > 0).mean() * 100.0), 4)


def _compute_aggregate_win_rate(trade_log: list[dict[str, Any]]) -> float:
    if not trade_log:
        return 0.0
    winners = sum(1 for trade in trade_log if float(trade["realized_pnl"]) > 0)
    return round((winners / len(trade_log)) * 100.0, 4)


def _compute_max_drawdown(equity_frame: pd.DataFrame) -> float:
    peaks = equity_frame["equity"].cummax()
    drawdown = peaks - equity_frame["equity"]
    return round(float(drawdown.max()), 4)


def _compute_max_drawdown_pct(equity_frame: pd.DataFrame) -> float:
    peaks = equity_frame["equity"].cummax().replace(0, pd.NA)
    drawdown_pct = (peaks - equity_frame["equity"]) / peaks
    return round(float(drawdown_pct.fillna(0).max() * 100.0), 4)


def _compute_sharpe_ratio(equity_frame: pd.DataFrame) -> float | None:
    returns = equity_frame["equity"].pct_change().dropna()
    if returns.empty:
        return None
    std = float(returns.std())
    if std == 0 or math.isnan(std):
        return None
    annualization_factor = sqrt(252 * 24 * 60)
    sharpe = (float(returns.mean()) / std) * annualization_factor
    if math.isnan(sharpe) or math.isinf(sharpe):
        return None
    return round(sharpe, 6)


def _trade_log_records(closed_positions: pd.DataFrame, fills_report: pd.DataFrame) -> list[dict[str, Any]]:
    if closed_positions.empty:
        return []
    fill_lookup = fills_report.set_index("position_id") if not fills_report.empty and "position_id" in fills_report.columns else None
    records: list[dict[str, Any]] = []
    for _, row in closed_positions.iterrows():
        position_id = row["opening_order_id"] if "opening_order_id" in row else None
        records.append(
            {
                "instrument_id": str(row["instrument_id"]),
                "entry_side": str(row["entry"]),
                "quantity": float(row["peak_qty"]),
                "opened_at": row["ts_opened"].isoformat(),
                "closed_at": row["ts_closed"].isoformat(),
                "avg_px_open": float(row["avg_px_open"]),
                "avg_px_close": float(row["avg_px_close"]),
                "realized_pnl": _money_text_to_float(row["realized_pnl"]),
                "realized_return": float(row["realized_return"]),
                "commissions": _sum_commissions(row["commissions"]),
                "position_id": position_id,
                "slippage": _position_slippage(fill_lookup, row),
            },
        )
    return records


def _position_slippage(fill_lookup: pd.DataFrame | None, row: pd.Series) -> float:
    if fill_lookup is None:
        return 0.0
    try:
        position_rows = fill_lookup.loc[row["opening_order_id"]]
    except KeyError:
        return 0.0
    if isinstance(position_rows, pd.Series):
        position_rows = position_rows.to_frame().T
    if "slippage" not in position_rows.columns:
        return 0.0
    return round(float(position_rows["slippage"].fillna(0).sum()), 4)


def _equity_curve_records(equity_frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {
            "timestamp": timestamp.isoformat(),
            "equity": round(float(value), 4),
        }
        for timestamp, value in equity_frame["equity"].items()
    ]


def _combine_equity_curves(segments: list[SegmentExecutionResult]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for segment in segments:
        records.extend(segment.equity_curve)
    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        raise RuntimeError("No equity curve records were produced by the backtest.")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.drop_duplicates(subset=["timestamp", "equity"]).sort_values("timestamp")
    frame = frame.set_index("timestamp")
    return frame[["equity"]]


def _money_text_to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").strip()
    if " " in text:
        text = text.split(" ", maxsplit=1)[0]
    return float(text)


def _sum_commissions(value: Any) -> float:
    if value in (None, [], ()):
        return 0.0
    if isinstance(value, list):
        return round(sum(_money_text_to_float(item) for item in value), 4)
    return round(_money_text_to_float(value), 4)
