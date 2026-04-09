# Milestone v1.1: Quant Research Infrastructure

**Status:** ACTIVE
**Phases:** 6-9

## Overview

v1.1 extends the shipped MGC research platform into a more professional quant research infrastructure. The milestone keeps the existing ingestion, backtest, strategy, optimization, and hardening foundation intact while adding statistically stronger validation, deeper analytics, interactive reporting, and reusable strategy infrastructure.

Priority order for v1.1 is:
1. Research correctness
2. Visualization quality
3. Platform reusability

## Phases

### Phase 6: Research Integrity Framework

**Status**: COMPLETE (2026-04-09)
**Goal**: Add statistically trustworthy validation workflows on top of the existing optimization pipeline without changing the current strategy behavior.
**Depends on**: v1.0 shipped baseline
**Requirements**: INT-01, INT-02, INT-03, INT-04
**Success Criteria**:
1. `optimize --walk-forward` can roll through configured windows, optimize in-sample, test the next out-of-sample window, and aggregate the results.
2. Optimization workflows can enforce a three-way train/validate/test split with a protected final test window that is untouched until the end.
3. Monte Carlo analysis can randomize or resample realized trade results and persist outputs that distinguish robustness from luck.
4. Parameter-stability analysis surfaces robust versus fragile parameter regions instead of only ranking a single best parameter set.

### Phase 7: Analytics and Audit Layer

**Status**: COMPLETE (2026-04-09)
**Goal**: Make every backtest and optimization result explainable through richer audit detail and performance breakdowns.
**Depends on**: Phase 6
**Requirements**: ANL-01, ANL-02, ANL-03, ANL-04
**Success Criteria**:
1. Each run can produce a trade audit record showing which indicators and gates were active when a trade was taken or rejected.
2. Performance can be broken down by session, volatility regime, month, and year from the same result set.
3. Drawdown reporting includes duration, recovery, and underwater-equity analysis rather than just max depth.
4. Parameter sensitivity metrics quantify how much Sharpe or related performance changes as each parameter moves.

### Phase 8: Interactive Tearsheet Reporting

**Status**: COMPLETE (2026-04-09)
**Goal**: Generate professional, self-contained interactive HTML tearsheets automatically from backtest and optimization outputs.
**Depends on**: Phase 7
**Requirements**: VIZ-01, VIZ-02, VIZ-03
**Success Criteria**:
1. Every `backtest` run emits a self-contained Plotly HTML tearsheet automatically.
2. Every `optimize` run emits a self-contained Plotly HTML tearsheet automatically, including walk-forward and Monte Carlo visuals when those analyses are present.
3. The tearsheet includes core views such as equity, drawdown, monthly PnL heatmap, return distribution, and parameter/validation charts from the available outputs.
4. Generated HTML files open locally in any browser with no extra services or manual assembly steps.

### Phase 9: Reusable Strategy Platform

**Status**: COMPLETE (2026-04-09)
**Goal**: Refactor the platform for future strategy reuse and direct strategy-to-strategy comparison without changing current validated behavior.
**Depends on**: Phase 8
**Requirements**: PLT-01, PLT-02, PLT-03, PLT-04
**Success Criteria**:
1. The current strategy can be expressed through a generic strategy base and reusable indicator library with behavior preserved.
2. The runner can select which strategy to execute from configuration rather than from hardcoded code paths.
3. The platform can compare two strategies on the same data and present their outcomes side by side.
4. Existing v1.0 behavior remains intact and the prior passing test suite stays green while the platform becomes more reusable.

## Milestone Summary

**Requirements Count:** 15
**Phases Count:** 4
**Starting Phase Number:** 6

## Next Step

Run `/gsd-complete-milestone` when you're ready to archive v1.1.
