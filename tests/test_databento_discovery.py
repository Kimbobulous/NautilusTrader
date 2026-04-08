from __future__ import annotations

import json
from pathlib import Path

from mgc_bt.config import load_settings
from mgc_bt.ingest.discovery import discover_databento_files


def test_discovery_handles_actual_folder_names(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    definitions = data_root / "definitions"
    bars = data_root / "ohcl-1m"
    trades = data_root / "Trades"
    mbp1 = data_root / "MBP-1_03.09.2021-11.09.2023"
    for folder in (definitions, bars, trades, mbp1):
        folder.mkdir(parents=True)

    _write_metadata(definitions / "metadata.json", "definition", "day")
    _write_metadata(bars / "metadata.json", "ohlcv-1m", None)
    _write_metadata(trades / "metadata.json", "trades", "day")
    _write_metadata(mbp1 / "metadata.json", "mbp-1", "day")

    (definitions / "glbx-mdp3-20210307.definition.dbn.zst").write_text("", encoding="utf-8")
    (bars / "glbx-mdp3-20210306-20260305.ohlcv-1m.dbn.zst").write_text("", encoding="utf-8")
    (trades / "glbx-mdp3-20210309.trades.dbn.zst").write_text("", encoding="utf-8")
    (mbp1 / "glbx-mdp3-20210309.mbp-1.dbn.zst").write_text("", encoding="utf-8")

    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        (
            "[paths]\n"
            f"project_root = \"{tmp_path.as_posix()}\"\n"
            f"data_root = \"{data_root.as_posix()}\"\n"
            "catalog_root = \"catalog\"\n"
            "results_root = \"results\"\n"
            "[ingestion]\n"
            "dataset = \"GLBX.MDP3\"\n"
            "symbol = \"MGC\"\n"
            "bar_schema = \"ohlcv-1m\"\n"
            "trade_schema = \"trades\"\n"
            "definition_schema = \"definition\"\n"
            "load_definitions = true\n"
            "load_bars = true\n"
            "load_trades = true\n"
            "load_mbp1 = false\n"
            "definitions_glob = \"definitions/*.definition.dbn.zst\"\n"
            "bars_glob = \"ohcl-1m/*.ohlcv-1m.dbn.zst\"\n"
            "trades_glob = \"Trades/*.trades.dbn.zst\"\n"
            "mbp1_glob = \"MBP-1_03.09.2021-11.09.2023/*.mbp-1.dbn.zst\"\n"
            "[backtest]\n"
            "default_mode = \"auto_roll\"\n"
            "venue_name = \"GLBX\"\n"
            "oms_type = \"NETTING\"\n"
            "account_type = \"MARGIN\"\n"
            "base_currency = \"USD\"\n"
            "starting_balance = \"50000 USD\"\n"
            "default_leverage = 1.0\n"
            "trade_size = \"1\"\n"
            "results_subdir = \"backtests\"\n"
            "roll_preference = \"open_interest\"\n"
            "calendar_roll_business_days = 5\n"
            "start_date = \"\"\n"
            "end_date = \"\"\n"
            "commission_per_side = 0.5\n"
            "slippage_ticks = 1\n"
            "[optimization]\n"
            "study_name = \"study\"\n"
            "direction = \"maximize\"\n"
        ),
        encoding="utf-8",
    )

    result = discover_databento_files(load_settings(config_path))

    assert [path.name for path in result.definition_files] == ["glbx-mdp3-20210307.definition.dbn.zst"]
    assert [path.name for path in result.bar_files] == ["glbx-mdp3-20210306-20260305.ohlcv-1m.dbn.zst"]
    assert [path.name for path in result.trade_files] == ["glbx-mdp3-20210309.trades.dbn.zst"]
    assert [path.name for path in result.mbp1_files] == ["glbx-mdp3-20210309.mbp-1.dbn.zst"]
    assert {item.folder.name: item.schema for item in result.metadata}["ohcl-1m"] == "ohlcv-1m"


def _write_metadata(path: Path, schema: str, split_duration: str | None) -> None:
    path.write_text(
        json.dumps(
            {
                "query": {"schema": schema},
                "customizations": {"split_duration": split_duration},
            },
        ),
        encoding="utf-8",
    )
