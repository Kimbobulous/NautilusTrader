# Phase 10 Discussion Log

Date: 2026-04-09
Phase: 10
Title: Full 5-Year Optimization Run

## Summary

Phase 10 is a research execution gate, not a platform-building phase. The existing optimization, walk-forward, Monte Carlo, stability, tearsheet, and reporting infrastructure should be used as-is unless a real bug is discovered.

The phase must stop after the first full research run and wait for explicit human approval before any Phase 11 refinement work begins.

## Decisions

### 1. Final test set policy

Decision: `B`

- Do not run `--final-test` in Phase 10.
- Keep the final 6-month protected test set completely hidden.
- Phase 10 runs with:
  - `--walk-forward`
  - `--monte-carlo`
  - `--stability`

Rationale:
- the final test should only be used once
- using it now would contaminate the untouched evaluation set

### 2. Runtime and resume policy

Decision: `C`

- Run a bounded smoke configuration first.
- If smoke passes, launch the full 5-year optimization with persistent SQLite storage and resume support.

Locked smoke contract:
- training window: `6` months
- validation window: `1` month
- test window: `1` month
- max trials: `20`
- save config to `configs/smoke_optimization.toml`

Rationale:
- catch pipeline issues before spending hours on the full run

### 3. Anomaly handling

Decision: `C`

Hard-stop integrity failures:
- fewer than `3` conclusive walk-forward windows
- Monte Carlo analysis fails
- `ranked_results.csv` is empty

Warn-and-report findings:
- negative aggregated walk-forward Sharpe
- Monte Carlo p-value does not support real edge
- most windows inconclusive

Rationale:
- weak strategy performance is still useful research
- broken outputs are not

### 4. Top-3 parameter reporting

Decision: `C`

Report both:
- top `3` raw parameter sets from `ranked_results.csv`
- best walk-forward-selected parameter path

Rationale:
- divergence between them may reveal overfitting

### 5. Output package

Decision: `C`

Produce both:
- concise gate report in chat
- saved markdown findings summary in the phase directory

Requested saved findings file:
- `10-RESEARCH-FINDINGS.md`

Requested chat report content:
- aggregated walk-forward Sharpe
- Monte Carlo p-value
- top `3` parameter sets
- warnings/anomalies

Additional saved-summary content:
- chart descriptions
- interpretation
- artifact links/paths

## Additional Locked Context

Before any run:
- verify `configs/settings.toml` date windows
- verify catalog coverage for those windows

Expected date windows:
- in-sample: `2021-03-09` to `2024-12-31`
- holdout: `2025-01-01` to `2025-12-31`
- protected final test: last `6` months of available data

After the full run completes:
- open `tearsheet.html` in a browser
- include a brief description of the equity curve and walk-forward chart in the gate report

## Responsibility Split

### Human

The human will run:
- `uv run python -m mgc_bt health`
- smoke optimization command
- full optimization command
- any `--resume` commands

### Codex

Codex will:
- verify config correctness
- confirm catalog data coverage
- create `configs/smoke_optimization.toml`
- interpret pasted results
- write `10-RESEARCH-FINDINGS.md`
- produce the concise gate report
- stop and wait for explicit approval before Phase 11

## Planning Implications

Phase 10 planning should therefore focus on:
- preflight validation of config and catalog readiness
- creation of the reusable smoke optimization config
- exact operator command contract for smoke and full runs
- post-run interpretation and stop-gate reporting

It should not include:
- strategy logic changes
- infrastructure refactors
- early use of the protected final test set
