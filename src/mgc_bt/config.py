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
    commission_per_side: float
    slippage_ticks: int


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
            commission_per_side=float(_require(backtest, "commission_per_side", "backtest")),
            slippage_ticks=int(_require(backtest, "slippage_ticks", "backtest")),
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
