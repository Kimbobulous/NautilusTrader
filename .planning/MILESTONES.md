# Milestones

## v1.1 Quant Research Infrastructure (Shipped: 2026-04-09)

**Phases completed:** 4 phases, 16 plans
**Files changed:** 163 | **Net LOC:** ~+4,586 | **Total Python LOC:** 11,792

### Accomplishments

- Added walk-forward optimization with rolling in-sample/OOS windows, time-weighted aggregate OOS metrics, and a protected final test evaluation gate.
- Delivered deterministic Monte Carlo permutation and bootstrap analysis to distinguish genuine strategy edge from luck.
- Integrated Optuna fANOVA parameter stability analysis with a 5×5 importance heatmap and neighborhood robustness reruns.
- Shipped streaming trade audit capture and multi-dimension performance breakdowns (session, volatility regime, month, year, day/hour).
- Generated automatic self-contained Plotly HTML tearsheets after every `backtest` and `optimize` run.
- Refactored the platform for strategy reuse: thin base class, standalone indicator primitives, config-driven strategy registry, and a dedicated side-by-side `compare` command.

### Notes

- Archived roadmap: [.planning/milestones/v1.1-ROADMAP.md](.planning/milestones/v1.1-ROADMAP.md)
- Archived requirements: [.planning/milestones/v1.1-REQUIREMENTS.md](.planning/milestones/v1.1-REQUIREMENTS.md)
- All 15 requirements validated. 89 tests passing at close.

---

## v1.0 - MGC Research Workflow

**Shipped:** 2026-04-09
**Phases:** 5
**Plans:** 17
**Tasks:** 45

### Accomplishments

- Built a complete Databento-to-Nautilus MGC catalog ingestion workflow with validation and reporting.
- Delivered a reusable, artifact-producing Nautilus backtest runner with single-contract and auto-roll support.
- Implemented the production rule-based MGC strategy plus dedicated risk controls aligned with Nautilus native infrastructure.
- Added Optuna optimization with ranked results, best-run exports, and holdout evaluation.
- Hardened the local workflow with shared readiness checks, a `health` command, manifests, explicit `--force` behavior, and an operator usage guide.

### Notes

- Archived roadmap: [.planning/milestones/v1.0-ROADMAP.md](C:/dev/nautilustrader/.planning/milestones/v1.0-ROADMAP.md)
- Archived requirements: [.planning/milestones/v1.0-REQUIREMENTS.md](C:/dev/nautilustrader/.planning/milestones/v1.0-REQUIREMENTS.md)
- Milestone was archived without a separate `v1.0` milestone-audit file; completion is based on phase verification artifacts and a clean 100% roadmap state.
