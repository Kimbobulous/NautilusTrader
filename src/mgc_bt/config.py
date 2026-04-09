from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


class ConfigError(ValueError):
    """Raised when the project configuration is invalid."""


@dataclass(frozen=True)
class PathsConfig:
    project_root: Path
    data_root: Path
    catalog_root: Path
    results_root: Path


@dataclass(frozen=True)
class IngestionConfig:
    dataset: str
    symbol: str
    bar_schema: str
    trade_schema: str
    definition_schema: str
    load_definitions: bool
    load_bars: bool
    load_trades: bool
    load_mbp1: bool
    definitions_glob: str
    bars_glob: str
    trades_glob: str
    mbp1_glob: str


@dataclass(frozen=True)
class BacktestConfig:
    default_mode: str
    venue_name: str
    oms_type: str
    account_type: str
    base_currency: str
    starting_balance: str
    default_leverage: float
    trade_size: str
    results_subdir: str
    roll_preference: str
    calendar_roll_business_days: int
    start_date: str | None
    end_date: str | None
    commission_per_side: float
    slippage_ticks: int
    supertrend_atr_length: int
    supertrend_factor: float
    supertrend_training_period: int
    vwap_reset_hour_utc: int
    wavetrend_n1: int
    wavetrend_n2: int
    wavetrend_ob_level: float
    delta_imbalance_threshold: float
    absorption_volume_multiplier: float
    absorption_range_multiplier: float
    volume_lookback: int
    atr_trail_length: int
    atr_trail_multiplier: float
    min_pullback_bars: int


@dataclass(frozen=True)
class OptimizationConfig:
    study_name: str
    direction: str


@dataclass(frozen=True)
class Settings:
    config_path: Path
    paths: PathsConfig
    ingestion: IngestionConfig
    backtest: BacktestConfig
    optimization: OptimizationConfig


def load_settings(config_path: str | Path) -> Settings:
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    for section in ("paths", "ingestion", "backtest", "optimization"):
        if section not in raw:
            raise ConfigError(f"Missing required config section: [{section}]")

    project_root_default = path.parent.parent
    raw_paths = raw["paths"]
    project_root = _resolve_path(raw_paths.get("project_root", "."), project_root_default, project_root_default)
    data_root = _resolve_path(_require(raw_paths, "data_root", "paths"), project_root, path.parent)
    catalog_root = _resolve_path(_require(raw_paths, "catalog_root", "paths"), project_root, path.parent)
    results_root = _resolve_path(_require(raw_paths, "results_root", "paths"), project_root, path.parent)

    ingestion = raw["ingestion"]
    backtest = raw["backtest"]
    optimization = raw["optimization"]

    return Settings(
        config_path=path,
        paths=PathsConfig(
            project_root=project_root,
            data_root=data_root,
            catalog_root=catalog_root,
            results_root=results_root,
        ),
        ingestion=IngestionConfig(
            dataset=str(_require(ingestion, "dataset", "ingestion")),
            symbol=str(_require(ingestion, "symbol", "ingestion")),
            bar_schema=str(_require(ingestion, "bar_schema", "ingestion")),
            trade_schema=str(_require(ingestion, "trade_schema", "ingestion")),
            definition_schema=str(_require(ingestion, "definition_schema", "ingestion")),
            load_definitions=bool(_require(ingestion, "load_definitions", "ingestion")),
            load_bars=bool(_require(ingestion, "load_bars", "ingestion")),
            load_trades=bool(_require(ingestion, "load_trades", "ingestion")),
            load_mbp1=bool(ingestion.get("load_mbp1", False)),
            definitions_glob=str(_require(ingestion, "definitions_glob", "ingestion")),
            bars_glob=str(_require(ingestion, "bars_glob", "ingestion")),
            trades_glob=str(_require(ingestion, "trades_glob", "ingestion")),
            mbp1_glob=str(_require(ingestion, "mbp1_glob", "ingestion")),
        ),
        backtest=BacktestConfig(
            default_mode=str(_require(backtest, "default_mode", "backtest")),
            venue_name=str(_require(backtest, "venue_name", "backtest")),
            oms_type=str(_require(backtest, "oms_type", "backtest")),
            account_type=str(_require(backtest, "account_type", "backtest")),
            base_currency=str(_require(backtest, "base_currency", "backtest")),
            starting_balance=str(_require(backtest, "starting_balance", "backtest")),
            default_leverage=float(_require(backtest, "default_leverage", "backtest")),
            trade_size=str(_require(backtest, "trade_size", "backtest")),
            results_subdir=str(_require(backtest, "results_subdir", "backtest")),
            roll_preference=str(_require(backtest, "roll_preference", "backtest")),
            calendar_roll_business_days=int(_require(backtest, "calendar_roll_business_days", "backtest")),
            start_date=_optional_str(backtest.get("start_date")),
            end_date=_optional_str(backtest.get("end_date")),
            commission_per_side=float(_require(backtest, "commission_per_side", "backtest")),
            slippage_ticks=int(_require(backtest, "slippage_ticks", "backtest")),
            supertrend_atr_length=int(_require(backtest, "supertrend_atr_length", "backtest")),
            supertrend_factor=float(_require(backtest, "supertrend_factor", "backtest")),
            supertrend_training_period=int(_require(backtest, "supertrend_training_period", "backtest")),
            vwap_reset_hour_utc=int(_require(backtest, "vwap_reset_hour_utc", "backtest")),
            wavetrend_n1=int(_require(backtest, "wavetrend_n1", "backtest")),
            wavetrend_n2=int(_require(backtest, "wavetrend_n2", "backtest")),
            wavetrend_ob_level=float(_require(backtest, "wavetrend_ob_level", "backtest")),
            delta_imbalance_threshold=float(_require(backtest, "delta_imbalance_threshold", "backtest")),
            absorption_volume_multiplier=float(_require(backtest, "absorption_volume_multiplier", "backtest")),
            absorption_range_multiplier=float(_require(backtest, "absorption_range_multiplier", "backtest")),
            volume_lookback=int(_require(backtest, "volume_lookback", "backtest")),
            atr_trail_length=int(_require(backtest, "atr_trail_length", "backtest")),
            atr_trail_multiplier=float(_require(backtest, "atr_trail_multiplier", "backtest")),
            min_pullback_bars=int(_require(backtest, "min_pullback_bars", "backtest")),
        ),
        optimization=OptimizationConfig(
            study_name=str(_require(optimization, "study_name", "optimization")),
            direction=str(_require(optimization, "direction", "optimization")),
        ),
    )


def _resolve_path(value: str | Path, project_root: Path, relative_to: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path

    if value == ".":
        return project_root.resolve()

    candidate = (project_root / path).resolve()
    if candidate.exists() or not (relative_to / path).exists():
        return candidate

    return (relative_to / path).resolve()


def _require(section: dict, key: str, name: str) -> object:
    if key not in section:
        raise ConfigError(f"Missing required key '{key}' in [{name}]")
    return section[key]


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
