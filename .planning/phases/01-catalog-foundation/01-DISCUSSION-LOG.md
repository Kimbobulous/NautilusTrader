# Phase 1: Catalog Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 1-Catalog Foundation
**Areas discussed:** Project structure, Ingestion source contract, Validation strictness, Config format, Package and CLI naming

---

## Project structure

| Option | Description | Selected |
|--------|-------------|----------|
| Conventional package layout | `src/`, `configs/`, `results/`, `catalog/`, `tests/` | ✓ |
| Flat app layout | Fewer directories, simpler initial shape | |
| Other | User-defined alternative | |

**User's choice:** Conventional package layout
**Notes:** Chosen for maintainability and clean future-phase growth.

---

## Ingestion source contract

| Option | Description | Selected |
|--------|-------------|----------|
| Config-driven directory scanning | Point at root folders and discover matching DBN files by schema/type | |
| Explicit file manifest in config | Manually list definition/bar/trade paths | |
| Hybrid | Scan by default, allow explicit overrides per dataset | ✓ |

**User's choice:** Hybrid
**Notes:** Flexibility matters because local file naming may get weird. The exact current layout under `C:/dev/mgc-data` must be supported.

---

## Validation strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Strict gate | Fail on all major problems and inconsistencies | |
| Warn-only mode | Write what we can and continue with warnings | |
| Mixed strictness | Strict for structural issues, warn for quality issues | ✓ |

**User's choice:** Mixed strictness
**Notes:** Missing definitions or failed instrument lookup should block ingestion. Sparse overnight gold sessions and similar quality quirks should warn, not fail.

---

## Config format

| Option | Description | Selected |
|--------|-------------|----------|
| TOML | `configs/settings.toml`, human-readable, native `tomllib` support | ✓ |
| YAML | Alternative config format | |
| JSON | Alternative config format | |

**User's choice:** TOML
**Notes:** Config should include `paths`, `ingestion`, `backtest`, and `optimization` sections from day one, even if some sections begin as placeholders.

---

## Package and CLI naming

| Option | Description | Selected |
|--------|-------------|----------|
| `mgc_bt` | Short package/module name for clean CLI commands | ✓ |
| Longer descriptive package name | More verbose module path | |
| Other | User-defined alternative | |

**User's choice:** `mgc_bt`
**Notes:** Preferred commands are `python -m mgc_bt ingest`, `python -m mgc_bt backtest`, and `python -m mgc_bt optimize`.

---

## the agent's Discretion

- Internal package/module split under `src/mgc_bt/`
- Exact logging/output implementation details
- Specific TOML key names and discovery heuristics

## Deferred Ideas

None.
