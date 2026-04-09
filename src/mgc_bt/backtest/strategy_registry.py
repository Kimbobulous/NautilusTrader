from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module


@dataclass(frozen=True)
class StrategyRegistration:
    name: str
    strategy_path: str
    config_path: str


_REGISTRY: dict[str, StrategyRegistration] = {
    "mgc_production": StrategyRegistration(
        name="mgc_production",
        strategy_path="mgc_bt.backtest.strategy:MgcProductionStrategy",
        config_path="mgc_bt.backtest.strategy:MgcStrategyConfig",
    ),
}


def registered_strategies() -> dict[str, StrategyRegistration]:
    return dict(_REGISTRY)


def register_strategy(name: str, strategy_path: str, config_path: str) -> None:
    _REGISTRY[name] = StrategyRegistration(name=name, strategy_path=strategy_path, config_path=config_path)


def resolve_strategy_registration(*, strategy: str | None, strategy_class: str | None) -> StrategyRegistration:
    strategy_class_text = _optional_text(strategy_class)
    if strategy_class_text:
        return StrategyRegistration(
            name=_strategy_name_from_path(strategy_class_text),
            strategy_path=strategy_class_text,
            config_path=_derive_config_path(strategy_class_text),
        )

    strategy_name = _optional_text(strategy) or "mgc_production"
    try:
        return _REGISTRY[strategy_name]
    except KeyError as exc:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown strategy '{strategy_name}'. Registered strategies: {available}.") from exc


def _derive_config_path(strategy_path: str) -> str:
    module_name, class_name = _split_import_path(strategy_path)
    if class_name.endswith("Strategy"):
        config_class_name = f"{class_name[:-8]}Config"
    else:
        config_class_name = f"{class_name}Config"
    import_module(module_name)
    module = import_module(module_name)
    if not hasattr(module, config_class_name):
        raise ValueError(
            f"Strategy override '{strategy_path}' requires a matching config class '{module_name}:{config_class_name}'.",
        )
    return f"{module_name}:{config_class_name}"


def _strategy_name_from_path(strategy_path: str) -> str:
    _, class_name = _split_import_path(strategy_path)
    return class_name


def _split_import_path(value: str) -> tuple[str, str]:
    if ":" not in value:
        raise ValueError("Strategy import paths must use the 'package.module:ClassName' format.")
    module_name, class_name = value.split(":", 1)
    if not module_name or not class_name:
        raise ValueError("Strategy import paths must use the 'package.module:ClassName' format.")
    return module_name, class_name


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
