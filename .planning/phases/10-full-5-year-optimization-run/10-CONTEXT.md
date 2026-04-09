# Phase 10 Context: Full 5-Year Optimization Run

## Objective

Use the shipped v1.0/v1.1 platform to run the first real 5-year MGC research validation pass without changing infrastructure or strategy logic.

This phase is operational and research-focused, not implementation-heavy. The main goal is to produce a credible optimization artifact bundle and stop for human review before any strategy refinement begins.

## Locked Decisions

### Final Test Policy

- Do **not** run `--final-test` in Phase 10.
- The protected final 6-month test set remains untouched until after Phase 11 refinements are complete.
- Phase 10 uses:
  - `--walk-forward`
  - `--monte-carlo`
  - `--stability`

### Runtime and Resume Policy

- Start with a bounded smoke run before launching the full 5-year run.
- Smoke run purpose:
  - prove the entire optimization pipeline runs cleanly end to end
  - confirm all expected artifacts are produced
  - catch configuration or runtime issues before a multi-hour job
- Smoke config must be saved at:
  - `configs/smoke_optimization.toml`
- If the smoke run passes, the full run should use persistent SQLite storage and resume support.

### Anomaly Handling

Hard-stop integrity failures:
- fewer than `3` conclusive walk-forward windows
- Monte Carlo analysis fails to complete
- `ranked_results.csv` is empty

Warn-and-report findings:
- aggregated walk-forward Sharpe is negative
- Monte Carlo p-value does not support edge
- most walk-forward windows are inconclusive

Weak performance is a research finding, not a phase failure.

### Reporting Contract

Phase 10 must report both:
- top `3` parameter sets from raw `ranked_results.csv`
- the best walk-forward selected parameter path

Differences between them must be flagged as potential overfitting evidence.

### Stop-Gate Output

At phase completion, produce:
- a concise gate report in chat
- a saved markdown summary at the phase level with findings, anomalies, and artifact references

Required gate report items:
- walk-forward aggregated Sharpe
- Monte Carlo p-value
- top `3` ranked parameter sets
- best walk-forward-selected parameter path
- warnings or anomalies
- brief visual description of `tearsheet.html`, including the equity curve and walk-forward chart

## Date Window Contract

Before any run:
- verify `configs/settings.toml` is aligned to the intended full dataset windows
- verify the catalog has adequate data for those windows

Expected windows:
- in-sample: `2021-03-09` to `2024-12-31`
- holdout: `2025-01-01` to `2025-12-31`
- protected final test: last `6` months of available data, still hidden in Phase 10

## Human / Codex Split

### Human Responsibilities

The human runs all long-lived optimization commands directly in the terminal, including:
- `uv run python -m mgc_bt health`
- smoke optimization command
- full optimization command
- any `--resume` continuation commands

Reason:
- the optimization may run for hours
- the human needs direct visibility into progress and interruptions
- long terminal output should not fill Codex context

### Codex Responsibilities

Codex is responsible for:
- verifying `settings.toml` before any run
- confirming catalog coverage for the required date ranges
- creating `configs/smoke_optimization.toml`
- checking the optimization command contract and artifact expectations
- interpreting pasted smoke/full-run results
- writing the saved findings summary for the phase
- producing the short gate report after the run completes
- stopping and waiting for explicit approval before Phase 11

## Constraints Carried Forward

- No infrastructure changes unless a real bug is found.
- No strategy logic changes in Phase 10.
- Always use Nautilus native infrastructure first; check `nt_docs/` before building anything custom.
- Use `uv run python -m mgc_bt ...` for CLI commands.
- Use `uv pip install` only for packages.
- Existing `89` tests must keep passing.
- The MGC golden fixture must remain exact.
- Commit and push after the phase completes.

## Deliverable

Phase 10 is complete only when:
- the smoke run has been validated
- the full 5-year run has completed
- the required artifacts exist
- the saved findings summary is written
- the human has been given the stop-gate report and the phase pauses for explicit approval
