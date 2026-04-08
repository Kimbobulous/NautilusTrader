from __future__ import annotations

from copy import deepcopy
from typing import Any

from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from mgc_bt.backtest.configuration import build_segment_run_specs
from mgc_bt.backtest.contracts import resolve_contract_selection
from mgc_bt.backtest.results import aggregate_execution_results
from mgc_bt.backtest.results import build_segment_execution_result
from mgc_bt.config import Settings


class BacktestError(RuntimeError):
    """Raised when the backtest runner cannot complete."""


def run_backtest(settings: Settings, params: dict[str, Any] | None = None) -> dict[str, Any]:
    raw_params = deepcopy(params or {})
    catalog = ParquetDataCatalog(str(settings.paths.catalog_root))
    selection = resolve_contract_selection(
        catalog=catalog,
        symbol_root=settings.ingestion.symbol,
        default_mode=settings.backtest.default_mode,
        requested_instrument_id=_optional_text(raw_params.get("instrument_id")),
        start=_optional_text(raw_params.get("start_date")) or settings.backtest.start_date,
        end=_optional_text(raw_params.get("end_date")) or settings.backtest.end_date,
        roll_preference=settings.backtest.roll_preference,
        calendar_roll_business_days=settings.backtest.calendar_roll_business_days,
    )

    normalized_params = {
        "instrument_id": _optional_text(raw_params.get("instrument_id")),
        "start_date": _optional_text(raw_params.get("start_date")) or settings.backtest.start_date,
        "end_date": _optional_text(raw_params.get("end_date")) or settings.backtest.end_date,
        "trade_size": raw_params.get("trade_size", settings.backtest.trade_size),
        "roll_source": selection.roll_source,
    }

    starting_balance = settings.backtest.starting_balance
    segment_results = []
    for spec in build_segment_run_specs(
        settings=settings,
        catalog=catalog,
        selection=selection,
        params=normalized_params,
        starting_balance=starting_balance,
    ):
        node = BacktestNode(configs=[spec.run_config])
        results = node.run()
        if not results:
            raise BacktestError(f"No backtest result was returned for {spec.window.instrument_id}.")

        engine = node.get_engine(spec.run_config.id)
        if engine is None:
            raise BacktestError(f"Backtest engine was not available for {spec.window.instrument_id}.")

        venue = Venue(settings.backtest.venue_name)
        fills_report = engine.trader.generate_order_fills_report()
        positions_report = engine.trader.generate_positions_report()
        account_report = engine.trader.generate_account_report(venue=venue)

        segment_result = build_segment_execution_result(
            result=results[0],
            instrument_id=spec.window.instrument_id,
            fills_report=fills_report,
            positions_report=positions_report,
            account_report=account_report,
        )
        segment_results.append(segment_result)
        starting_balance = f"{segment_result.equity_curve[-1]['equity']:.2f} {settings.backtest.base_currency}"

        node.dispose()

    return aggregate_execution_results(
        mode=selection.mode,
        symbol_root=settings.ingestion.symbol,
        parameters=normalized_params,
        segments=segment_results,
    )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
