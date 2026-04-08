from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import shutil

from nautilus_trader.adapters.databento.loaders import DatabentoDataLoader

from mgc_bt.config import Settings
from mgc_bt.ingest.catalog import (
    dedupe_contract_instruments,
    filter_market_data,
    instrument_ids_from_instruments,
    open_catalog,
    sort_records_by_ts_init,
    timestamp_ns_from_record,
)
from mgc_bt.ingest.discovery import DiscoveryResult, discover_databento_files
from mgc_bt.ingest.reporting import render_ingest_report
from mgc_bt.ingest.validation import validate_discovery, validate_ingest_result


@dataclass(frozen=True)
class DataWriteStats:
    files_discovered: int
    records_written: int


@dataclass(frozen=True)
class IngestResult:
    catalog_path: Path
    discovery: DiscoveryResult
    definitions: DataWriteStats
    bars: DataWriteStats
    trades: DataWriteStats
    instrument_ids: list[str]
    date_range_start: str | None
    date_range_end: str | None
    warnings: list[str]


class IngestError(RuntimeError):
    """Raised when the ingest flow fails structurally."""


def run_ingest(settings: Settings) -> IngestResult:
    discovery = discover_databento_files(settings)
    failures, warnings = validate_discovery(discovery, settings)
    if failures:
        raise IngestError(_format_failures(failures))

    if settings.paths.catalog_root.exists():
        shutil.rmtree(settings.paths.catalog_root)
    settings.paths.results_root.mkdir(parents=True, exist_ok=True)

    loader = DatabentoDataLoader()
    catalog = open_catalog(settings.paths.catalog_root)

    contract_instruments = _load_contract_instruments(loader, discovery, settings)
    catalog.write_data(sort_records_by_ts_init(contract_instruments))
    instrument_ids = sorted(instrument_ids_from_instruments(contract_instruments))
    if not instrument_ids:
        raise IngestError("Definitions loaded but no MGC futures contracts were resolved.")

    total_bar_count = 0
    total_trade_count = 0
    min_ts: int | None = None
    max_ts: int | None = None

    if settings.ingestion.load_bars:
        for path in discovery.bar_files:
            bars = loader.from_dbn_file(path=path, as_legacy_cython=False)
            filtered_bars = filter_market_data(bars, set(instrument_ids))
            if filtered_bars:
                ordered_bars = sort_records_by_ts_init(filtered_bars)
                catalog.write_data(ordered_bars)
                total_bar_count += len(filtered_bars)
                min_ts, max_ts = _update_date_range(min_ts, max_ts, ordered_bars)

    if settings.ingestion.load_trades:
        for path in discovery.trade_files:
            trades = loader.from_dbn_file(path=path, as_legacy_cython=False)
            filtered_trades = filter_market_data(trades, set(instrument_ids))
            if filtered_trades:
                ordered_trades = sort_records_by_ts_init(filtered_trades)
                catalog.write_data(ordered_trades)
                total_trade_count += len(filtered_trades)
                min_ts, max_ts = _update_date_range(min_ts, max_ts, ordered_trades)

    result = IngestResult(
        catalog_path=settings.paths.catalog_root,
        discovery=discovery,
        definitions=DataWriteStats(
            files_discovered=len(discovery.definition_files),
            records_written=len(contract_instruments),
        ),
        bars=DataWriteStats(
            files_discovered=len(discovery.bar_files),
            records_written=total_bar_count,
        ),
        trades=DataWriteStats(
            files_discovered=len(discovery.trade_files),
            records_written=total_trade_count,
        ),
        instrument_ids=instrument_ids,
        date_range_start=_format_timestamp(min_ts),
        date_range_end=_format_timestamp(max_ts),
        warnings=warnings,
    )
    post_failures, post_warnings = validate_ingest_result(result, settings)
    if post_failures:
        raise IngestError(_format_failures(post_failures))

    if post_warnings:
        return IngestResult(
            catalog_path=result.catalog_path,
            discovery=result.discovery,
            definitions=result.definitions,
            bars=result.bars,
            trades=result.trades,
            instrument_ids=result.instrument_ids,
            date_range_start=result.date_range_start,
            date_range_end=result.date_range_end,
            warnings=[*result.warnings, *post_warnings],
        )

    return result


def render_ingest_cli_output(result: IngestResult) -> str:
    return render_ingest_report(result)


def _load_contract_instruments(
    loader: DatabentoDataLoader,
    discovery: DiscoveryResult,
    settings: Settings,
) -> list[object]:
    all_instruments: list[object] = []
    for path in discovery.definition_files:
        # Nautilus 1.225.0 writes Databento market data to the catalog cleanly from PyO3
        # objects, but Databento FuturesContract definitions still need legacy Cython
        # decoding for catalog serialization.
        all_instruments.extend(loader.from_dbn_file(path=path, as_legacy_cython=True))
    return dedupe_contract_instruments(all_instruments, settings.ingestion.symbol)


def _update_date_range(min_ts: int | None, max_ts: int | None, records: list[object]) -> tuple[int | None, int | None]:
    for record in records:
        ts = timestamp_ns_from_record(record)
        if ts is None:
            continue
        min_ts = ts if min_ts is None else min(min_ts, ts)
        max_ts = ts if max_ts is None else max(max_ts, ts)
    return min_ts, max_ts


def _format_timestamp(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1_000_000_000, tz=UTC).isoformat()


def _format_failures(failures: list[str]) -> str:
    return "Structural ingest validation failed:\n- " + "\n- ".join(failures)
