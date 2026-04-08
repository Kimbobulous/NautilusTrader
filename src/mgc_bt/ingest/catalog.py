from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from nautilus_trader.persistence.catalog import ParquetDataCatalog


def open_catalog(path: Path) -> ParquetDataCatalog:
    path.mkdir(parents=True, exist_ok=True)
    return ParquetDataCatalog(str(path))


def dedupe_contract_instruments(instruments: Iterable[Any], symbol_root: str) -> list[Any]:
    deduped: dict[str, Any] = {}
    for instrument in instruments:
        instrument_id = str(getattr(instrument, "id", ""))
        if type(instrument).__name__ != "FuturesContract":
            continue
        if getattr(instrument, "underlying", None) != symbol_root and not instrument_id.startswith(symbol_root):
            continue
        deduped[instrument_id] = instrument
    return sorted(deduped.values(), key=lambda item: str(item.id))


def instrument_ids_from_instruments(instruments: Iterable[Any]) -> set[str]:
    return {str(instrument.id) for instrument in instruments}


def sort_records_by_ts_init(records: Iterable[Any]) -> list[Any]:
    return sorted(records, key=lambda record: int(getattr(record, "ts_init", 0)))


def filter_market_data(records: Iterable[Any], allowed_instrument_ids: set[str]) -> list[Any]:
    filtered: list[Any] = []
    for record in records:
        instrument_id = instrument_id_from_record(record)
        if instrument_id in allowed_instrument_ids:
            filtered.append(record)
    return filtered


def instrument_id_from_record(record: Any) -> str:
    if hasattr(record, "instrument_id"):
        return str(record.instrument_id)
    if hasattr(record, "bar_type") and hasattr(record.bar_type, "instrument_id"):
        return str(record.bar_type.instrument_id)
    raise ValueError(f"Unsupported record type for instrument ID extraction: {type(record).__name__}")


def timestamp_ns_from_record(record: Any) -> int | None:
    if hasattr(record, "ts_event"):
        value = getattr(record, "ts_event")
        return int(value) if value is not None else None
    return None
