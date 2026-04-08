from __future__ import annotations

import json
from pathlib import Path

from mgc_bt.config import load_settings
from mgc_bt.ingest.discovery import DiscoveryResult, FolderMetadata
from mgc_bt.ingest.service import DataWriteStats, IngestResult
from mgc_bt.ingest.validation import validate_discovery, validate_ingest_result


def test_validate_discovery_flags_missing_definitions(tmp_path: Path) -> None:
    settings = load_settings("configs/settings.toml")
    discovery = DiscoveryResult(
        root=tmp_path,
        definition_files=[],
        bar_files=[tmp_path / "bars.dbn.zst"],
        trade_files=[tmp_path / "trades.dbn.zst"],
        mbp1_files=[],
        metadata=[],
    )

    failures, warnings = validate_discovery(discovery, settings)

    assert "No definition DBN files were discovered." in failures
    assert warnings == []


def test_validate_discovery_emits_warning_for_degraded_days(tmp_path: Path) -> None:
    settings = load_settings("configs/settings.toml")
    condition_path = tmp_path / "condition.json"
    condition_path.write_text(
        json.dumps(
            [
                {"date": "2025-09-17", "condition": "degraded"},
                {"date": "2025-09-18", "condition": "available"},
            ],
        ),
        encoding="utf-8",
    )
    metadata = FolderMetadata(
        folder=tmp_path / "Trades",
        schema="trades",
        split_duration="day",
        metadata_path=None,
        condition_path=condition_path,
    )
    discovery = DiscoveryResult(
        root=tmp_path,
        definition_files=[tmp_path / "defs.dbn.zst"],
        bar_files=[tmp_path / "bars.dbn.zst"],
        trade_files=[tmp_path / "trades.dbn.zst"],
        mbp1_files=[tmp_path / "mbp.dbn.zst"],
        metadata=[metadata],
    )

    failures, warnings = validate_discovery(discovery, settings)

    assert failures == []
    assert any("degraded Databento day" in warning for warning in warnings)
    assert any("MBP-1 files detected" in warning for warning in warnings)


def test_validate_ingest_result_distinguishes_failures_from_warnings(tmp_path: Path) -> None:
    settings = load_settings("configs/settings.toml")
    discovery = DiscoveryResult(
        root=tmp_path,
        definition_files=[tmp_path / "defs.dbn.zst"],
        bar_files=[tmp_path / "bars.dbn.zst"],
        trade_files=[tmp_path / "trades.dbn.zst"],
        mbp1_files=[],
        metadata=[],
    )
    result = IngestResult(
        catalog_path=tmp_path / "catalog",
        discovery=discovery,
        definitions=DataWriteStats(files_discovered=1, records_written=2),
        bars=DataWriteStats(files_discovered=1, records_written=10),
        trades=DataWriteStats(files_discovered=1, records_written=20),
        instrument_ids=["MGCJ1.GLBX"],
        date_range_start="2021-03-09T00:00:00+00:00",
        date_range_end="2021-03-10T00:00:00+00:00",
        warnings=[],
    )

    failures, warnings = validate_ingest_result(result, settings)

    assert failures == []
    assert any("single date-range DBN file" in warning for warning in warnings)
