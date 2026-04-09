# Phase 4: Optimization Workflow - Research

**Date:** 2026-04-09
**Phase:** 04 - Optimization Workflow
**Goal:** Add a repeatable Optuna-based optimization workflow on top of the existing catalog-backed backtest runner, with ranked outputs, holdout evaluation, and resumable study storage.

## Research Question

What do we need to know to plan Phase 4 cleanly so optimization reuses the verified Nautilus backtest workflow instead of creating a second execution path?

## Key Findings

### 1. The existing runner contract is already the right optimization foundation

- `src/mgc_bt/backtest/runner.py` already exposes `run_backtest(settings, params) -> dict`, which matches the locked Phase 4 requirement for in-process trial execution.
- `src/mgc_bt/cli.py` is currently a thin command surface for `ingest` and `backtest`, with `optimize` still unimplemented, so Phase 4 can extend the existing CLI pattern instead of replacing it.
- `src/mgc_bt/backtest/artifacts.py` already persists machine-readable backtest bundles and refreshes `latest/`, giving Phase 4 a strong reference implementation for optimization output persistence.

### 2. Optuna is not installed yet, so Phase 4 needs a dependency/bootstrap task

- A direct import check against the current environment shows `optuna` is missing.
- That is not a planning blocker, but it is a real execution prerequisite for Phase 4.
- Because this project is locked to `uv`, execution should install Optuna through `uv pip install optuna` rather than `pip`.

### 3. Nautilus should stay the execution engine while Optuna stays outside it

- The local Nautilus docs in `nt_docs/concepts/backtesting.md` explicitly call out `BacktestEngine.reset()` as a parameter-optimization-friendly pattern.
- The current codebase uses `BacktestNode` and high-level run configs rather than directly managing a raw `BacktestEngine`.
- For v1, the safer planning choice is to keep the verified `run_backtest(...)` path as the source of truth and evaluate internal reuse or reset opportunities inside that boundary rather than rewriting the execution model around a lower-level engine API.
- This keeps the Phase 2 and Phase 3 trust chain intact and follows the project rule to build on Nautilus native infrastructure rather than reimplementing it.

### 4. The search space is already mostly encoded in project config and runner wiring

- `src/mgc_bt/config.py` already models the custom risk settings that Phase 4 must optimize:
  - `max_loss_per_trade_dollars`
  - `max_daily_trades`
  - `max_daily_loss_dollars`
  - `max_consecutive_losses`
  - `max_drawdown_pct`
- `src/mgc_bt/backtest/runner.py` already forwards both strategy parameters and custom risk parameters into the shared execution path.
- `configs/settings.toml` currently has only a minimal `[optimization]` section, so planning should explicitly expand it with:
  - study metadata
  - seed
  - max trials
  - max runtime
  - early-stopping thresholds
  - in-sample and holdout dates
  - storage path or storage-root assumptions

### 5. Phase 4 output persistence should mirror the proven backtest artifact pattern

- Phase 2 already established:
  - timestamped canonical output folders
  - machine-readable summary artifacts
  - `latest/` refresh behavior
- Phase 4 can extend that pattern under `results/optimization/` rather than inventing a second persistence style.
- The locked output contract naturally splits into:
  - aggregated optimization outputs
  - top-ranked light bundles
  - a full best-run bundle
  - failed-trial logging
  - separately labeled holdout artifacts

### 6. Honest evaluation requires Phase 4 to preserve the in-sample / holdout boundary

- The phase context locks every trial to the full in-sample auto-roll window.
- The holdout window must remain untouched during trial scoring and only be evaluated after the best in-sample parameter set is chosen.
- That means planning must treat holdout execution as a separate post-optimization export step, not as part of the objective loop.
- The output structure and CLI messaging should make that separation hard to confuse.

### 7. Resume and failure handling should be treated as core workflow features, not polish

- Long local optimization runs are likely to encounter:
  - interrupted terminals
  - machine restarts
  - occasional bad parameter combinations
- The locked SQLite storage requirement and `--resume` flag mean study persistence belongs in the first orchestration plan, not as an afterthought.
- Failed trials should be recorded as expected outcomes with parameter/error payloads instead of aborting the entire session.

### 8. The native/custom risk split from Phase 3 must carry directly into optimization

- `nt_docs/concepts/execution.md` and `nt_docs/api_reference/risk.md` support the Phase 3 rule:
  - Nautilus native `RiskEngineConfig` handles framework-supported infrastructure guardrails.
  - The custom `RiskManager` handles session-level logic Nautilus does not provide.
- Planning must preserve that split by optimizing only the custom risk parameters, not native `RiskEngineConfig` limits.

### 9. The catalog continuity rule still matters anywhere optimization touches catalog-backed assumptions

- Phase 1 and later docs verified the Databento ingestion split:
  - definitions required legacy Cython decoding
  - bars and trades used `as_legacy_cython=False`
- Phase 4 should keep this visible anywhere planning references catalog continuity or future catalog-touching helpers so later work does not accidentally erase that operational knowledge.

## Planning Implications

### Recommended module boundaries

- `src/mgc_bt/optimization/`
  - Optuna study orchestration
  - search-space definitions
  - objective scoring
  - progress callbacks
  - result ranking and persistence helpers
- `src/mgc_bt/cli.py`
  - `optimize` command argument parsing
  - resume flag exposure
  - concise live progress / final summary printing
- `src/mgc_bt/config.py`
  - expanded `[optimization]` typed config
- `tests/`
  - unit tests for objective scoring, early stopping, ranking, persistence, and CLI wiring

### Recommended plan sequence

1. Expand config plus Optuna orchestration, objective scoring, progress callbacks, and CLI entry.
2. Add ranked-result persistence, failed-trial logging, SQLite study resume, and `latest/` refresh.
3. Re-run the best in-sample configuration, execute holdout evaluation, export bundles, and surface the overfitting warning.

### Important carry-forward constraints

- Continue using Nautilus native infrastructure as the foundation.
- Keep `run_backtest(settings, params) -> dict` as the source of truth for every trial.
- Preserve the catalog decode split in any catalog-related planning notes:
  - definitions = legacy Cython
  - bars/trades = `as_legacy_cython=False`

## Risks and Mitigations

### Risk: optimization creates a second execution path that drifts from `backtest`

- Mitigation: keep Optuna trial execution centered on `run_backtest(...)` and treat CLI optimization as orchestration only.

### Risk: study persistence and output persistence diverge

- Mitigation: separate concerns clearly in planning:
  - SQLite storage for Optuna state
  - timestamped results folders for user-facing artifacts

### Risk: holdout results get confused with in-sample results

- Mitigation: export dedicated holdout files with explicit names and include holdout-specific CLI messaging.

### Risk: broad search space causes many trial failures or unusably long runs

- Mitigation: record failures without aborting, add runtime caps, and include early stopping on stalled improvement.

### Risk: optimization overfits to low-trade or high-drawdown solutions

- Mitigation: enforce the locked hard-penalty objective function and keep the holdout rerun mandatory.

## Validation Architecture

Phase 4 can be validated with fast local tests plus one bounded optimization smoke path:

- unit tests for:
  - objective scoring and penalty logic
  - search-space generation
  - early-stopping logic
  - ranking / tie-break behavior
  - failed-trial serialization
- integration tests for:
  - CLI `optimize` wiring
  - resume behavior against SQLite storage
  - best-run and holdout artifact persistence
- manual smoke:
  - one small bounded optimization run with a very low trial budget to confirm end-to-end orchestration

## Recommendation

Plan Phase 4 as three sequential plans:

1. Optuna config, search space, objective scoring, orchestration, and CLI integration
2. Ranked-result persistence, failed-trial logging, SQLite resume, and `latest/` refresh
3. Best-run export, holdout rerun, labeled holdout artifacts, and overfitting warning

## RESEARCH COMPLETE
