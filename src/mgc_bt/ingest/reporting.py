from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mgc_bt.ingest.service import IngestResult


def render_ingest_report(result: "IngestResult") -> str:
    lines = [
        "Ingest complete",
        f"Catalog: {result.catalog_path}",
        (
            "Definitions: "
            f"{result.definitions.records_written} written "
            f"from {result.definitions.files_discovered} file(s)"
        ),
        f"Bars: {result.bars.records_written} written from {result.bars.files_discovered} file(s)",
        f"Trades: {result.trades.records_written} written from {result.trades.files_discovered} file(s)",
        f"Date range: {result.date_range_start or 'n/a'} -> {result.date_range_end or 'n/a'}",
        f"Instruments: {', '.join(result.instrument_ids[:5])}" + (" ..." if len(result.instrument_ids) > 5 else ""),
    ]
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in result.warnings)
    else:
        lines.append("Warnings: none")
    return "\n".join(lines)
