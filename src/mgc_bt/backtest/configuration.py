from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nautilus_trader.backtest.config import ImportableFeeModelConfig
from nautilus_trader.backtest.config import ImportableFillModelConfig
from nautilus_trader.backtest.config import ImportableLatencyModelConfig
from nautilus_trader.backtest.node import BacktestDataConfig
from nautilus_trader.backtest.node import BacktestEngineConfig
from nautilus_trader.backtest.node import BacktestRunConfig
from nautilus_trader.backtest.node import BacktestVenueConfig
from nautilus_trader.common.config import LoggingConfig
from nautilus_trader.config import ImportableStrategyConfig
from nautilus_trader.config import RiskEngineConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from mgc_bt.backtest.contracts import ContractSelection
from mgc_bt.backtest.contracts import ContractWindow
from mgc_bt.config import Settings

BAR_INTERVAL_NANOS = 60_000_000_000


@dataclass(frozen=True)
class SegmentRunSpec:
    run_config: BacktestRunConfig
    window: ContractWindow
    strategy_params: dict[str, object]


def build_segment_run_specs(
    settings: Settings,
    catalog: ParquetDataCatalog,
    selection: ContractSelection,
    params: dict[str, object],
    starting_balance: str | None = None,
) -> list[SegmentRunSpec]:
    specs: list[SegmentRunSpec] = []
    effective_starting_balance = starting_balance or settings.backtest.starting_balance
    trade_size = Decimal(str(params.get("trade_size", settings.backtest.trade_size)))

    for window in selection.windows:
        strategy_params = {
            "instrument_id": InstrumentId.from_str(window.instrument_id),
            "bar_type": BarType.from_str(window.bar_type),
            "trade_size": trade_size,
            "supertrend_atr_length": int(params.get("supertrend_atr_length", settings.backtest.supertrend_atr_length)),
            "supertrend_factor": float(params.get("supertrend_factor", settings.backtest.supertrend_factor)),
            "supertrend_training_period": int(params.get("supertrend_training_period", settings.backtest.supertrend_training_period)),
            "vwap_reset_hour_utc": int(params.get("vwap_reset_hour_utc", settings.backtest.vwap_reset_hour_utc)),
            "wavetrend_n1": int(params.get("wavetrend_n1", settings.backtest.wavetrend_n1)),
            "wavetrend_n2": int(params.get("wavetrend_n2", settings.backtest.wavetrend_n2)),
            "wavetrend_ob_level": float(params.get("wavetrend_ob_level", settings.backtest.wavetrend_ob_level)),
            "delta_imbalance_threshold": float(params.get("delta_imbalance_threshold", settings.backtest.delta_imbalance_threshold)),
            "absorption_volume_multiplier": float(params.get("absorption_volume_multiplier", settings.backtest.absorption_volume_multiplier)),
            "absorption_range_multiplier": float(params.get("absorption_range_multiplier", settings.backtest.absorption_range_multiplier)),
            "volume_lookback": int(params.get("volume_lookback", settings.backtest.volume_lookback)),
            "atr_trail_length": int(params.get("atr_trail_length", settings.backtest.atr_trail_length)),
            "atr_trail_multiplier": float(params.get("atr_trail_multiplier", settings.backtest.atr_trail_multiplier)),
            "min_pullback_bars": int(params.get("min_pullback_bars", settings.backtest.min_pullback_bars)),
            "max_loss_per_trade_dollars": float(params.get("max_loss_per_trade_dollars", settings.risk.max_loss_per_trade_dollars)),
            "max_daily_trades": int(params.get("max_daily_trades", settings.risk.max_daily_trades)),
            "max_daily_loss_dollars": float(params.get("max_daily_loss_dollars", settings.risk.max_daily_loss_dollars)),
            "max_consecutive_losses": int(params.get("max_consecutive_losses", settings.risk.max_consecutive_losses)),
            "max_drawdown_pct": float(params.get("max_drawdown_pct", settings.risk.max_drawdown_pct)),
        }
        specs.append(
            SegmentRunSpec(
                run_config=BacktestRunConfig(
                    venues=[build_venue_config(settings, starting_balance=effective_starting_balance)],
                    data=[
                        build_bar_data_config(settings, window),
                        build_trade_data_config(settings, window),
                    ],
                    engine=BacktestEngineConfig(
                        logging=LoggingConfig(log_level="ERROR"),
                        risk_engine=RiskEngineConfig(
                            bypass=False,
                            max_order_submit_rate=settings.risk.native_max_order_submit_rate,
                            max_order_modify_rate=settings.risk.native_max_order_modify_rate,
                            max_notional_per_order=settings.risk.native_max_notional_per_order,
                        ),
                        strategies=[
                            ImportableStrategyConfig(
                                # Catalog continuity reminder:
                                # definitions were ingested with legacy Cython decoding,
                                # while bars and trades were ingested with as_legacy_cython=False.
                                strategy_path="mgc_bt.backtest.strategy:MgcProductionStrategy",
                                config_path="mgc_bt.backtest.strategy:MgcStrategyConfig",
                                config=strategy_params,
                            ),
                        ],
                    ),
                    dispose_on_completion=False,
                    start=window.start.isoformat(),
                    end=window.end.isoformat(),
                ),
                window=window,
                strategy_params=strategy_params,
            ),
        )

    return specs


def build_venue_config(settings: Settings, starting_balance: str) -> BacktestVenueConfig:
    latency_model = ImportableLatencyModelConfig(
        latency_model_path="nautilus_trader.backtest.models:LatencyModel",
        config_path="nautilus_trader.backtest.config:LatencyModelConfig",
        config={"base_latency_nanos": BAR_INTERVAL_NANOS},
    )
    fill_model = ImportableFillModelConfig(
        fill_model_path="nautilus_trader.backtest.models:OneTickSlippageFillModel",
        config_path="nautilus_trader.backtest.config:FillModelConfig",
        config={},
    )
    fee_model = ImportableFeeModelConfig(
        fee_model_path="nautilus_trader.backtest.models:PerContractFeeModel",
        config_path="nautilus_trader.backtest.config:PerContractFeeModelConfig",
        config={"commission": f"{settings.backtest.commission_per_side:.2f} USD"},
    )
    return BacktestVenueConfig(
        name=settings.backtest.venue_name,
        oms_type=settings.backtest.oms_type,
        account_type=settings.backtest.account_type,
        base_currency=settings.backtest.base_currency,
        starting_balances=[starting_balance],
        default_leverage=settings.backtest.default_leverage,
        fill_model=fill_model,
        fee_model=fee_model,
        latency_model=latency_model,
        bar_execution=True,
        trade_execution=True,
    )


def build_bar_data_config(settings: Settings, window: ContractWindow) -> BacktestDataConfig:
    return BacktestDataConfig(
        catalog_path=str(settings.paths.catalog_root),
        data_cls=Bar,
        instrument_id=InstrumentId.from_str(window.instrument_id),
        start_time=window.start.isoformat(),
        end_time=window.end.isoformat(),
    )


def build_trade_data_config(settings: Settings, window: ContractWindow) -> BacktestDataConfig:
    return BacktestDataConfig(
        catalog_path=str(settings.paths.catalog_root),
        data_cls=TradeTick,
        instrument_id=InstrumentId.from_str(window.instrument_id),
        start_time=window.start.isoformat(),
        end_time=window.end.isoformat(),
    )
