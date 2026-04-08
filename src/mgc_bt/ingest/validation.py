from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mgc_bt.ingest.discovery import DiscoveryResult

if TYPE_CHECKING:
    from mgc_bt.config import Settings
    from mgc_bt.ingest.service import IngestResult


def validate_discovery(discovery: DiscoveryResult, settings: Settings) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    if settings.ingestion.load_definitions and not discovery.definition_files:
        failures.append("No definition DBN files were discovered.")
    if settings.ingestion.load_bars and not discovery.bar_files:
        failures.append("No OHLCV-1M DBN files were discovered.")
    if settings.ingestion.load_trades and not discovery.trade_files:
        failures.append("No trade DBN files were discovered.")
    if not settings.paths.data_root.exists():
        failures.append(f"Configured data_root does not exist: {settings.paths.data_root}")

    metadata_by_folder = {item.folder.name: item for item in discovery.metadata}
    bar_metadata = metadata_by_folder.get("ohcl-1m")
    if bar_metadata and bar_metadata.schema != settings.ingestion.bar_schema:
        failures.append(
            f"Bar folder metadata schema mismatch: expected {settings.ingestion.bar_schema}, found {bar_metadata.schema!r}.",
        )

    if discovery.mbp1_files and not settings.ingestion.load_mbp1:
        warnings.append(
            f"MBP-1 files detected ({len(discovery.mbp1_files)}) but ignored in Phase 1 because load_mbp1=false.",
        )

    warnings.extend(_condition_warnings(discovery))
    return failures, warnings


def validate_ingest_result(result: IngestResult, settings: Settings) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    if result.definitions.records_written <= 0:
        failures.append("No MGC futures contracts were written to the catalog.")
    if settings.ingestion.load_bars and result.bars.records_written <= 0:
        failures.append("No MGC bar records were written to the catalog.")
    if settings.ingestion.load_trades and result.trades.records_written <= 0:
        failures.append("No MGC trade records were written to the catalog.")
    if not result.instrument_ids:
        failures.append("No MGC instrument IDs were resolved from the definition files.")

    if settings.ingestion.load_bars and result.date_range_start is None:
        failures.append("Bar ingestion completed without a detectable date range.")
    if result.discovery.bar_files and len(result.discovery.bar_files) == 1:
        warnings.append("Bars are sourced from a single date-range DBN file; discovery is intentionally schema-based.")

    return failures, warnings


def _condition_warnings(discovery: DiscoveryResult) -> list[str]:
    warnings: list[str] = []
    for item in discovery.metadata:
        if item.condition_path is None or not item.condition_path.exists():
            continue
        degraded_dates = _read_degraded_dates(item.condition_path)
        if degraded_dates:
            preview = ", ".join(degraded_dates[:3])
            suffix = "..." if len(degraded_dates) > 3 else ""
            warnings.append(
                f"{item.folder.name} has {len(degraded_dates)} degraded Databento day(s): {preview}{suffix}",
            )
    return warnings


def _read_degraded_dates(path: Path) -> list[str]:
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [str(entry.get("date")) for entry in raw if entry.get("condition") == "degraded"]
