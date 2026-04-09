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
        "supertrend_atr_length": raw_params.get("supertrend_atr_length", settings.backtest.supertrend_atr_length),
        "supertrend_factor": raw_params.get("supertrend_factor", settings.backtest.supertrend_factor),
        "supertrend_training_period": raw_params.get("supertrend_training_period", settings.backtest.supertrend_training_period),
        "vwap_reset_hour_utc": raw_params.get("vwap_reset_hour_utc", settings.backtest.vwap_reset_hour_utc),
        "wavetrend_n1": raw_params.get("wavetrend_n1", settings.backtest.wavetrend_n1),
        "wavetrend_n2": raw_params.get("wavetrend_n2", settings.backtest.wavetrend_n2),
        "wavetrend_ob_level": raw_params.get("wavetrend_ob_level", settings.backtest.wavetrend_ob_level),
        "delta_imbalance_threshold": raw_params.get("delta_imbalance_threshold", settings.backtest.delta_imbalance_threshold),
        "absorption_volume_multiplier": raw_params.get("absorption_volume_multiplier", settings.backtest.absorption_volume_multiplier),
        "absorption_range_multiplier": raw_params.get("absorption_range_multiplier", settings.backtest.absorption_range_multiplier),
        "volume_lookback": raw_params.get("volume_lookback", settings.backtest.volume_lookback),
        "atr_trail_length": raw_params.get("atr_trail_length", settings.backtest.atr_trail_length),
        "atr_trail_multiplier": raw_params.get("atr_trail_multiplier", settings.backtest.atr_trail_multiplier),
        "min_pullback_bars": raw_params.get("min_pullback_bars", settings.backtest.min_pullback_bars),
        "max_loss_per_trade_dollars": raw_params.get("max_loss_per_trade_dollars", settings.risk.max_loss_per_trade_dollars),
        "max_daily_trades": raw_params.get("max_daily_trades", settings.risk.max_daily_trades),
        "max_daily_loss_dollars": raw_params.get("max_daily_loss_dollars", settings.risk.max_daily_loss_dollars),
        "max_consecutive_losses": raw_params.get("max_consecutive_losses", settings.risk.max_consecutive_losses),
        "min_account_equity": raw_params.get("min_account_equity", settings.risk.min_account_equity),
        "max_drawdown_pct": raw_params.get("max_drawdown_pct", settings.risk.max_drawdown_pct),
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
            start_date=spec.window.start.isoformat(),
            end_date=spec.window.end.isoformat(),
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
