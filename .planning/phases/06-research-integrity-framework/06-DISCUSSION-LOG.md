# Phase 6: Research Integrity Framework - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 06-research-integrity-framework
**Areas discussed:** Walk-forward window design, three-way split contract, Monte Carlo methodology, parameter stability analysis, output and runtime policy

---

## Walk-forward window design

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed time windows | Use calendar-based training/validation/test windows with a rolling step size | x |
| Fixed folds | Use fold counts independent of calendar time | |
| Hybrid adaptive windows | Adjust windows dynamically based on data density | |

**User's choice:** Fixed time windows with defaults of 12 months training, 3 months validation, 3 months test, stepped forward by 3 months.
**Notes:** Windows must re-optimize on training, select on validation, then score on the test slice. Skip windows with fewer than 50,000 training bars. Flag windows with fewer than 10 out-of-sample trades as inconclusive. Aggregate OOS Sharpe as a time-weighted average.

---

## Three-way split contract

| Option | Description | Selected |
|--------|-------------|----------|
| Replace current optimize split | Make all optimization runs use train/validate/test only | |
| Extend optimize with walk-forward mode | Keep current optimize path intact and activate three-way split with a flag | x |
| Separate command | Create a dedicated walk-forward command outside optimize | |

**User's choice:** Keep existing `optimize` behavior exactly as it is, and add the three-way split under `--walk-forward`.
**Notes:** The final test set is the last 6 months of available data and should stay hidden until explicitly requested with `--final-test`, including a clear warning before execution.

---

## Monte Carlo methodology

| Option | Description | Selected |
|--------|-------------|----------|
| Trade-sequence permutation only | Shuffle realized trade order to test sequencing dependence | |
| Bootstrap resampling only | Resample trades with replacement to estimate confidence intervals | |
| Both methods | Run both permutation and bootstrap analysis | x |

**User's choice:** Implement both trade-sequence permutation and bootstrap resampling.
**Notes:** Default to 1000 simulations. Outputs must include p-value, percentile bands for Sharpe and final PnL, fan-chart-ready confidence data, and a pass/fail verdict at 95% confidence.

---

## Parameter stability analysis

| Option | Description | Selected |
|--------|-------------|----------|
| Heatmaps only | Visualize performance around the best region using important parameters | |
| Neighborhood score only | Perturb the best parameter set and score local robustness | |
| Both outputs | Generate heatmaps and a neighborhood robustness score | x |

**User's choice:** Produce both 2D heatmaps and a neighborhood robustness score.
**Notes:** Heatmaps should use the two most important parameters from Optuna built-in parameter importance (`fanova`) unless Nautilus provides a better native answer. Neighborhood robustness uses independent `+/-10%` and `+/-20%` perturbations and reports the percentage of neighbors with Sharpe above 0.5. `70%+` is the robustness interpretation threshold.

---

## Output and runtime policy

| Option | Description | Selected |
|--------|-------------|----------|
| Manual extras | Run walk-forward, Monte Carlo, and stability as separate optional tooling | |
| Automatic research mode | Attach all validation outputs to optimize with selective skip flags | x |
| Minimal output mode | Persist only summary metrics to keep runtime and storage low | |

**User's choice:** `--walk-forward` activates walk-forward automatically. Monte Carlo and stability run automatically for walk-forward research runs, while standard `optimize` keeps its current behavior unless explicitly opted into with flags like `--monte-carlo` and `--stability`.
**Notes:** Terminal output must include per-window status and cumulative OOS performance. Walk-forward outputs go under `results/optimization/YYYY-MM-DD_HHMMSS/walk_forward/`. Monte Carlo and stability outputs sit alongside the existing optimization artifacts. If runtime is estimated to exceed 30 minutes, print a warning and estimated completion time before starting.

---

## the agent's Discretion

- Internal module boundaries for new analysis helpers
- Exact runtime-estimation heuristic
- Exact in-memory data structures used to pass walk-forward, Monte Carlo, and stability results between modules

## Deferred Ideas

None.
