---
phase: 01-catalog-foundation
plan: 02
subsystem: data
tags: [databento, nautilus-trader, parquet, catalog, futures]
requires:
  - phase: 01-01
    provides: CLI and typed TOML settings loading
provides:
  - Schema-aware Databento file discovery
  - Definition-first Nautilus catalog ingestion
  - MGC futures contract filtering that excludes spreads
affects: [phase-3-strategy, phase-2-backtest, catalog-validation]
tech-stack:
  added: [nautilus_trader DatabentoDataLoader, ParquetDataCatalog]
  patterns: [definitions-first ingestion, metadata-informed discovery]
key-files:
  created: [src/mgc_bt/ingest/discovery.py, src/mgc_bt/ingest/catalog.py, src/mgc_bt/ingest/service.py, tests/test_databento_discovery.py]
  modified: [src/mgc_bt/cli.py]
key-decisions:
  - "Discovery trusts metadata and file suffixes instead of folder names alone because the local bar folder is named `ohcl-1m` while the schema is `ohlcv-1m`."
  - "Phase 1 filters to outright `FuturesContract` MGC instruments and excludes spreads even though the Databento parent-symbol data includes both."
  - "Definitions are decoded with legacy Cython objects in Nautilus 1.225.0 because PyO3 FuturesContract objects do not serialize to the Parquet catalog on this installed version."
patterns-established:
  - "Databento definitions load before any bars or trades are written."
  - "Daily-split and range-split DBN files are both handled by the same discovery contract."
requirements-completed: [DATA-01, DATA-02, DATA-03]
duration: 1h 25min
completed: 2026-04-08
---

# Phase 1: Catalog Foundation Summary

**Metadata-driven Databento discovery with filtered MGC futures ingestion into a Nautilus Parquet catalog**

## Performance

- **Duration:** 1h 25min
- **Started:** 2026-04-08T07:55:00-05:00
- **Completed:** 2026-04-08T09:20:00-05:00
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Implemented schema-aware discovery for definitions, bars, trades, and MBP-1 DBN files.
- Built the definition-first ingest service around `DatabentoDataLoader` and `ParquetDataCatalog`.
- Successfully loaded the real local MGC dataset into `C:\dev\nautilustrader\catalog`.

## Task Commits

Implementation landed in aggregate phase commits for this local execution run:

1. **Task 1-3: Build discovery, catalog helpers, and CLI ingestion path** - `012ea0f` (feat)
2. **Cleanup: ignore editable install metadata** - `7ce95f6` (chore)

**Plan metadata:** Covered by the phase planning docs already committed before execution.

## Files Created/Modified
- `src/mgc_bt/ingest/discovery.py` - Databento file discovery and folder metadata parsing.
- `src/mgc_bt/ingest/catalog.py` - Catalog helpers, instrument filtering, and timestamp sorting.
- `src/mgc_bt/ingest/service.py` - Ordered ingest orchestration and catalog rebuild behavior.
- `src/mgc_bt/cli.py` - Real ingest command dispatch.
- `tests/test_databento_discovery.py` - Discovery contract coverage.

## Decisions Made
- Used metadata plus filename suffixes as the discovery source of truth because the bar folder name is not canonical.
- Filtered definitions to outright MGC futures contracts only, leaving spreads out of the catalog for v1.
- Sorted all catalog writes by `ts_init` because Nautilus rejects non-monotonic batches.

## Deviations from Plan

### Auto-fixed Issues

**1. [Runtime compatibility] Databento definition decoding used legacy Cython objects**
- **Found during:** Live ingest verification
- **Issue:** `as_legacy_cython=False` produced PyO3 `FuturesContract` objects that Nautilus 1.225.0 would not serialize into `ParquetDataCatalog`
- **Fix:** Kept market-data decoding on PyO3 but switched definition-file decoding to `as_legacy_cython=True`
- **Files modified:** `src/mgc_bt/ingest/service.py`
- **Verification:** Reproduced serializer failure in isolation, then reran the full ingest successfully
- **Committed in:** `012ea0f`

---

**Total deviations:** 1 auto-fixed runtime compatibility issue
**Impact on plan:** Necessary for compatibility with the installed Nautilus version. No scope creep.

## Issues Encountered

- The raw Databento parent-symbol files include many spreads as well as outright contracts. The service now filters to MGC futures contracts only.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The catalog is populated and queryable for 41 MGC instruments.
- Phase 2 can build on `catalog/` without needing to solve Databento discovery again.

---
*Phase: 01-catalog-foundation*
*Completed: 2026-04-08*
