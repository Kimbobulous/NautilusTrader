# Phase 8: Interactive Tearsheet Reporting - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 8 adds automatic self-contained HTML tearsheets to the existing `backtest` and `optimize` workflows. It must build on the filesystem artifacts produced by Phases 6 and 7, render a professional dark-themed Plotly report without internet dependencies, and remain non-blocking so core run results still persist even if tearsheet generation fails.

</domain>

<decisions>
## Implementation Decisions

### Tearsheet structure
- **D-01:** The tearsheet uses an executive-summary-first structure rather than a dense dashboard or a long narrative report.
- **D-02:** The report must be scannable in roughly 30 seconds, with headline stats and equity information visible immediately after opening.
- **D-03:** Section order is locked as:
  - Header
  - Executive summary
  - Equity curve
  - Drawdown analysis
  - Trade analysis
  - Performance breakdowns
  - Audit diagnostics
  - Optimization sections when optimization artifacts exist
  - Footer
- **D-04:** The header must show strategy name, instrument, date range, and generated timestamp.
- **D-05:** The executive summary must show stat cards for:
  - `Total PnL`
  - `Sharpe ratio`
  - `Win rate`
  - `Max drawdown`
  - `Total trades`
  - `Profit factor`
- **D-06:** The equity section must render the full-run equity curve with drawdown shaded below it.
- **D-07:** The drawdown section must include the underwater curve and the drawdown-episodes table.
- **D-08:** The trade-analysis section must include return distribution histogram, win/loss breakdown, and average trade duration.
- **D-09:** The performance-breakdowns section must include session, volatility regime, monthly heatmap, day-of-week, and hour-of-day views.
- **D-10:** The audit-diagnostics section must include entry-rejection-reason breakdown and signal-quality-over-time views.
- **D-11:** The footer must include run-config summary and relevant file paths.

### Shared backtest and optimize tearsheet contract
- **D-12:** Phase 8 uses one shared tearsheet framework rather than separate backtest and optimization templates.
- **D-13:** Sections `1-7` are always present in the framework.
- **D-14:** The optimization-only section appears only when optimization artifacts exist.
- **D-15:** The tearsheet generator must accept a result-folder path and determine which sections to render from the files present on disk.
- **D-16:** Running `backtest` generates a tearsheet with sections `1-7`; running `optimize` generates a tearsheet with all sections when optimization artifacts are available.

### Chart defaults and visual hierarchy
- **D-17:** Headline stat cards plus equity/drawdown context must appear above the fold.
- **D-18:** The first question the tearsheet should answer is: did this strategy make money, what was the worst drawdown, and what was the Sharpe.
- **D-19:** Stat cards must use color-coded thresholds:
  - positive/good metrics use green/teal
  - poor metrics use red
  - example thresholds include `Sharpe > 1.0 = good`, `Sharpe < 0.5 = poor`, and `drawdown > 20% = poor`
- **D-20:** The visual style is a dark professional trading aesthetic.
- **D-21:** The color scheme must use dark backgrounds with teal/green for positive signals and red for negative signals, matching the existing platform direction.

### Interactivity depth
- **D-22:** Phase 8 should use moderate interactivity rather than a static report or a heavy app-like control surface.
- **D-23:** All Plotly charts must support standard hover, zoom, and pan interactions.
- **D-24:** Each section must support collapse/expand toggles so users can hide sections they do not care about.
- **D-25:** Monthly heatmap and breakdown views must support dropdown-style filtering such as session-specific filtering.
- **D-26:** Walk-forward views must support toggling individual windows on and off.
- **D-27:** The tearsheet must remain a single scrollable page; do not introduce tabs or multi-panel app shells.
- **D-28:** Use pure Plotly plus minimal vanilla JavaScript for toggles and light interactions; do not introduce a heavy JS framework.

### Generation and failure policy
- **D-29:** Tearsheet generation is automatic after every `backtest` and `optimize` run; it is not a separate command.
- **D-30:** Tearsheet generation must be non-blocking, consistent with the Phase 7 analytics policy.
- **D-31:** The tearsheet should be generated on a best-effort basis and clearly mark missing sections instead of silently dropping them.
- **D-32:** If a section's required files are missing, render the section header and a clear notice such as `Section unavailable - audit_log.csv not found`.
- **D-33:** The tearsheet should only be skipped entirely when the core summary input is missing, especially `summary.json`.
- **D-34:** If core summary input is missing, the platform should log a warning and skip tearsheet generation rather than failing the whole run.

### File and embedding contract
- **D-35:** The generated HTML file must be named `tearsheet.html`.
- **D-36:** `tearsheet.html` lives in the run result folder alongside `summary.json`.
- **D-37:** The HTML must be completely self-contained.
- **D-38:** No external CDN calls or internet access may be required to open the tearsheet.
- **D-39:** Charts should embed their data in the HTML as local JSON/config, not fetch data at runtime.
- **D-40:** File size should stay reasonable, so the tearsheet must not embed raw `audit_log.csv` contents directly.
- **D-41:** Large artifacts such as the audit log must be summarized into visual/statistical outputs rather than inlined wholesale.
- **D-42:** The tearsheet file must be added to `manifest.json` automatically.

### the agent's Discretion
- Exact HTML/CSS component composition for the stat-card grid, section chrome, and footer formatting
- Exact Plotly chart types for audit diagnostics and optimization diagnostics, as long as they honor the locked section purposes
- Exact threshold palette and styling details within the locked dark-theme/teal-green-red aesthetic

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and phase scope
- `.planning/PROJECT.md` - v1.1 milestone priorities, automatic tearsheet requirement, native-first rule, and no-strategy-change constraint
- `.planning/REQUIREMENTS.md` - Phase 8 requirements `VIZ-01` through `VIZ-03`
- `.planning/ROADMAP.md` - Phase 8 goal and success criteria
- `.planning/STATE.md` - current milestone state and carry-forward concerns

### Filesystem-first artifact sources
- `src/mgc_bt/backtest/artifacts.py` - current backtest artifact writing flow and manifest update point where tearsheet generation should attach
- `src/mgc_bt/backtest/analytics.py` - Phase 7 analytics contract and data available for tearsheet sections
- `src/mgc_bt/backtest/results.py` - canonical summary, trade-log, equity-curve, and additive drawdown metrics
- `src/mgc_bt/optimization/results.py` - optimization artifact layout including `walk_forward/`, `monte_carlo/`, `stability/`, and `analytics/`
- `src/mgc_bt/optimization/study.py` - optimize orchestration path where automatic tearsheet generation will attach
- `src/mgc_bt/cli.py` - current user-visible run summary behavior that tearsheet generation should extend additively

### Prior phase contracts Phase 6 and Phase 7
- `.planning/phases/06-research-integrity-framework/06-CONTEXT.md` - walk-forward, Monte Carlo, and stability output contract consumed by the optimization tearsheet
- `.planning/phases/06-research-integrity-framework/06-VERIFICATION.md` - confirmed artifact availability and constraints from the research-integrity layer
- `.planning/phases/07-analytics-and-audit-layer/07-CONTEXT.md` - canonical analytics contract Phase 8 must read directly from disk
- `.planning/phases/07-analytics-and-audit-layer/07-VERIFICATION.md` - confirms Phase 7 artifacts are filesystem-first and ready for tearsheet consumption

### Existing plotting and output conventions
- `src/mgc_bt/backtest/plotting.py` - current local plotting conventions and available equity-curve rendering helper
- `tests/test_backtest_artifacts.py` - backtest output contract and manifest expectations
- `tests/test_optimization_results.py` - optimization output contract and coexistence requirements for Phase 6/7 artifacts

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mgc_bt/backtest/plotting.py` already provides a local plotting helper and establishes the expectation that result visualizations are saved in the run directory.
- `src/mgc_bt/backtest/analytics.py` and `src/mgc_bt/optimization/analytics.py` already transform run artifacts into filesystem-first summaries, which means Phase 8 can consume those outputs without recomputation.
- `src/mgc_bt/backtest/artifacts.py` and `src/mgc_bt/optimization/results.py` already own manifest generation and are the natural insertion points for `tearsheet.html`.

### Established Patterns
- Run outputs are timestamped folders with a `manifest.json` describing generated files.
- Post-processing steps are additive and non-blocking; core result persistence must happen before optional reporting.
- The platform already distinguishes core artifacts from heavier optional analysis outputs, which supports best-effort tearsheet sections.

### Integration Points
- Backtest tearsheet generation should attach after core bundle and analytics generation in `src/mgc_bt/backtest/artifacts.py`.
- Optimization tearsheet generation should attach after ranked results, best-run bundle, and optional Phase 6/7 analysis outputs are written in `src/mgc_bt/optimization/results.py` or adjacent orchestration code.
- The tearsheet generator should be a filesystem-reader that takes a run directory and decides which sections to render based on discovered files.

</code_context>

<specifics>
## Specific Ideas

- The report should feel like a professional trading/research report, not a generic product dashboard.
- The tearsheet must answer the top-level research question immediately, then let the user drill into diagnostics.
- Missing sections should be explicit, because silence would create false confidence.
- The optimization tearsheet should layer walk-forward, Monte Carlo, and sensitivity views into the same narrative rather than acting like a separate app.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 8 scope.

</deferred>

---

*Phase: 08-interactive-tearsheet-reporting*
*Context gathered: 2026-04-09*
