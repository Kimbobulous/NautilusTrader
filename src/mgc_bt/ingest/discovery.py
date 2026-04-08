from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from mgc_bt.config import Settings


@dataclass(frozen=True)
class FolderMetadata:
    folder: Path
    schema: str | None
    split_duration: str | None
    metadata_path: Path | None
    condition_path: Path | None


@dataclass(frozen=True)
class DiscoveryResult:
    root: Path
    definition_files: list[Path]
    bar_files: list[Path]
    trade_files: list[Path]
    mbp1_files: list[Path]
    metadata: list[FolderMetadata]


def discover_databento_files(settings: Settings) -> DiscoveryResult:
    root = settings.paths.data_root
    metadata = [
        _folder_metadata(root / "definitions"),
        _folder_metadata(root / "ohcl-1m"),
        _folder_metadata(root / "Trades"),
        _folder_metadata(root / "MBP-1_03.09.2021-11.09.2023"),
    ]
    return DiscoveryResult(
        root=root,
        definition_files=_resolve_glob(root, settings.ingestion.definitions_glob),
        bar_files=_resolve_glob(root, settings.ingestion.bars_glob),
        trade_files=_resolve_glob(root, settings.ingestion.trades_glob),
        mbp1_files=_resolve_glob(root, settings.ingestion.mbp1_glob),
        metadata=metadata,
    )


def _resolve_glob(root: Path, pattern: str) -> list[Path]:
    path_pattern = Path(pattern)
    if path_pattern.is_absolute():
        parent = path_pattern.parent
        return sorted(parent.glob(path_pattern.name))
    return sorted(root.glob(pattern))


def _folder_metadata(folder: Path) -> FolderMetadata:
    metadata_path = folder / "metadata.json"
    condition_path = folder / "condition.json"
    raw = _read_json(metadata_path) if metadata_path.exists() else None
    query = raw.get("query", {}) if isinstance(raw, dict) else {}
    customizations = raw.get("customizations", {}) if isinstance(raw, dict) else {}
    return FolderMetadata(
        folder=folder,
        schema=query.get("schema"),
        split_duration=customizations.get("split_duration"),
        metadata_path=metadata_path if metadata_path.exists() else None,
        condition_path=condition_path if condition_path.exists() else None,
    )


def _read_json(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))
