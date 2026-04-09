from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import json
from typing import Any


SECTION_UNAVAILABLE_PREFIX = "Section unavailable - "


@dataclass(frozen=True)
class TearsheetPayload:
    run_dir: Path
    run_type: str
    shared_run_dir: Path
    summary: dict[str, Any]
    trades: list[dict[str, Any]]
    run_config_text: str
    manifest: dict[str, Any] | None
    underwater_curve: list[dict[str, Any]] | None
    drawdown_episodes: list[dict[str, Any]] | None
    breakdowns: dict[str, list[dict[str, Any]]]
    audit_log: list[dict[str, Any]] | None
    optimization_summary: dict[str, Any] | None
    ranked_results: list[dict[str, Any]] | None
    parameter_sensitivity: list[dict[str, Any]] | None
    walk_forward_summary: dict[str, Any] | None
    walk_forward_windows: list[dict[str, Any]] | None
    monte_carlo_summary: dict[str, Any] | None
    monte_carlo_confidence_bands: list[dict[str, Any]] | None
    stability_summary: dict[str, Any] | None
    stability_heatmap_rows: list[dict[str, Any]] | None
    notices: dict[str, str]


def load_tearsheet_payload(run_dir: Path | str) -> TearsheetPayload:
    root = Path(run_dir)
    if (root / "optimization_summary.json").exists():
        return _load_optimization_payload(root)
    return _load_backtest_payload(root)


def missing_notice(filename: str) -> str:
    return f"{SECTION_UNAVAILABLE_PREFIX}{filename} not found"


def _load_backtest_payload(run_dir: Path) -> TearsheetPayload:
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(missing_notice("summary.json"))
    notices: dict[str, str] = {}
    return TearsheetPayload(
        run_dir=run_dir,
        run_type="backtest",
        shared_run_dir=run_dir,
        summary=_read_json(summary_path),
        trades=_read_csv(run_dir / "trades.csv", notices=notices),
        run_config_text=_read_text(run_dir / "run_config.toml", notices=notices),
        manifest=_read_json_if_exists(run_dir / "manifest.json"),
        underwater_curve=_read_csv_optional(run_dir / "analytics" / "underwater_curve.csv", notices=notices),
        drawdown_episodes=_read_csv_optional(run_dir / "analytics" / "drawdown_episodes.csv", notices=notices),
        breakdowns=_read_breakdowns(run_dir / "analytics" / "breakdowns", notices),
        audit_log=_read_csv_optional(run_dir / "analytics" / "audit_log.csv", notices=notices),
        optimization_summary=None,
        ranked_results=None,
        parameter_sensitivity=None,
        walk_forward_summary=None,
        walk_forward_windows=None,
        monte_carlo_summary=None,
        monte_carlo_confidence_bands=None,
        stability_summary=None,
        stability_heatmap_rows=None,
        notices=notices,
    )


def _load_optimization_payload(run_dir: Path) -> TearsheetPayload:
    notices: dict[str, str] = {}
    shared_run_dir = run_dir / "best_run"
    summary_path = shared_run_dir / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(missing_notice("summary.json"))
    return TearsheetPayload(
        run_dir=run_dir,
        run_type="optimize",
        shared_run_dir=shared_run_dir,
        summary=_read_json(summary_path),
        trades=_read_csv(shared_run_dir / "trades.csv", notices=notices),
        run_config_text=_read_text(shared_run_dir / "run_config.toml", notices=notices),
        manifest=_read_json_if_exists(run_dir / "manifest.json"),
        underwater_curve=_read_csv_optional(shared_run_dir / "analytics" / "underwater_curve.csv", notices=notices),
        drawdown_episodes=_read_csv_optional(shared_run_dir / "analytics" / "drawdown_episodes.csv", notices=notices),
        breakdowns=_read_breakdowns(shared_run_dir / "analytics" / "breakdowns", notices),
        audit_log=_read_csv_optional(shared_run_dir / "analytics" / "audit_log.csv", notices=notices),
        optimization_summary=_read_json_if_exists(run_dir / "optimization_summary.json"),
        ranked_results=_read_csv_optional(run_dir / "ranked_results.csv", notices=notices),
        parameter_sensitivity=_read_csv_optional(run_dir / "analytics" / "parameter_sensitivity.csv", notices=notices),
        walk_forward_summary=_read_json_if_exists(run_dir / "walk_forward" / "aggregated_summary.json"),
        walk_forward_windows=_read_csv_optional(run_dir / "walk_forward" / "window_results.csv", notices=notices),
        monte_carlo_summary=_read_json_if_exists(run_dir / "monte_carlo" / "monte_carlo_summary.json"),
        monte_carlo_confidence_bands=_read_csv_optional(run_dir / "monte_carlo" / "equity_confidence_bands.csv", notices=notices),
        stability_summary=_read_json_if_exists(run_dir / "stability" / "stability_summary.json"),
        stability_heatmap_rows=_read_csv_optional(run_dir / "stability" / "top_pair_heatmap.csv", notices=notices),
        notices=notices,
    )


def _read_breakdowns(directory: Path, notices: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    filenames = {
        "by_session": "by_session.csv",
        "by_volatility_regime": "by_volatility_regime.csv",
        "by_month": "by_month.csv",
        "by_year": "by_year.csv",
        "by_day_of_week": "by_day_of_week.csv",
        "by_hour": "by_hour.csv",
    }
    rows: dict[str, list[dict[str, Any]]] = {}
    for key, filename in filenames.items():
        path = directory / filename
        if path.exists():
            rows[key] = _read_csv_rows(path)
        else:
            notices[key] = missing_notice(filename)
            rows[key] = []
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json(path)


def _read_text(path: Path, *, notices: dict[str, str]) -> str:
    if not path.exists():
        notices[path.name] = missing_notice(path.name)
        return ""
    return path.read_text(encoding="utf-8")


def _read_csv(path: Path, *, notices: dict[str, str]) -> list[dict[str, Any]]:
    if not path.exists():
        notices[path.name] = missing_notice(path.name)
        return []
    return _read_csv_rows(path)


def _read_csv_optional(path: Path, *, notices: dict[str, str]) -> list[dict[str, Any]] | None:
    if not path.exists():
        notices[path.name] = missing_notice(path.name)
        return None
    return _read_csv_rows(path)


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
