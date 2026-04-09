from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import tempfile
from pathlib import Path
from typing import Any

import optuna
from nautilus_trader.model.data import Bar, TradeTick
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from mgc_bt.backtest.contracts import ContractSelectionError
from mgc_bt.backtest.contracts import resolve_contract_selection
from mgc_bt.config import Settings
from mgc_bt.ingest.discovery import discover_databento_files
from mgc_bt.ingest.validation import validate_discovery
from mgc_bt.optimization.storage import optimization_storage_url


@dataclass(frozen=True)
class PreflightIssue:
    level: str
    message: str
    fix: str | None = None


@dataclass(frozen=True)
class PreflightReport:
    command: str
    failures: list[PreflightIssue]
    warnings: list[PreflightIssue]

    @property
    def ok(self) -> bool:
        return not self.failures


def preflight_ingest(settings: Settings) -> PreflightReport:
    discovery = discover_databento_files(settings)
    failures: list[PreflightIssue] = []
    warnings: list[PreflightIssue] = []

    structural_failures, structural_warnings = validate_discovery(discovery, settings)
    failures.extend(
        PreflightIssue("error", message, "Check your data_root and Databento file layout in settings.toml.")
        for message in structural_failures
    )
    warnings.extend(PreflightIssue("warning", message) for message in structural_warnings)

    _check_path_writable(
        settings.paths.catalog_root,
        failures,
        "Catalog path is not writable.",
        "Choose a writable catalog_root in settings.toml or fix filesystem permissions.",
    )

    if _catalog_has_files(settings.paths.catalog_root):
        warnings.append(
            PreflightIssue(
                "warning",
                f"Catalog path already contains data: {settings.paths.catalog_root}",
                "Running ingest will replace the existing catalog contents at that path.",
            ),
        )

    return PreflightReport("ingest", failures, warnings)


def preflight_backtest(settings: Settings, params: dict[str, Any] | None = None) -> PreflightReport:
    params = params or {}
    failures: list[PreflightIssue] = []
    warnings: list[PreflightIssue] = []

    if not _catalog_has_files(settings.paths.catalog_root):
        failures.append(
            PreflightIssue(
                "error",
                f"Catalog data was not found at {settings.paths.catalog_root}.",
                "Run `python -m mgc_bt ingest` first or point catalog_root at an existing populated catalog.",
            ),
        )
        return PreflightReport("backtest", failures, warnings)

    catalog = ParquetDataCatalog(str(settings.paths.catalog_root))
    instruments = _mgc_instruments(catalog, settings.ingestion.symbol)
    if not instruments:
        failures.append(
            PreflightIssue(
                "error",
                "No MGC futures definitions were found in the catalog.",
                "Re-run ingest and confirm definition files load before market data.",
            ),
        )
        return PreflightReport("backtest", failures, warnings)

    if not _has_any_bars(catalog, instruments):
        failures.append(
            PreflightIssue(
                "error",
                "No 1-minute MGC bars were found in the catalog.",
                "Re-run ingest and confirm bar DBN files are present and enabled.",
            ),
        )
    if not _has_any_trades(catalog, instruments):
        failures.append(
            PreflightIssue(
                "error",
                "No MGC trade ticks were found in the catalog.",
                "Re-run ingest and confirm trade DBN files are present and enabled.",
            ),
        )
    if failures:
        return PreflightReport("backtest", failures, warnings)

    try:
        selection = resolve_contract_selection(
            catalog=catalog,
            symbol_root=settings.ingestion.symbol,
            default_mode=settings.backtest.default_mode,
            requested_instrument_id=_optional_text(params.get("instrument_id")),
            start=_optional_text(params.get("start_date")) or settings.backtest.start_date,
            end=_optional_text(params.get("end_date")) or settings.backtest.end_date,
            roll_preference=settings.backtest.roll_preference,
            calendar_roll_business_days=settings.backtest.calendar_roll_business_days,
        )
    except ContractSelectionError as exc:
        failures.append(
            PreflightIssue(
                "error",
                str(exc),
                "Check the requested instrument/date range and confirm the catalog has matching MGC data.",
            ),
        )
        return PreflightReport("backtest", failures, warnings)

    for window in selection.windows:
        first_trade = catalog.query_first_timestamp(TradeTick, identifier=window.instrument_id)
        last_trade = catalog.query_last_timestamp(TradeTick, identifier=window.instrument_id)
        if first_trade is None or last_trade is None:
            failures.append(
                PreflightIssue(
                    "error",
                    f"No trade ticks were found for {window.instrument_id}.",
                    "Re-run ingest and confirm trade data exists for the requested contract range.",
                ),
            )
            continue
        from pandas import Timestamp

        if first_trade > Timestamp(window.end) or last_trade < Timestamp(window.start):
            failures.append(
                PreflightIssue(
                    "error",
                    f"Requested backtest window has no trade coverage for {window.instrument_id}.",
                    "Adjust start/end dates or ingest a catalog range that covers the requested window.",
                ),
            )

    return PreflightReport("backtest", failures, warnings)


def preflight_optimize(
    settings: Settings,
    *,
    resume: bool,
    study_name: str | None,
) -> PreflightReport:
    failures: list[PreflightIssue] = []
    warnings: list[PreflightIssue] = []

    backtest_report = preflight_backtest(
        settings,
        {
            "instrument_id": None,
            "start_date": settings.optimization.in_sample_start,
            "end_date": settings.optimization.in_sample_end,
        },
    )
    failures.extend(backtest_report.failures)
    warnings.extend(backtest_report.warnings)

    holdout_end = _coerce_datetime(settings.optimization.holdout_end)
    if holdout_end > datetime.now(tz=UTC):
        failures.append(
            PreflightIssue(
                "error",
                "Optimization holdout_end is in the future.",
                "Set [optimization].holdout_end to a completed historical date before running optimize.",
            ),
        )

    storage_path = (settings.paths.results_root / settings.optimization.results_subdir / settings.optimization.storage_filename)
    _check_path_writable(
        storage_path,
        failures,
        "Optuna storage path is not writable.",
        "Choose a writable results_root/optimization storage location or fix filesystem permissions.",
    )

    effective_study_name = study_name or settings.optimization.study_name
    if resume and not _study_exists(settings, effective_study_name):
        failures.append(
            PreflightIssue(
                "error",
                f"Optuna study '{effective_study_name}' does not exist in storage.",
                "Run optimize without --resume first, or use the correct --study-name for an existing study.",
            ),
        )

    return PreflightReport("optimize", failures, warnings)


def render_preflight_failure(report: PreflightReport) -> str:
    lines = [f"{report.command} preflight failed:"]
    for issue in report.failures:
        lines.append(f"- {issue.message}")
        if issue.fix:
            lines.append(f"  Fix: {issue.fix}")
    return "\n".join(lines)


def render_preflight_warnings(report: PreflightReport) -> str | None:
    if not report.warnings:
        return None
    lines = [f"{report.command} preflight warnings:"]
    for issue in report.warnings:
        lines.append(f"- {issue.message}")
        if issue.fix:
            lines.append(f"  Note: {issue.fix}")
    return "\n".join(lines)


def _catalog_has_files(path: Path) -> bool:
    return path.exists() and any(path.rglob("*.parquet"))


def _check_path_writable(
    target: Path,
    failures: list[PreflightIssue],
    message: str,
    fix: str,
) -> None:
    try:
        parent = target if target.suffix == "" else target.parent
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=parent, delete=True):
            pass
    except OSError:
        failures.append(PreflightIssue("error", f"{message} Target: {target}", fix))


def _mgc_instruments(catalog: ParquetDataCatalog, symbol_root: str) -> list[Any]:
    instruments: list[Any] = []
    for instrument in catalog.instruments():
        if type(instrument).__name__ != "FuturesContract":
            continue
        if getattr(instrument, "underlying", None) != symbol_root and not str(instrument.id).startswith(symbol_root):
            continue
        instruments.append(instrument)
    return instruments


def _has_any_bars(catalog: ParquetDataCatalog, instruments: list[Any]) -> bool:
    for instrument in instruments:
        bar_type = f"{instrument.id}-1-MINUTE-LAST-EXTERNAL"
        if catalog.query_first_timestamp(Bar, identifier=bar_type) is not None:
            return True
    return False


def _has_any_trades(catalog: ParquetDataCatalog, instruments: list[Any]) -> bool:
    for instrument in instruments:
        if catalog.query_first_timestamp(TradeTick, identifier=str(instrument.id)) is not None:
            return True
    return False


def _coerce_datetime(value: str) -> datetime:
    from pandas import Timestamp

    return Timestamp(value, tz="UTC").to_pydatetime()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _study_exists(settings: Settings, study_name: str) -> bool:
    storage_path = settings.paths.results_root / settings.optimization.results_subdir / settings.optimization.storage_filename
    if not storage_path.exists():
        return False
    try:
        summaries = optuna.study.get_all_study_summaries(storage=optimization_storage_url(settings))
    except Exception:
        return False
    return any(summary.study_name == study_name for summary in summaries)
