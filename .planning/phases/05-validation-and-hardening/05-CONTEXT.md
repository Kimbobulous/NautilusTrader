# Phase 5: Validation and Hardening - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 hardens the existing local MGC research workflow without adding new trading logic, new indicators, or new optimization capabilities. This phase owns shared preflight validation, clearer operator-facing failure modes, regression coverage around the most fragile workflow edges, safer result-directory handling, a unified `health` readiness command, and concise operator documentation for repeatable local use.

</domain>

<decisions>
## Implementation Decisions

### Scope guardrails
- **D-01:** Phase 5 is hardening only and must not add new strategy logic, indicators, or optimization features.
- **D-02:** If implementation uncovers ideas that expand workflow scope instead of hardening it, those ideas should be deferred or added to backlog rather than implemented here.
- **D-03:** The working definition of done is that a new local user can clone the repo, follow `USAGE.md`, and run `ingest`, `backtest`, `optimize`, and `health` without confusing failures.

### Validation depth
- **D-04:** Use strong preflight checks before all three primary commands: `ingest`, `backtest`, and `optimize`.
- **D-05:** Preflight failures must produce clear actionable error messages instead of raw Python tracebacks.
- **D-06:** Shared readiness checks should be reusable across command execution and the new `health` command rather than duplicated in separate code paths.

### Ingest preflight
- **D-07:** `ingest` preflight must verify configured source data directories exist.
- **D-08:** `ingest` preflight must verify at least one relevant DBN file is discoverable for the enabled ingest types.
- **D-09:** `ingest` preflight must verify the configured catalog path is writable.
- **D-10:** `ingest` preflight should warn if the target catalog already appears to contain data for the same date range rather than silently pretending this is a fresh write.

### Backtest preflight
- **D-11:** `backtest` preflight must verify the catalog exists.
- **D-12:** `backtest` preflight must verify the catalog contains instrument definitions, bars, and trades needed for the selected workflow.
- **D-13:** `backtest` preflight must verify the requested date range actually has data in the catalog.
- **D-14:** If an instrument ID is explicitly supplied, `backtest` preflight must verify that instrument exists in the catalog.
- **D-15:** `backtest` preflight must verify required backtest settings are present and structurally valid before runner execution begins.

### Optimize preflight
- **D-16:** `optimize` preflight must include all `backtest` readiness checks because optimization depends on the same runner.
- **D-17:** `optimize` preflight must verify the in-sample and holdout windows do not overlap.
- **D-18:** `optimize` preflight must verify the holdout end date is not in the future.
- **D-19:** `optimize` preflight must verify the Optuna storage path is writable.
- **D-20:** If `--resume` is passed, `optimize` preflight must verify the named study already exists instead of letting Optuna silently create or mis-handle it.

### Health command
- **D-21:** Add a CLI command `python -m mgc_bt health`.
- **D-22:** `health` must run the shared preflight checks for `ingest`, `backtest`, and `optimize` in one pass.
- **D-23:** `health` should summarize what is ready, what is missing, and what needs attention.
- **D-24:** `health` is a hardening/readiness surface, not a separate workflow with its own duplicated logic.

### Regression coverage scope
- **D-25:** Regression coverage should focus on the most fragile areas instead of broad feature expansion.
- **D-26:** Required regression coverage includes malformed `settings.toml`, missing catalog, nonexistent optimization resume target, result-output integrity, and ranked-results CSV integrity.
- **D-27:** Add tests ensuring output folders contain the expected files after each command path covered by automated tests.
- **D-28:** Add tests ensuring `ranked_results.csv` has the correct columns and is not empty after optimization persistence.

### Operator safeguards
- **D-29:** Use a mixed fail/warn model.
- **D-30:** Hard fail on integrity issues such as missing catalog, invalid date windows, overlapping in-sample and holdout windows, or corrupt/missing resume storage targets.
- **D-31:** Warn and continue for convenience issues such as preexisting output folders, catalog continuity gaps, or holdout Sharpe degradation.

### Results and storage hygiene
- **D-32:** Add overwrite protection for result directories rather than assuming timestamp uniqueness is always enough.
- **D-33:** If a timestamped output directory already exists, append a suffix instead of overwriting it.
- **D-34:** Add `manifest.json` to each result folder listing what files were written and when.
- **D-35:** Do not add automated cleanup or retention deletion in Phase 5.
- **D-36:** Add a `--force` flag to `backtest` and `optimize` that explicitly allows refreshing `latest/`.

### Documentation and CLI polish
- **D-37:** Add a root `USAGE.md`.
- **D-38:** `USAGE.md` must document exact commands for `ingest`, `backtest`, `optimize`, and `health`.
- **D-39:** `USAGE.md` must document expected output structure, optimization resume usage, how to rerun best parameters manually, and common error messages with fixes.
- **D-40:** Improve CLI `--help` text so command options are understandable without opening docs.

### Carry-forward project rules
- **D-41:** Continue using Nautilus native infrastructure as the foundation rather than reimplementing existing Nautilus behavior.
- **D-42:** Any catalog-touching or catalog-assuming hardening work must preserve the verified Databento decode split:
  - definitions use legacy Cython decoding
  - bars/trades use `as_legacy_cython=False`

### the agent's Discretion
- Exact module boundaries for preflight validation helpers and health-report rendering
- The precise manifest JSON shape beyond the required file listing and timestamp intent
- Whether some warnings are grouped by category or emitted inline, as long as they remain actionable

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing workflow contracts
- `.planning/PROJECT.md` - Scope, hardening boundary, and native-Nautilus-first rule
- `.planning/REQUIREMENTS.md` - Phase 5 must still satisfy CLI-01, DATA-06, BT-06, and OPT-05 without scope creep
- `.planning/ROADMAP.md` - Phase goal and existing three-plan breakdown
- `.planning/STATE.md` - Current phase position and carry-forward risks

### Existing implementation contracts
- `.planning/phases/01-catalog-foundation/01-CONTEXT.md` - Ingest and catalog assumptions that Phase 5 validation must respect
- `.planning/phases/01-catalog-foundation/01-VERIFICATION.md` - Verified ingestion output expectations
- `.planning/phases/02-backtest-runner/02-CONTEXT.md` - Runner and artifact expectations Phase 5 must harden rather than replace
- `.planning/phases/02-backtest-runner/02-VERIFICATION.md` - Verified backtest output bundle and next-bar assumptions
- `.planning/phases/04-optimization-workflow/04-CONTEXT.md` - Optimization contract, holdout separation, and storage expectations
- `.planning/phases/04-optimization-workflow/04-VERIFICATION.md` - Verified optimization outputs and engine-reuse decision that hardening should preserve

### Nautilus references
- `nt_docs/concepts/backtesting.md` - Current Nautilus backtest workflow reference for validation assumptions and native execution handling
- `nt_docs/api_reference/backtest.md` - Current backtest API reference used by the runner
- `nt_docs/concepts/execution.md` - Native execution and risk responsibilities that should not be duplicated in hardening work

### Project instructions
- `AGENTS.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mgc_bt/cli.py` - Existing command surface for `ingest`, `backtest`, and `optimize`; Phase 5 extends it with clearer help, force flags, and `health`
- `src/mgc_bt/config.py` - Existing typed settings loader where structural validation already begins
- `src/mgc_bt/ingest/service.py` and `src/mgc_bt/ingest/validation.py` - Existing ingest discovery and structural validation logic, but no standalone preflight contract yet
- `src/mgc_bt/backtest/runner.py` - Existing reusable runner that currently assumes the catalog is already valid
- `src/mgc_bt/backtest/artifacts.py` - Existing timestamped result persistence and `latest/` refresh logic that currently overwrites `latest/` unconditionally and writes no manifest
- `src/mgc_bt/optimization/study.py`, `src/mgc_bt/optimization/results.py`, and `src/mgc_bt/optimization/storage.py` - Existing optimization orchestration and persistence surfaces, including resume storage, but no explicit resume preflight and no manifest support

### Established Patterns
- Core workflows are already routed through reusable Python functions with thin CLI wrappers
- Results are already stored in timestamped run directories with `latest/` mirrors
- Existing tests already cover config, CLI, ingest discovery, runner behavior, artifacts, optimization persistence, and strategy behavior

### Current Gaps To Harden
- No unified preflight service across commands
- No `health` command
- No manifest files in result directories
- No timestamp-collision handling beyond `exist_ok=False`
- No explicit `--force` gating for refreshing `latest/`
- Some local operator errors still rely on exception flow rather than guided readiness checks

</code_context>

<specifics>
## Specific Ideas

- Hardening should prefer one shared validation layer that command handlers and `health` both call.
- Result manifests should make it easy to verify what was written without reading the whole directory tree manually.
- The CLI should feel safer for long local optimization runs by telling the user what is missing before a multi-hour run starts.

</specifics>

<deferred>
## Deferred Ideas

- Automated result cleanup or retention deletion
- Any new trading rules, data sources, indicators, or optimization regimes
- Distributed health checks beyond the local configured environment

</deferred>

---

*Phase: 05-validation-and-hardening*
*Context gathered: 2026-04-09*
