from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


class ConfigError(ValueError):
    """Raised when the project configuration is invalid."""


DEFAULT_WALK_FORWARD = {
    "train_months": 12,
    "validation_months": 3,
    "test_months": 3,
    "step_months": 3,
    "validation_top_n": 5,
    "min_training_bars": 50_000,
    "min_test_trades": 10,
    "final_test_months": 6,
    "runtime_warning_minutes": 30,
}

DEFAULT_MONTE_CARLO = {
    "simulations": 1_000,
    "confidence_level": 0.95,
    "percentile_points": (5, 25, 50, 75, 95),
    "random_seed_offset": 10_000,
}


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
class RiskConfig:
    native_max_order_submit_rate: str
    native_max_order_modify_rate: str
    native_max_notional_per_order: dict[str, int]
    max_loss_per_trade_dollars: float
    max_daily_trades: int
    max_daily_loss_dollars: float
    max_consecutive_losses: int
    max_drawdown_pct: float


@dataclass(frozen=True)
class OptimizationConfig:
    study_name: str
    direction: str
    results_subdir: str
    storage_filename: str
    seed: int
    max_trials: int
    max_runtime_seconds: int
    early_stop_window: int
    early_stop_min_improvement: float
    in_sample_start: str
    in_sample_end: str
    holdout_start: str
    holdout_end: str


@dataclass(frozen=True)
class WalkForwardConfig:
    train_months: int
    validation_months: int
    test_months: int
    step_months: int
    validation_top_n: int
    min_training_bars: int
    min_test_trades: int
    final_test_months: int
    runtime_warning_minutes: int


@dataclass(frozen=True)
class MonteCarloConfig:
    simulations: int
    confidence_level: float
    percentile_points: tuple[int, ...]
    random_seed_offset: int


@dataclass(frozen=True)
class Settings:
    config_path: Path
    paths: PathsConfig
    ingestion: IngestionConfig
    backtest: BacktestConfig
    risk: RiskConfig
    optimization: OptimizationConfig
    walk_forward: WalkForwardConfig
    monte_carlo: MonteCarloConfig


def load_settings(config_path: str | Path) -> Settings:
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Config file is not valid TOML: {exc}") from exc

    for section in ("paths", "ingestion", "backtest", "risk", "optimization"):
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
    risk = raw["risk"]
    optimization = raw["optimization"]
    walk_forward = dict(DEFAULT_WALK_FORWARD)
    walk_forward.update(raw.get("walk_forward", {}))
    monte_carlo = dict(DEFAULT_MONTE_CARLO)
    monte_carlo.update(raw.get("monte_carlo", {}))

    settings = Settings(
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
        risk=RiskConfig(
            native_max_order_submit_rate=str(_require(risk, "native_max_order_submit_rate", "risk")),
            native_max_order_modify_rate=str(_require(risk, "native_max_order_modify_rate", "risk")),
            native_max_notional_per_order={
                str(key): int(value) for key, value in dict(_require(risk, "native_max_notional_per_order", "risk")).items()
            },
            max_loss_per_trade_dollars=float(_require(risk, "max_loss_per_trade_dollars", "risk")),
            max_daily_trades=int(_require(risk, "max_daily_trades", "risk")),
            max_daily_loss_dollars=float(_require(risk, "max_daily_loss_dollars", "risk")),
            max_consecutive_losses=int(_require(risk, "max_consecutive_losses", "risk")),
            max_drawdown_pct=float(_require(risk, "max_drawdown_pct", "risk")),
        ),
        optimization=OptimizationConfig(
            study_name=str(_require(optimization, "study_name", "optimization")),
            direction=str(_require(optimization, "direction", "optimization")),
            results_subdir=str(optimization.get("results_subdir", "optimization")),
            storage_filename=str(optimization.get("storage_filename", "optuna_storage.db")),
            seed=int(optimization.get("seed", 42)),
            max_trials=int(optimization.get("max_trials", 200)),
            max_runtime_seconds=int(optimization.get("max_runtime_seconds", 14_400)),
            early_stop_window=int(optimization.get("early_stop_window", 50)),
            early_stop_min_improvement=float(optimization.get("early_stop_min_improvement", 0.05)),
            in_sample_start=str(optimization.get("in_sample_start", "2021-03-08T00:00:00+00:00")),
            in_sample_end=str(optimization.get("in_sample_end", "2025-03-08T00:00:00+00:00")),
            holdout_start=str(optimization.get("holdout_start", "2025-03-08T00:00:00+00:00")),
            holdout_end=str(optimization.get("holdout_end", "2026-03-08T00:00:00+00:00")),
        ),
        walk_forward=WalkForwardConfig(
            train_months=int(_require(walk_forward, "train_months", "walk_forward")),
            validation_months=int(_require(walk_forward, "validation_months", "walk_forward")),
            test_months=int(_require(walk_forward, "test_months", "walk_forward")),
            step_months=int(_require(walk_forward, "step_months", "walk_forward")),
            validation_top_n=int(_require(walk_forward, "validation_top_n", "walk_forward")),
            min_training_bars=int(_require(walk_forward, "min_training_bars", "walk_forward")),
            min_test_trades=int(_require(walk_forward, "min_test_trades", "walk_forward")),
            final_test_months=int(_require(walk_forward, "final_test_months", "walk_forward")),
            runtime_warning_minutes=int(_require(walk_forward, "runtime_warning_minutes", "walk_forward")),
        ),
        monte_carlo=MonteCarloConfig(
            simulations=int(_require(monte_carlo, "simulations", "monte_carlo")),
            confidence_level=float(_require(monte_carlo, "confidence_level", "monte_carlo")),
            percentile_points=tuple(int(value) for value in list(_require(monte_carlo, "percentile_points", "monte_carlo"))),
            random_seed_offset=int(_require(monte_carlo, "random_seed_offset", "monte_carlo")),
        ),
    )
    _validate_optimization_settings(settings)
    _validate_phase_six_settings(settings)
    return settings


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


def _validate_optimization_settings(settings: Settings) -> None:
    if settings.optimization.seed < 0:
        raise ConfigError("Optimization seed must be non-negative.")
    if settings.optimization.max_trials <= 0:
        raise ConfigError("Optimization max_trials must be greater than zero.")
    if settings.optimization.max_runtime_seconds <= 0:
        raise ConfigError("Optimization max_runtime_seconds must be greater than zero.")
    if settings.optimization.early_stop_window <= 0:
        raise ConfigError("Optimization early_stop_window must be greater than zero.")
    if settings.optimization.early_stop_min_improvement < 0:
        raise ConfigError("Optimization early_stop_min_improvement cannot be negative.")

    in_sample_start = _coerce_timestamp(settings.optimization.in_sample_start)
    in_sample_end = _coerce_timestamp(settings.optimization.in_sample_end)
    holdout_start = _coerce_timestamp(settings.optimization.holdout_start)
    holdout_end = _coerce_timestamp(settings.optimization.holdout_end)
    if in_sample_start >= in_sample_end:
        raise ConfigError("Optimization in-sample start must be earlier than in-sample end.")
    if holdout_start >= holdout_end:
        raise ConfigError("Optimization holdout start must be earlier than holdout end.")
    if in_sample_end > holdout_start:
        raise ConfigError("Optimization in-sample end must be earlier than or equal to holdout start.")


def _validate_phase_six_settings(settings: Settings) -> None:
    walk_forward_checks = {
        "train_months": settings.walk_forward.train_months,
        "validation_months": settings.walk_forward.validation_months,
        "test_months": settings.walk_forward.test_months,
        "step_months": settings.walk_forward.step_months,
        "min_training_bars": settings.walk_forward.min_training_bars,
        "min_test_trades": settings.walk_forward.min_test_trades,
        "runtime_warning_minutes": settings.walk_forward.runtime_warning_minutes,
    }
    for name, value in walk_forward_checks.items():
        if value <= 0:
            raise ConfigError(f"Walk-forward {name} must be greater than zero.")
    if settings.walk_forward.validation_top_n < 1:
        raise ConfigError("Walk-forward validation_top_n must be greater than or equal to one.")
    if settings.walk_forward.final_test_months != 6:
        raise ConfigError("Walk-forward final_test_months must stay locked to 6.")

    if settings.monte_carlo.simulations <= 0:
        raise ConfigError("Monte Carlo simulations must be greater than zero.")
    if settings.monte_carlo.random_seed_offset <= 0:
        raise ConfigError("Monte Carlo random_seed_offset must be greater than zero.")
    if not 0.0 < settings.monte_carlo.confidence_level < 1.0:
        raise ConfigError("Monte Carlo confidence_level must be between 0 and 1.")
    if not settings.monte_carlo.percentile_points:
        raise ConfigError("Monte Carlo percentile_points cannot be empty.")
    if tuple(settings.monte_carlo.percentile_points) != tuple(sorted(settings.monte_carlo.percentile_points)):
        raise ConfigError("Monte Carlo percentile_points must stay sorted in ascending order.")
    if any(value < 0 or value > 100 for value in settings.monte_carlo.percentile_points):
        raise ConfigError("Monte Carlo percentile_points must be within 0..100.")


def _coerce_timestamp(value: str):
    try:
        from pandas import Timestamp
    except Exception as exc:  # pragma: no cover - pandas is a required dependency transitively
        raise ConfigError(f"Could not validate optimization timestamps: {exc}") from exc
    return Timestamp(value, tz="UTC")
