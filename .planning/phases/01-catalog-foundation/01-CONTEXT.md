# Phase 1: Catalog Foundation - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers the initial Python project skeleton, config system, CLI surface, and validated Databento-to-Nautilus catalog ingestion workflow for MGC. This phase does not implement the trading strategy, backtest execution outputs, or optimization logic beyond establishing the config structure those later phases will reuse.

</domain>

<decisions>
## Implementation Decisions

### Project structure
- **D-01:** Use a conventional package layout with top-level `src/`, `configs/`, `results/`, `catalog/`, and `tests/` directories.
- **D-02:** Keep the codebase maintainable for later phases by establishing the full project skeleton in Phase 1 rather than growing ad hoc script files.

### Package and CLI naming
- **D-03:** Use `mgc_bt` as the Python package name.
- **D-04:** The CLI should be runnable from the project root with the venv active using module execution such as `python -m mgc_bt ingest`, `python -m mgc_bt backtest`, and `python -m mgc_bt optimize`.

### Config format
- **D-05:** Use TOML for configuration, with the primary file at `configs/settings.toml`.
- **D-06:** The config must have clearly separated sections for `paths`, `ingestion`, `backtest`, and `optimization`.
- **D-07:** `backtest` and `optimization` sections should exist from Phase 1 even if they begin mostly as placeholders, so later phases extend the existing structure instead of introducing new config files.

### Ingestion source contract
- **D-08:** Use a hybrid ingestion contract: scan data directories by default, but allow explicit file overrides in config when discovery needs help.
- **D-09:** The ingestion workflow must support the exact existing top-level layout under `C:/dev/mgc-data`: `definitions/`, `MBP-1_03.09.2021-11.09.2023/`, `ohcl-1m/`, and `Trades/`.
- **D-10:** All configurable paths should be handled with forward-slash-safe semantics or `pathlib.Path` to avoid Windows backslash problems.

### Nautilus and Databento ingestion rules
- **D-11:** DEFINITION files must always be loaded before any market data because Nautilus catalog ingestion requires instruments before bars or trades.
- **D-12:** Decode DBN files with `as_legacy_cython=False` for catalog-oriented ingestion.
- **D-13:** The catalog path must be configurable, with `C:/dev/nautilustrader/catalog/` as the default suggestion.

### Validation posture
- **D-14:** Fail hard on structural ingestion issues such as missing definitions, failed instrument lookup, or conditions that make the catalog unusable for downstream phases.
- **D-15:** Emit warnings rather than blocking ingestion for quality issues such as sparse sessions or expected futures-market irregularities.
- **D-16:** Gold futures overnight/session gaps are not by themselves a reason to fail ingestion.

### the agent's Discretion
- Exact internal module breakdown under `src/mgc_bt/`
- Logging library choice and output formatting
- Precise TOML key names, as long as the locked section structure is respected
- The specific discovery heuristics used to match DBN files within the known top-level folders

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Nautilus Databento ingestion
- `nt_docs/integrations/databento.md` - Official Databento adapter guidance, including the requirement to load DEFINITION files before market data and catalog-oriented loader usage
- `nt_docs/how_to/data_catalog_databento.py` - Example workflow for writing Databento-decoded data into a `ParquetDataCatalog`
- `nt_docs/api_reference/adapters/databento.md` - Databento adapter API reference for loader/provider details

### Nautilus backtesting and strategy architecture
- `nt_docs/concepts/backtesting.md` - Backtest API choices and rationale for `BacktestNode` versus `BacktestEngine`
- `nt_docs/getting_started/backtest_high_level.py` - Recommended high-level catalog-backed backtesting pattern
- `nt_docs/getting_started/backtest_low_level.py` - Low-level engine reference for comparison and constraints
- `nt_docs/concepts/strategies.md` - Strategy lifecycle and event-driven handler model that later phases must follow
- `nt_docs/api_reference/backtest.md` - Backtest API surface

### Catalog and persistence
- `nt_docs/api_reference/persistence.md` - Catalog and persistence API reference

### Project planning context
- `.planning/PROJECT.md` - Project goals, constraints, and v1 scope
- `.planning/REQUIREMENTS.md` - Requirement mapping for Phase 1
- `.planning/ROADMAP.md` - Phase boundary and success criteria for Catalog Foundation
- `.planning/research/SUMMARY.md` - Research summary distilled during project initialization

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.codex/get-shit-done/` planning workflows and templates - Useful only for project process, not for application runtime code
- `nt_docs/` local Nautilus documentation set - Primary implementation reference for Databento ingestion and future backtest integration

### Established Patterns
- No existing application package is present yet, so Phase 1 sets the initial runtime code patterns
- Planning artifacts already assume a structured, config-driven project rather than notebooks or loose scripts

### Integration Points
- Local data source root: `C:/dev/mgc-data`
- Planned default catalog root: `C:/dev/nautilustrader/catalog/`
- CLI entry should be callable from the repo root with the existing `.venv`

</code_context>

<specifics>
## Specific Ideas

- The project should feel like a clean local research tool, with explicit commands and minimal ambiguity about what each step does.
- The config structure should be established early so later phases extend it instead of inventing new ad hoc settings files.
- Windows path handling needs to be deliberate from the beginning.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 01-catalog-foundation*
*Context gathered: 2026-04-08*
