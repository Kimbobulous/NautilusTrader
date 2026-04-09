# Phase 5: Validation and Hardening - Research

**Date:** 2026-04-09
**Phase:** 05 - Validation and Hardening
**Goal:** Make the local workflow reliable through validation, regression protection, and safer operator feedback without expanding scope.

## Research Question

What do we need to know to plan Phase 5 so it hardens the existing local workflow realistically, using the current codebase rather than generic “add validation” guidance?

## Key Findings

### 1. The CLI is still thin enough that a shared preflight layer will fit cleanly

- `src/mgc_bt/cli.py` currently routes directly into `run_ingest`, `run_backtest`, and `run_optimization`.
- That means Phase 5 can introduce a shared preflight surface without rewriting the command architecture.
- The same pattern also makes `health` straightforward: it can call the same readiness functions without duplicating command logic.

### 2. Structural validation exists in pieces, but not as an operator-facing readiness contract

- `src/mgc_bt/ingest/validation.py` already validates discovered files and ingest results.
- `src/mgc_bt/config.py` already validates some optimization structure such as non-overlapping in-sample and holdout windows.
- `src/mgc_bt/backtest/runner.py` and `src/mgc_bt/optimization/study.py` still mostly assume their prerequisites are satisfied instead of running a formal preflight pass first.
- Phase 5 therefore does not need a new validation philosophy so much as a unified, user-facing validation layer.

### 3. Current result persistence is functional but not yet defensive

- `src/mgc_bt/backtest/artifacts.py` creates timestamped run directories and force-refreshes `latest/` by deleting it unconditionally.
- `src/mgc_bt/optimization/results.py` does the same for optimization `latest/` and assumes a timestamp collision never happens.
- There is currently no manifest describing what files were written.
- This is exactly the sort of repeated local-use fragility Phase 5 should harden.

### 4. Resume behavior exists, but resume validation is weaker than the user wants

- `src/mgc_bt/optimization/study.py` uses `optuna.create_study(..., load_if_exists=resume)`.
- That supports resumable storage, but it does not itself guarantee the named study exists before a `--resume` run.
- Phase 5 should add an explicit readiness check so `--resume` failures are explained in user terms rather than delegated entirely to Optuna behavior.

### 5. The most valuable tests are around failure surfaces, not deeper market simulation

- The test suite already covers many success-path behaviors:
  - config loading
  - CLI wiring
  - ingest discovery
  - runner behavior
  - optimization outputs
- The most meaningful hardening additions are therefore:
  - malformed config messaging
  - missing catalog messaging
  - resume target validation
  - output integrity checks
  - manifest presence
  - ranked CSV column and non-empty guarantees

### 6. `health` is best implemented as an aggregator, not a separate workflow

- Because the CLI already has clean command boundaries and shared settings loading, `health` can be a read-only aggregation layer over command preflight functions.
- That keeps readiness logic canonical and avoids the common mistake of a health command that “passes” even when the real commands would fail.

### 7. The catalog-backed workflow still constrains what hardening can assume

- The system remains catalog-backed through Nautilus and should stay that way.
- Any Phase 5 checks that inspect catalog readiness must preserve the Phase 1/2/3/4 operational note:
  - definitions were ingested with legacy Cython decoding
  - bars/trades were ingested with `as_legacy_cython=False`
- Hardening should validate catalog presence and expected contents, not redesign ingestion or the runner.

### 8. Operator docs should focus on exact commands and recovery paths

- The repo does not yet have a dedicated root `USAGE.md`.
- Given the existing CLI style, the highest-value documentation is practical:
  - exact commands
  - expected output paths
  - resume instructions
  - rerunning best params
  - common failures and fixes
- This is more useful than broad architectural prose for the Phase 5 audience.

## Planning Implications

### Recommended plan sequence

1. Add targeted regression tests and fixtures around the most fragile success and failure paths.
2. Implement shared preflight validation plus the `health` command and actionable CLI failure messages.
3. Harden result-directory behavior, add manifests and `--force`, then finish with operator docs and help text.

### Recommended code boundaries

- `src/mgc_bt/validation/` or equivalent shared readiness module:
  - preflight checks for ingest, backtest, optimize
  - health-report aggregation
- Existing persistence modules:
  - extend `src/mgc_bt/backtest/artifacts.py`
  - extend `src/mgc_bt/optimization/results.py`
- `src/mgc_bt/cli.py`
  - add `health`
  - add `--force`
  - improve help descriptions

## Risks and Mitigations

### Risk: hardening drifts into feature expansion

- Mitigation: keep all changes tied to readiness, safer execution, clearer errors, or output integrity.

### Risk: `health` duplicates logic and becomes misleading

- Mitigation: require `health` to call the exact same preflight code paths as the main commands.

### Risk: output hardening breaks existing artifact contracts

- Mitigation: add manifests and safer overwrite behavior around the existing result layouts rather than changing those layouts.

### Risk: tests become heavy or brittle

- Mitigation: keep Phase 5 focused on targeted regression tests with small fixtures and mocked boundaries where possible.

## Validation Architecture

Phase 5 can be validated with targeted pytest coverage plus a small manual CLI check:

- unit/integration tests for:
  - malformed config and user-facing config errors
  - missing catalog / bad instrument / bad date-window readiness failures
  - optimization resume validation
  - manifest generation
  - expected file presence in result bundles
  - `ranked_results.csv` columns and non-empty output
  - `health` summary output
- manual smoke:
  - `python -m mgc_bt health`
  - one bounded `backtest` and one bounded `optimize` run to confirm `--force` and `latest/` behavior

## Recommendation

Plan Phase 5 as three sequential plans:

1. Regression coverage for fragile non-strategy workflow edges
2. Shared preflight validation, actionable errors, and the `health` command
3. Safer result persistence, manifest files, `--force`, and operator documentation/help polish

## RESEARCH COMPLETE
