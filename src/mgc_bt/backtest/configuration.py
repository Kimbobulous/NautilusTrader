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
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
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
        }
        specs.append(
            SegmentRunSpec(
                run_config=BacktestRunConfig(
                    venues=[build_venue_config(settings, starting_balance=effective_starting_balance)],
                    data=[build_bar_data_config(settings, window)],
                    engine=BacktestEngineConfig(
                        logging=LoggingConfig(log_level="ERROR"),
                        strategies=[
                            ImportableStrategyConfig(
                                strategy_path="mgc_bt.backtest.strategy_stub:Phase2HarnessStrategy",
                                config_path="mgc_bt.backtest.strategy_stub:Phase2HarnessConfig",
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
