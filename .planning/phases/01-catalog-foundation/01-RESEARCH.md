# Phase 1: Catalog Foundation - Research

**Date:** 2026-04-08
**Status:** Complete
**Scope:** Planning research for Phase 1 only

## Summary

Phase 1 should stay deliberately sequential:

1. Scaffold a real Python package and CLI first.
2. Implement Databento discovery plus Nautilus catalog ingestion second.
3. Add validation/reporting last so the ingest command becomes trustworthy instead of merely functional.

The local Nautilus docs strongly support a catalog-first workflow for performance and repeatability. The main implementation trap is not Python packaging, but the exact Databento ingestion contract on Windows: definitions must be loaded first, DBN decoding should use `as_legacy_cython=False` for catalog writes, and path handling should be normalized through `pathlib.Path` instead of raw backslash strings.

## Relevant Inputs

### Locked Phase Decisions

- Use a conventional project layout with `src/`, `configs/`, `results/`, `catalog/`, and `tests/`
- Use package name `mgc_bt`
- Use `configs/settings.toml` with `paths`, `ingestion`, `backtest`, and `optimization` sections
- Support hybrid discovery: scan by default, allow explicit overrides
- Support the exact local Databento layout under `C:/dev/mgc-data`
- Treat missing definitions and unusable catalog state as hard failures
- Treat sparse sessions and expected futures irregularities as warnings

### Canonical Nautilus References Reviewed

- `nt_docs/integrations/databento.md`
- `nt_docs/how_to/data_catalog_databento.py`
- `nt_docs/api_reference/adapters/databento.md`
- `nt_docs/api_reference/persistence.md`

## Findings

### 1. Databento-to-catalog contract is strict

The Nautilus Databento integration docs are unambiguous about the catalog workflow:

- `DatabentoDataLoader` should be used to decode DBN files
- `ParquetDataCatalog` is the right storage target for repeatable backtests
- `DEFINITION` files must be written before bars, trades, or other market data
- `as_legacy_cython=False` is the recommended decode mode for catalog-oriented writes

This means Phase 1 should not attempt a "load everything in any order" abstraction. The ingestion service should have an explicit ordered pipeline:

1. discover definition files
2. decode definitions
3. write instruments to catalog
4. resolve target instrument ids
5. decode bars and trades
6. write market data
7. validate catalog contents

### 2. The real local data layout is workable but asymmetric

The inspected local folder structure is:

- `C:/dev/mgc-data/definitions/`
- `C:/dev/mgc-data/ohcl-1m/`
- `C:/dev/mgc-data/Trades/`
- `C:/dev/mgc-data/MBP-1_03.09.2021-11.09.2023/`

Observed file patterns:

- definitions: many daily `*.definition.dbn.zst` files
- bars: one large `glbx-mdp3-20210306-20260305.ohlcv-1m.dbn.zst`
- trades: many daily `*.trades.dbn.zst` files
- mbp-1: many daily `*.mbp-1.dbn.zst` files

Implication for planning:

- Discovery logic should be schema-aware, not folder-name-only
- Phase 1 should ingest definitions, 1-minute bars, and trades only
- MBP-1 should be discoverable but ignored by default in v1 ingestion because it is not required by Phase 1 requirements

### 2a. Metadata confirms the actual naming contract

Reading one `metadata.json` file from each folder confirmed these patterns:

- `definitions/metadata.json` uses schema `definition` and daily splitting
- `ohcl-1m/metadata.json` uses schema `ohlcv-1m` and no duration splitting, which explains the single large bar file
- `Trades/metadata.json` uses schema `trades` and daily splitting
- `MBP-1_03.09.2021-11.09.2023/metadata.json` uses schema `mbp-1` and daily splitting

Two execution-relevant details fall out of that:

- The folder is actually named `ohcl-1m`, but the file schema and DBN filename use `ohlcv-1m`; discovery must tolerate the folder typo and trust schema/file suffixes instead of assuming the directory name is canonical.
- Daily-split folders should expect many `glbx-mdp3-YYYYMMDD.<schema>.dbn.zst` files, while the bar folder currently uses a single date-range filename `glbx-mdp3-YYYYMMDD-YYYYMMDD.ohlcv-1m.dbn.zst`.

### 3. Local metadata already tells us about data-quality edge cases

The `condition.json` and metadata files under the raw Databento folders show:

- bars were requested with dataset `GLBX.MDP3`, schema `ohlcv-1m`, symbol `MGC.FUT`, and parent symbology
- trades and definitions have long daily availability histories
- some dates are marked `degraded` rather than `available`

That matters for validation design. A degraded day should become a warning in the ingest report, not a hard failure, because the user explicitly wants structural strictness but quality warnings for market-data irregularities.

### 4. Windows path handling should be normalized at the config boundary

Because this project is local-first on Windows, the lowest-friction approach is:

- parse TOML once
- convert configured paths immediately to `Path` objects
- resolve them against the project root when relative
- store normalized `Path` values inside a typed config object

This keeps downstream ingestion code free from string-concatenation path bugs.

### 5. CLI design should be stable from day one

The project wants a long-lived command surface:

- `python -m mgc_bt ingest`
- `python -m mgc_bt backtest`
- `python -m mgc_bt optimize`

Phase 1 should therefore build the shared command parser and config loader now, even if only `ingest` is implemented. `backtest` and `optimize` can exist as stub subcommands that fail clearly with "not implemented yet" behavior or be registered later in Phase 2/4. The roadmap wording favors building the CLI shell in Phase 1, so the parser should reserve those commands now.

## Recommended Plan Shape

### Plan 01-01: Scaffold package, config model, and CLI shell

This plan should create:

- `pyproject.toml`
- `configs/settings.toml`
- `src/mgc_bt/`
- shared config/path loading
- top-level CLI dispatcher
- minimal pytest scaffolding

This gives later plans stable import paths and command entry points.

### Plan 01-02: Implement discovery and ordered catalog ingestion

This plan should build:

- schema-aware Databento file discovery
- explicit definition-first ingest service
- catalog writer utilities
- instrument resolution/filtering for MGC data

This is the highest-risk plan and should stay isolated from reporting logic.

### Plan 01-03: Add validation and ingestion reporting

This plan should add:

- structural validation gates
- quality warning collection
- counts/date-range reporting
- tests covering missing inputs, degraded dates, and empty catalog scenarios

Keeping this separate prevents Phase 1 from hiding ingestion correctness inside logging code.

## Design Recommendations

### Config shape

Use one TOML file with stable sections:

- `[paths]`
- `[ingestion]`
- `[backtest]`
- `[optimization]`

Recommended path keys:

- `project_root`
- `data_root`
- `catalog_root`
- `results_root`

Recommended ingestion keys:

- `dataset`
- `symbol`
- `bar_schema`
- `trade_schema`
- `load_bars`
- `load_trades`
- `load_mbp1`
- `definitions_glob`
- `bars_glob`
- `trades_glob`
- `mbp1_glob`

The explicit glob keys provide the "override" half of the hybrid discovery contract without forcing the user to maintain a full manifest.

### Internal module boundaries

Phase 1 should probably separate concerns this way:

- `src/mgc_bt/config.py` or `src/mgc_bt/config/__init__.py` for TOML loading and typed settings
- `src/mgc_bt/cli.py` and `src/mgc_bt/__main__.py` for command dispatch
- `src/mgc_bt/ingest/discovery.py` for raw file scanning
- `src/mgc_bt/ingest/catalog.py` for Nautilus catalog helpers
- `src/mgc_bt/ingest/service.py` for orchestration
- `src/mgc_bt/ingest/validation.py` for structural and quality checks
- `src/mgc_bt/ingest/reporting.py` for result formatting

### Validation behavior

Use two classes of checks:

- Structural failures: missing definitions, zero discovered files for required schemas, failed catalog instrument lookup, zero bars/trades written when enabled, invalid configured paths
- Quality warnings: degraded raw-data dates, sparse sessions, discontinuities, missing optional overrides, ignored MBP-1 files

## Validation Architecture

Phase 1 can support Nyquist-style validation cleanly with `pytest`.

Recommended coverage:

- config parsing test verifies TOML sections and path normalization
- discovery test verifies the exact local folder names are recognized
- ingestion unit/integration tests verify definitions load before market data
- validation tests verify structural failures vs warning-only conditions

Recommended commands:

- quick: `uv run pytest tests/test_cli.py tests/test_databento_discovery.py tests/test_ingest_validation.py -q`
- full: `uv run pytest -q`

The first plan should establish test infrastructure so Plans 02 and 03 can use it immediately.

## Risks To Explicitly Plan Around

### Risk 1: Instrument identity mismatch

Databento raw symbols, parent symbols, and Nautilus `InstrumentId` are not the same thing. The ingest service should not assume a hardcoded string like `MGC.GLBX` until the loaded definitions are inspected or resolved through Nautilus objects.

### Risk 2: Partial success hidden as success

It is easy to write an ingest command that completes after writing definitions but silently skips trades or bars. Reporting must emit per-schema discovered, decoded, and written counts.

### Risk 3: Overloading Phase 1 with MBP-1 support

The data root contains MBP-1, but the Phase 1 requirement set does not require order-book ingestion. Planning should keep MBP-1 out of the required write path for now.

## Recommendation

Proceed with three sequential plans exactly as the roadmap currently states. Do not collapse ingestion and validation together. The current roadmap split matches the actual Nautilus/Databento risk profile on Windows.
