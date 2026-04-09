# Milestone v1.2 Requirements

## Research Execution

- [ ] **RES-01**: User can run a full 5-year MGC walk-forward optimization and generate the complete research artifact bundle: tearsheet, Monte Carlo outputs, stability outputs, walk-forward outputs, and ranked parameter results.
- [ ] **RES-02**: After Phase 1, the workflow stops and reports the walk-forward aggregated Sharpe, Monte Carlo p-value, top 3 parameter sets, and any warnings or anomalies before any further work proceeds.

## Strategy Refinement

- [ ] **REF-01**: User can analyze the MGC optimization outputs to identify weaknesses in the current strategy logic and document evidence-based refinement targets.
- [ ] **REF-02**: User can apply bounded MGC strategy refinements, rerun optimization, and compare before/after Sharpe, walk-forward results, and Monte Carlo evidence.
- [ ] **REF-03**: After Phase 2, the workflow stops and reports whether refinements improved or harmed results before proceeding further.

## Second Strategy Validation

- [ ] **STRAT-01**: User can implement a second MGC strategy using `BaseResearchStrategy`, the indicator/primitives library, and the strategy registry without bypassing the reusable platform.
- [ ] **STRAT-02**: User can run the second strategy through the full platform including analytics and tearsheet generation.
- [ ] **STRAT-03**: User can compare the MGC pullback strategy and the second strategy through the dedicated `compare` workflow and review the resulting comparison tearsheet.
- [ ] **STRAT-04**: After Phase 3, the workflow stops and reports second-strategy results, comparison findings, and any platform issues before proceeding.

## Research Report and Platform Validation

- [ ] **RPT-01**: User can run a final validation pass on both strategies and capture the findings in a research report.
- [ ] **RPT-02**: User can update operator documentation with research lessons learned and any platform usage changes discovered during v1.2.
- [ ] **RPT-03**: After Phase 4, the workflow stops and reports a final summary of both strategies, platform health, and any remaining issues.

## Future Requirements

- [ ] Add live trading and paper trading support in a future major milestone.
- [ ] Support multi-instrument and portfolio-level research workflows.
- [ ] Add new data source integrations beyond the existing local Databento workflow.

## Out of Scope

- Infrastructure rewrites unless a real bug is found during research execution.
- Any new strategy implementation that bypasses `BaseResearchStrategy`, the registry, or the reusable indicator/primitives layer.
- Multi-instrument or portfolio-level strategy evaluation.
- Live trading, paper trading, or broker integration.
- New market data sources beyond the existing local Databento workflow.

## Traceability

| Requirement | Phase |
|-------------|-------|
| RES-01 | Phase 10 |
| RES-02 | Phase 10 |
| REF-01 | Phase 11 |
| REF-02 | Phase 11 |
| REF-03 | Phase 11 |
| STRAT-01 | Phase 12 |
| STRAT-02 | Phase 12 |
| STRAT-03 | Phase 12 |
| STRAT-04 | Phase 12 |
| RPT-01 | Phase 13 |
| RPT-02 | Phase 13 |
| RPT-03 | Phase 13 |
