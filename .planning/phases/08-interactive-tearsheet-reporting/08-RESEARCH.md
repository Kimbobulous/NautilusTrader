---
phase: 08
slug: interactive-tearsheet-reporting
status: complete
created: 2026-04-09
---

# Phase 08 Research

## Question

How should Phase 8 add automatic self-contained Plotly tearsheets without rerunning analytics, breaking the existing backtest and optimize flows, or inflating memory usage on large runs?

## Findings

### 1. The platform already has a filesystem-first reporting contract

Phase 7 and Phase 6 already persist nearly all inputs a tearsheet needs:

- Backtest run folders already contain:
  - `summary.json`
  - `trades.csv`
  - `equity_curve.png`
  - `run_config.toml`
  - `analytics/audit_log.csv`
  - `analytics/drawdown_episodes.csv`
  - `analytics/underwater_curve.csv`
  - `analytics/breakdowns/*.csv`
- Optimization run folders already contain:
  - `ranked_results.csv`
  - `optimization_summary.json`
  - `best_run/`
  - `analytics/parameter_sensitivity.csv`
  - `analytics/breakdowns/*.csv`
  - optional `walk_forward/`
  - optional `monte_carlo/`
  - optional `stability/`

Implication:
- The tearsheet should be a read-only renderer over run folders.
- It should not recompute analytics already emitted in earlier phases.
- It should infer available sections from disk presence, matching the locked context.

### 2. Existing attachment points are already correct for non-blocking generation

The natural hook points are already established:

- Backtest:
  - `src/mgc_bt/backtest/artifacts.py`
  - core bundle is written first
  - analytics attach second
  - manifest writes last
- Optimization:
  - `src/mgc_bt/optimization/results.py`
  - result subtrees are written before final manifest assembly
  - optional analysis outputs are already best-effort in `study.py`

Implication:
- Tearsheet generation should follow the same pattern as analytics:
  - write core artifacts first
  - generate tearsheet second
  - warn and continue on failure
  - update `manifest.json` last

### 3. A dedicated reporting module is cleaner than extending current PNG plotting helpers

Current plotting support is intentionally minimal:

- `src/mgc_bt/backtest/plotting.py` only saves static PNG equity curves.

Plotly tearsheets need:

- shared filesystem loaders
- HTML section composition
- JSON-safe embedding
- optional-section detection
- minimal JS toggles
- dark-theme styling

Implication:
- Phase 8 should introduce a dedicated reporting/tearsheet module instead of stretching `plotting.py` beyond its current role.
- Keep PNG helpers intact for compatibility and use them alongside the new HTML path, not as the basis for it.

### 4. Self-contained HTML is feasible without a web app

The requirement is a single local HTML file with no network dependency.

For Plotly, the right approach is:

- generate figures in Python
- embed figures directly into the HTML using local Plotly JS payloads
- avoid external CDN references
- keep the page as one scrollable document with light inline JS for section toggles and trace/show-hide controls
- use `plotly.io.to_html()` with `include_plotlyjs=True` exactly once, then `include_plotlyjs=False` for later charts in the same document

Implication:
- A pure Python HTML generator is sufficient.
- No frontend build tooling or JS framework is needed.
- The page can stay deterministic and testable as an artifact generator, not an application.
- The renderer should centralize Plotly embed assembly so the JS bundle is written once and the total HTML stays within the user's under-10MB target.

### 5. Missing-section notices should be data-loader driven

The locked Phase 8 contract requires explicit notices like:

- `Section unavailable - audit_log.csv not found`

That is easiest if the generator first builds a typed availability map from the run folder, such as:

- summary present / missing
- backtest analytics present / partial
- optimization analysis present / partial

Implication:
- Shared loader code should return both parsed payloads and structured missing-file notices.
- Section renderers should consume that availability map and render either content or an explicit unavailable notice.

### 6. The audit log should not be embedded raw

Phase 7 intentionally streams `audit_log.csv` row-by-row to avoid runaway memory use. A 5-year run could produce a very large audit file.

Implication:
- The tearsheet must summarize audit data from disk into compact aggregations:
  - rejection reason counts
  - setup counts over time
  - fired vs rejected ratios
- It should never inline raw audit rows into the HTML.
- Audit summarization should be bounded and streaming-friendly where practical.

### 7. Best-run optimization tearsheet data should come from `best_run/` first

Optimization runs already persist a canonical best-run bundle containing:

- backtest-style summary
- trades
- equity curve PNG
- analytics subtree
- optional holdout outputs

Implication:
- The optimization tearsheet should reuse the same section renderers for the shared sections by reading `best_run/` as the base reporting source.
- Optimization-only sections should layer on top from the parent optimization run directory:
  - `ranked_results.csv`
  - `walk_forward/`
  - `monte_carlo/`
  - `stability/`
  - root `analytics/parameter_sensitivity.csv`

### 8. Manifest and latest handling should stay additive

Both backtest and optimization already refresh `latest/` by copying the canonical run directory after manifest generation.

Implication:
- `tearsheet.html` should be written into the canonical run dir before the final manifest pass so `latest/` inherits it automatically.
- No separate `latest` tearsheet logic should be added.

## Recommended Architecture

### Module split

- `src/mgc_bt/reporting/loaders.py`
  - filesystem readers for backtest and optimization run dirs
  - typed availability/missing-section model
- `src/mgc_bt/reporting/sections.py`
  - shared section builders for header, summary, equity, drawdown, trade analysis, breakdowns, audit diagnostics, footer
- `src/mgc_bt/reporting/optimization_sections.py`
  - walk-forward, Monte Carlo, stability, parameter sensitivity, ranked-results views
- `src/mgc_bt/reporting/tearsheet.py`
  - shared HTML document assembly
  - dark theme
  - self-contained Plotly embedding
  - section toggles / small inline JS

### Integration

- Backtest integration point:
  - `src/mgc_bt/backtest/artifacts.py`
- Optimization integration point:
  - `src/mgc_bt/optimization/results.py` or final orchestration point in `src/mgc_bt/optimization/study.py`

### Failure policy

- If `summary.json` is missing:
  - warn and skip tearsheet generation
- If any non-core source is missing:
  - render explicit unavailable section notice
- If tearsheet generation itself raises:
  - warn and continue
  - do not block core artifact persistence

## Risks To Address In Planning

1. HTML size growth from too many embedded figures or large tables
2. Drift between backtest and optimization section expectations
3. Fragile parsing of optional analysis outputs when files are partially present
4. Non-deterministic or brittle HTML snapshot testing
5. Accidentally recomputing analytics from heavyweight raw sources instead of consuming Phase 7 outputs

## Planning Guidance

- Keep the tearsheet generator read-only over filesystem artifacts.
- Reuse shared sections for both backtest and optimization.
- Treat optimization-only content as additive sections, not a separate app.
- Test for:
  - file existence
  - manifest inclusion
  - explicit unavailable-section notices
  - self-contained HTML without CDN usage
  - non-blocking failure behavior
