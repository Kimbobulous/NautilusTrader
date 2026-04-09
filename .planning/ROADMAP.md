# Roadmap: MGC Backtesting and Optimization System

## Milestones

- ✅ **v1.0 MGC Research Workflow** — Phases 1-5 (shipped 2026-04-09) — [archive](.planning/milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Quant Research Infrastructure** — Phases 6-9 (shipped 2026-04-09) — [archive](.planning/milestones/v1.1-ROADMAP.md)
- 🚧 **v1.2 Strategy Validation and Live Research** — Phases 10-13

## Active Phases

### Phase 10: Full 5-Year Optimization Run

**Status**: NOT STARTED
**Goal**: Run the complete 5-year MGC walk-forward optimization and produce the full research artifact bundle without changing infrastructure or strategy logic.
**Depends on**: Phase 9
**Requirements**: RES-01, RES-02
**Success Criteria**:
1. A complete 5-year walk-forward optimization run finishes on the shipped platform and writes the expected artifacts.
2. The run produces a full tearsheet, Monte Carlo outputs, parameter stability outputs, and walk-forward summary.
3. The phase stops after execution and reports walk-forward aggregated Sharpe, Monte Carlo p-value, top 3 parameter sets, and any warnings or anomalies.
4. No Phase 11 work begins until the human explicitly approves it.

### Phase 11: Results Analysis and Strategy Refinement

**Status**: NOT STARTED
**Goal**: Analyze the MGC optimization evidence, refine the strategy if warranted, and validate whether changes improve or harm results.
**Depends on**: Phase 10
**Requirements**: REF-01, REF-02, REF-03
**Success Criteria**:
1. The optimization outputs are analyzed for walk-forward behavior, Monte Carlo evidence, and parameter stability.
2. Any MGC refinements are evidence-driven and limited to strategy logic or risk parameters justified by research findings.
3. A follow-up validation run compares before/after Sharpe, walk-forward results, and Monte Carlo p-value.
4. The phase stops after reporting whether refinements improved or hurt results and waits for explicit approval.

### Phase 12: Second Strategy Implementation

**Status**: NOT STARTED
**Goal**: Implement a second contrasting MGC strategy on the reusable platform and compare it directly against the pullback strategy.
**Depends on**: Phase 11
**Requirements**: STRAT-01, STRAT-02, STRAT-03, STRAT-04
**Success Criteria**:
1. A second strategy is implemented using `BaseResearchStrategy`, the reusable indicator/primitives layer, and the strategy registry.
2. The second strategy runs through the full platform including analytics and tearsheet generation.
3. The `compare` workflow produces side-by-side comparison artifacts for both strategies.
4. The phase stops after reporting second-strategy results, comparison findings, and any platform issues, then waits for approval.

### Phase 13: Platform Stress Test and Documentation

**Status**: NOT STARTED
**Goal**: Validate the platform end to end across both strategies and capture the findings in final documentation.
**Depends on**: Phase 12
**Requirements**: RPT-01, RPT-02, RPT-03
**Success Criteria**:
1. The final validation pass covers both strategies and confirms the platform remains healthy.
2. A research report captures evidence for or against alpha, platform observations, and remaining issues.
3. `USAGE.md` is updated with any lessons learned or operator changes discovered during v1.2.
4. The phase stops after reporting final strategy summaries, platform health, and outstanding issues.

## Completed Phases

<details>
<summary>✅ v1.0 MGC Research Workflow (Phases 1-5) — SHIPPED 2026-04-09</summary>

- [x] Phase 1: Catalog Foundation — completed 2026-04-09
- [x] Phase 2: Backtest Runner — completed 2026-04-09
- [x] Phase 3: Production Strategy — completed 2026-04-09
- [x] Phase 4: Optimization Workflow — completed 2026-04-09
- [x] Phase 5: Validation and Hardening — completed 2026-04-09

</details>

<details>
<summary>✅ v1.1 Quant Research Infrastructure (Phases 6-9) — SHIPPED 2026-04-09</summary>

- [x] Phase 6: Research Integrity Framework (4/4 plans) — completed 2026-04-09
- [x] Phase 7: Analytics and Audit Layer (4/4 plans) — completed 2026-04-09
- [x] Phase 8: Interactive Tearsheet Reporting (4/4 plans) — completed 2026-04-09
- [x] Phase 9: Reusable Strategy Platform (4/4 plans) — completed 2026-04-09

</details>

## Next Step

Start with `/gsd-discuss-phase 10` to prepare the full 5-year research run.
