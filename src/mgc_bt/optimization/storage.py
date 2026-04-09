from __future__ import annotations

from pathlib import Path

from mgc_bt.config import Settings


def optimization_root(settings: Settings) -> Path:
    root = settings.paths.results_root / settings.optimization.results_subdir
    root.mkdir(parents=True, exist_ok=True)
    return root


def optimization_storage_path(settings: Settings) -> Path:
    return optimization_root(settings) / settings.optimization.storage_filename


def optimization_storage_url(settings: Settings) -> str:
    return f"sqlite:///{optimization_storage_path(settings).as_posix()}"
