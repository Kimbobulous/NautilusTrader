# Phase 10 Research: Full 5-Year Optimization Run

## Goal

Determine how to use the shipped optimization pipeline for the first real 5-year MGC validation pass without adding new infrastructure or exposing the protected final test set too early.

## Codebase Findings

### 1. The required optimization features already exist

The current CLI and optimization stack already support the full Phase 10 research bundle:

- `uv run python -m mgc_bt optimize --walk-forward`
- automatic walk-forward artifacts under `walk_forward/`
- automatic Monte Carlo analysis for walk-forward runs unless skipped
- automatic stability analysis for walk-forward runs unless skipped
- automatic `tearsheet.html` generation from persisted artifacts
- persistent Optuna SQLite storage through the configured optimization storage path
- `--resume` for interrupted or resumed studies

Relevant code:
- `src/mgc_bt/cli.py`
- `src/mgc_bt/optimization/study.py`
- `src/mgc_bt/optimization/walk_forward.py`
- `src/mgc_bt/optimization/results.py`
- `src/mgc_bt/reporting/loaders.py`
- `src/mgc_bt/reporting/tearsheet.py`

### 2. Current settings do not match the locked Phase 10 research window

`configs/settings.toml` is currently configured for:
- in-sample: `2021-03-08` -> `2025-03-08`
- holdout: `2025-03-08` -> `2026-03-08`

Phase 10 requires:
- in-sample: `2021-03-09` -> `2024-12-31`
- holdout: `2025-01-01` -> `2025-12-31`

This mismatch must be corrected before any smoke or full optimization run.

### 3. The protected final test is derived from `holdout_end`, not a separate config section

The walk-forward implementation excludes the last `6` months before `holdout_end` from the rolling schedule:

- `build_walk_forward_windows(...)` uses `holdout_end - final_test_months`
- `_run_final_test(...)` evaluates the last `6` months only when `--final-test` is requested

Implication:
- Phase 10 can preserve the protected final test simply by omitting `--final-test`
- the settings still need the correct `holdout_end` so the hidden window remains meaningful

Relevant code:
- `src/mgc_bt/optimization/walk_forward.py`
- `src/mgc_bt/optimization/study.py`

### 4. The smoke run can use the same typed TOML config path as production

The CLI already supports a global `--config` flag:

- `uv run python -m mgc_bt --config configs/smoke_optimization.toml health`
- `uv run python -m mgc_bt --config configs/smoke_optimization.toml optimize --walk-forward`

This means the smoke run should be captured as a reusable TOML file instead of ad-hoc CLI overrides.

### 5. Existing preflight coverage is good enough for Phase 10 with one operational caveat

The current preflight stack already checks:
- catalog existence
- definitions/bars/trades presence
- optimization storage writability
- future-dated holdout windows
- resume target existence

Operational caveat:
- the research phase still needs an explicit catalog/date coverage verification step tied to the locked Phase 10 windows, because the phase contract depends on known 2021-2025 coverage rather than a generic "catalog exists" check

Relevant code:
- `src/mgc_bt/validation/preflight.py`
- `src/mgc_bt/validation/health.py`

### 6. Artifact contract for Phase 10 findings is stable and file-based

The final stop-gate report can be built from persisted artifacts only:

- `ranked_results.csv`
- `walk_forward/aggregated_summary.json`
- `walk_forward/window_results.csv`
- `walk_forward/params_over_time.csv`
- `monte_carlo/monte_carlo_summary.json`
- `stability/stability_summary.json`
- `tearsheet.html`
- `optimization_summary.json`

This aligns cleanly with the human/Codex split:
- human runs commands
- Codex interprets saved outputs afterward

## Planning Implications

Phase 10 should be split into two plans:

1. **Preparation plan**
- align `configs/settings.toml` to the locked research windows
- create `configs/smoke_optimization.toml`
- lock smoke settings through the typed TOML loader and tests
- define the exact human-run command contract

2. **Human-in-the-loop findings plan**
- validate smoke-run artifacts before the full run starts
- validate full-run artifacts after the human finishes the long job
- hard-stop on integrity failures
- save `10-RESEARCH-FINDINGS.md`
- produce a concise stop-gate report and wait for explicit approval

## Recommended Smoke Defaults

Locked by discussion:
- training window: `6` months
- validation window: `1` month
- test window: `1` month
- max trials: `20`

Agent discretion recommendation:
- use `step_months = 1` for the smoke config so the smoke run still exercises multiple windows while staying compact

## Validation Architecture

Phase 10 validation should combine:

- automated config-loading regression coverage
- filesystem artifact presence checks
- manual operator-run command checkpoints
- persisted artifact interpretation only, not rerunning analysis inside the report step

The saved findings file should be written after artifact validation passes and should clearly separate:
- integrity failures
- weak-performance warnings
- overfitting signals
- human-observed tearsheet notes
