from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from mgc_bt.config import Settings
from mgc_bt.config import load_settings


@pytest.fixture
def sample_settings(tmp_path: Path) -> Settings:
    settings = load_settings("configs/settings.toml")
    return replace(
        settings,
        paths=replace(
            settings.paths,
            project_root=tmp_path,
            data_root=tmp_path / "data",
            catalog_root=tmp_path / "catalog",
            results_root=tmp_path / "results",
        ),
    )


def write_settings_file(path: Path, content: str) -> Path:
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path
