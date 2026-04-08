from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pandas as pd
from nautilus_trader.model.data import Bar
from nautilus_trader.persistence.catalog import ParquetDataCatalog


@dataclass(frozen=True)
class ContractWindow:
    instrument_id: str
    bar_type: str
    start: datetime
    end: datetime
    roll_reason: str


@dataclass(frozen=True)
class ContractSelection:
    mode: str
    requested_instrument_id: str | None
    roll_source: str
    windows: list[ContractWindow]


class ContractSelectionError(RuntimeError):
    """Raised when contract resolution cannot produce a valid backtest window."""


def resolve_contract_selection(
    catalog: ParquetDataCatalog,
    symbol_root: str,
    default_mode: str,
    requested_instrument_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    roll_preference: str = "open_interest",
    calendar_roll_business_days: int = 5,
) -> ContractSelection:
    contracts = _load_contract_metadata(catalog, symbol_root)
    if not contracts:
        raise ContractSelectionError(f"No outright {symbol_root} futures contracts were found in the catalog.")

    requested_start = _coerce_datetime(start)
    requested_end = _coerce_datetime(end)
    if requested_start and requested_end and requested_start >= requested_end:
        raise ContractSelectionError("Backtest start must be earlier than backtest end.")

    if requested_instrument_id:
        contract = next((item for item in contracts if item.instrument_id == requested_instrument_id), None)
        if contract is None:
            raise ContractSelectionError(f"Instrument '{requested_instrument_id}' was not found in the catalog.")
        window = _window_for_contract(contract, requested_start, requested_end)
        return ContractSelection(
            mode="single_contract",
            requested_instrument_id=requested_instrument_id,
            roll_source="explicit",
            windows=[window],
        )

    if default_mode != "auto_roll":
        raise ContractSelectionError(
            f"Unsupported backtest mode '{default_mode}'. Expected 'auto_roll' or an explicit instrument override.",
        )

    roll_source = "open_interest" if _open_interest_available(catalog, contracts) and roll_preference == "open_interest" else "calendar_fallback"
    windows = _auto_roll_windows(
        contracts=contracts,
        requested_start=requested_start,
        requested_end=requested_end,
        calendar_roll_business_days=calendar_roll_business_days,
        roll_source=roll_source,
    )
    if not windows:
        raise ContractSelectionError("Auto-roll could not resolve any contract windows for the requested range.")

    return ContractSelection(
        mode="auto_roll",
        requested_instrument_id=None,
        roll_source=roll_source,
        windows=windows,
    )


@dataclass(frozen=True)
class _ContractMetadata:
    instrument_id: str
    bar_type: str
    activation: datetime
    expiration: datetime
    data_start: datetime
    data_end: datetime


def _load_contract_metadata(catalog: ParquetDataCatalog, symbol_root: str) -> list[_ContractMetadata]:
    contracts: list[_ContractMetadata] = []
    for instrument in catalog.instruments():
        if type(instrument).__name__ != "FuturesContract":
            continue
        if getattr(instrument, "underlying", None) != symbol_root:
            continue

        instrument_id = str(instrument.id)
        bar_type = f"{instrument_id}-1-MINUTE-LAST-EXTERNAL"
        first_bar = catalog.query_first_timestamp(Bar, identifier=bar_type)
        last_bar = catalog.query_last_timestamp(Bar, identifier=bar_type)
        if first_bar is None or last_bar is None:
            continue

        activation_ns = int(getattr(instrument, "activation_ns", 0))
        expiration_ns = int(getattr(instrument, "expiration_ns", 0))
        contracts.append(
            _ContractMetadata(
                instrument_id=instrument_id,
                bar_type=bar_type,
                activation=_ns_to_datetime(activation_ns) if activation_ns else first_bar.to_pydatetime(),
                expiration=_ns_to_datetime(expiration_ns) if expiration_ns else last_bar.to_pydatetime(),
                data_start=first_bar.to_pydatetime(),
                data_end=last_bar.to_pydatetime(),
            ),
        )

    return sorted(contracts, key=lambda item: item.activation)


def _window_for_contract(
    contract: _ContractMetadata,
    requested_start: datetime | None,
    requested_end: datetime | None,
) -> ContractWindow:
    start = max(filter(None, [contract.data_start, requested_start]))
    end_candidates = [contract.data_end]
    if requested_end is not None:
        end_candidates.append(requested_end)
    end = min(end_candidates)
    if start >= end:
        raise ContractSelectionError(
            f"Requested range does not overlap available data for {contract.instrument_id}.",
        )
    return ContractWindow(
        instrument_id=contract.instrument_id,
        bar_type=contract.bar_type,
        start=start,
        end=end,
        roll_reason="single_contract",
    )


def _auto_roll_windows(
    contracts: list[_ContractMetadata],
    requested_start: datetime | None,
    requested_end: datetime | None,
    calendar_roll_business_days: int,
    roll_source: str,
) -> list[ContractWindow]:
    windows: list[ContractWindow] = []
    active_start = requested_start or min(item.data_start for item in contracts)
    hard_end = requested_end or max(item.data_end for item in contracts)

    for index, contract in enumerate(contracts):
        if contract.data_end < active_start:
            continue
        if contract.data_start > hard_end:
            break

        segment_start = max(contract.data_start, active_start)
        segment_end = min(contract.data_end, hard_end)
        if index < len(contracts) - 1:
            roll_cutoff = _calendar_roll_cutoff(contract.expiration, calendar_roll_business_days)
            next_contract = contracts[index + 1]
            segment_end = min(segment_end, roll_cutoff, next_contract.data_end)

        if segment_start >= segment_end:
            continue

        windows.append(
            ContractWindow(
                instrument_id=contract.instrument_id,
                bar_type=contract.bar_type,
                start=segment_start,
                end=segment_end,
                roll_reason=roll_source,
            ),
        )
        active_start = segment_end + timedelta(minutes=1)
        if active_start >= hard_end:
            break

    return windows


def _calendar_roll_cutoff(expiration: datetime, business_days_before: int) -> datetime:
    remaining = business_days_before
    current = expiration
    while remaining > 0:
        current -= timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def _open_interest_available(catalog: ParquetDataCatalog, contracts: list[_ContractMetadata]) -> bool:
    # Phase 1 only ingested definitions, 1-minute bars, and trades. Keep the detection
    # hook explicit so future catalog-touching phases remember that definitions were
    # legacy Cython decoded while bars/trades used as_legacy_cython=False.
    return False


def _coerce_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return pd.Timestamp(value, tz="UTC").to_pydatetime()


def _ns_to_datetime(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1_000_000_000, tz=UTC)
