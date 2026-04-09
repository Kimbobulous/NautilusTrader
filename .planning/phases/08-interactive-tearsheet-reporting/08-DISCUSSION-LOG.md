# Phase 8: Interactive Tearsheet Reporting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 08-interactive-tearsheet-reporting
**Areas discussed:** Tearsheet structure, Shared contract, Core chart defaults, Interactivity depth, Generation and failure policy

---

## Tearsheet Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Executive-summary first | Headline stats and equity first, then drill-down sections | ✓ |
| Dashboard grid | Many charts visible at once in a denser layout | |
| Narrative report | Story-first top-to-bottom report flow | |

**User's choice:** Executive-summary first
**Notes:** Locked section order is header, executive summary, equity curve, drawdown analysis, trade analysis, performance breakdowns, audit diagnostics, optimization sections when available, then footer.

---

## Backtest vs Optimize Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Shared framework | One tearsheet shell with extra optimization sections when artifacts exist | ✓ |
| Two distinct layouts | Separate backtest and optimize templates | |
| Shared shell, reordered | Same shell but different section emphasis/order | |

**User's choice:** Shared framework
**Notes:** Sections 1-7 are always present. Optimization-only content appears when optimization artifacts exist. The generator should infer renderable sections from files on disk.

---

## Core Chart Defaults

| Option | Description | Selected |
|--------|-------------|----------|
| Equity and drawdown first | Headline cards and key profitability/risk charts above the fold | ✓ |
| Audit first | Lead with diagnostics and signal explanation | |
| Different defaults by run type | Backtest and optimize start differently | |

**User's choice:** Equity and drawdown first
**Notes:** The first questions the report should answer are whether the strategy made money, how bad the drawdown was, and what the Sharpe looked like. Stat cards should use good/bad threshold coloring.

---

## Interactivity Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Standard interactions only | Hover, zoom, and pan only | |
| Moderate interactivity | Hover/zoom plus section toggles and selective trace/filter controls | ✓ |
| Heavy app-like controls | Tabs, panels, and more complex control surfaces | |

**User's choice:** Moderate interactivity
**Notes:** Plotly charts should support normal interactions. Sections should collapse/expand. Breakdown views need filters. Walk-forward views need trace toggles. Use minimal vanilla JS, no heavy framework, and keep one scrollable page.

---

## Generation and Failure Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Best-effort generation | Render partial tearsheet with explicit missing-section notices | ✓ |
| Skip on missing inputs | Do not generate if required section inputs are absent | |
| Mixed strictness | Different strictness by run type | |

**User's choice:** Best-effort generation
**Notes:** Missing section inputs should produce explicit section-level notices. Only missing `summary.json` should skip tearsheet generation entirely, and even then it should warn rather than fail the run.

---

## the agent's Discretion

- Exact Plotly chart selection for each section
- Exact CSS layout and component styling within the locked dark trading aesthetic
- Exact manifest-update placement and helper-module boundaries

## Deferred Ideas

None.
