from __future__ import annotations

from datetime import UTC
from datetime import datetime
from pathlib import Path

from nautilus_trader.persistence.catalog import ParquetDataCatalog

from mgc_bt.backtest.configuration import build_venue_config
from mgc_bt.backtest.configuration import BAR_INTERVAL_NANOS
from mgc_bt.backtest.contracts import _calendar_roll_cutoff
from mgc_bt.backtest.contracts import resolve_contract_selection
from mgc_bt.config import load_settings


def test_calendar_roll_cutoff_uses_business_days() -> None:
    expiration = datetime(2024, 6, 27, 17, 0, tzinfo=UTC)
    cutoff = _calendar_roll_cutoff(expiration, business_days_before=5)
    assert cutoff == datetime(2024, 6, 20, 17, 0, tzinfo=UTC)


def test_single_contract_selection_from_real_catalog() -> None:
    catalog = ParquetDataCatalog("catalog")
    selection = resolve_contract_selection(
        catalog=catalog,
        symbol_root="MGC",
        default_mode="auto_roll",
        requested_instrument_id="MGCM4.GLBX",
        start="2024-01-01T00:00:00+00:00",
        end="2024-02-01T00:00:00+00:00",
    )

    assert selection.mode == "single_contract"
    assert selection.windows[0].instrument_id == "MGCM4.GLBX"
    assert selection.windows[0].bar_type == "MGCM4.GLBX-1-MINUTE-LAST-EXTERNAL"


def test_auto_roll_selection_falls_back_when_open_interest_is_unavailable() -> None:
    catalog = ParquetDataCatalog("catalog")
    selection = resolve_contract_selection(
        catalog=catalog,
        symbol_root="MGC",
        default_mode="auto_roll",
        start="2024-01-01T00:00:00+00:00",
        end="2024-06-01T00:00:00+00:00",
        roll_preference="open_interest",
        calendar_roll_business_days=5,
    )

    assert selection.mode == "auto_roll"
    assert selection.roll_source == "calendar_fallback"
    assert selection.windows
    assert all(window.instrument_id.startswith("MGC") for window in selection.windows)


def test_venue_config_uses_native_latency_and_cost_models() -> None:
    settings = load_settings("configs/settings.toml")
    venue = build_venue_config(settings, starting_balance="50000 USD")

    assert venue.latency_model is not None
    assert venue.latency_model.config["base_latency_nanos"] == BAR_INTERVAL_NANOS
    assert venue.fill_model is not None
    assert venue.fill_model.fill_model_path.endswith("OneTickSlippageFillModel")
    assert venue.fee_model is not None
    assert venue.fee_model.config["commission"] == "0.50 USD"
