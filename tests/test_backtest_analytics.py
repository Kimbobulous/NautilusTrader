from __future__ import annotations

from pathlib import Path
import csv
import json

from mgc_bt.backtest.analytics import AuditLogWriter
from mgc_bt.backtest.analytics import build_breakdown_rows
from mgc_bt.backtest.analytics import classify_session
from mgc_bt.backtest.analytics import compute_drawdown_analysis
from mgc_bt.backtest.analytics import write_backtest_analytics


def test_audit_writer_streams_required_columns(tmp_path: Path) -> None:
    audit_path = tmp_path / "analytics" / "audit_log.csv"
    writer = AuditLogWriter(audit_path)
    writer.open()
    writer.write_row(
        {
            "record_type": "armed_bar",
            "timestamp": "2021-03-08T00:10:00+00:00",
            "instrument_id": "MGCJ1.GLBX",
            "optional_confirmation_count": 1,
            "entry_fired": False,
            "entry_rejected_reason": "core_triggers_failed",
        },
    )
    writer.close()

    with audit_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert rows[0]["entry_rejected_reason"] == "core_triggers_failed"


def test_write_backtest_analytics_creates_breakdowns_and_drawdown_files(tmp_path: Path) -> None:
    result = {
        "trade_log": [],
        "analytics_trade_log": [
            {
                "instrument_id": "MGCJ1.GLBX",
                "entry_timestamp": "2021-03-08T13:45:00+00:00",
                "exit_timestamp": "2021-03-08T13:55:00+00:00",
                "direction": "long",
                "pnl_dollars": 10.0,
                "realized_pnl": 10.0,
                "session_at_entry": "rth",
                "volatility_cluster_at_entry": 2,
                "opened_at": "2021-03-08T13:45:00+00:00",
            },
            {
                "instrument_id": "MGCJ1.GLBX",
                "entry_timestamp": "2021-03-09T01:10:00+00:00",
                "exit_timestamp": "2021-03-09T01:30:00+00:00",
                "direction": "short",
                "pnl_dollars": -5.0,
                "realized_pnl": -5.0,
                "session_at_entry": "asian",
                "volatility_cluster_at_entry": 3,
                "opened_at": "2021-03-09T01:10:00+00:00",
            },
        ],
        "equity_curve": [
            {"timestamp": "2021-03-08T13:30:00+00:00", "equity": 50000.0},
            {"timestamp": "2021-03-08T13:45:00+00:00", "equity": 50010.0},
            {"timestamp": "2021-03-09T01:30:00+00:00", "equity": 50005.0},
        ],
    }

    bundle = write_backtest_analytics(result, tmp_path)

    assert (tmp_path / "analytics" / "drawdown_episodes.csv").exists()
    assert (tmp_path / "analytics" / "underwater_curve.csv").exists()
    assert (tmp_path / "analytics" / "breakdowns" / "by_session.csv").exists()
    assert bundle.summary_updates["total_drawdown_episodes"] >= 1


def test_drawdown_analysis_includes_recovery_fields() -> None:
    analysis = compute_drawdown_analysis(
        [
            {"timestamp": "2021-03-08T00:00:00+00:00", "equity": 100.0},
            {"timestamp": "2021-03-08T00:01:00+00:00", "equity": 90.0},
            {"timestamp": "2021-03-08T00:02:00+00:00", "equity": 110.0},
        ],
    )
    assert analysis["episodes"]
    assert "recovery_duration_days" in analysis["episodes"][0]
    assert "recovered" in analysis["episodes"][0]
