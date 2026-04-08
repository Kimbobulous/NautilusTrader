# Testing Patterns

**Analysis Date:** 2026-04-08

## Test Framework

**Runner:**
- Not detected
- Config: No `jest.config.*`, `vitest.config.*`, or equivalent test config exists under `C:\dev\nautilustrader`

**Assertion Library:**
- Not detected

**Run Commands:**
```bash
No test command is defined in this repo
No watch command is defined in this repo
No coverage command is defined in this repo
```

## Test File Organization

**Location:**
- No collocated or dedicated test files were found under `.codex/`

**Naming:**
- No `*.test.*` or `*.spec.*` naming pattern is present

**Structure:**
```text
No test tree detected
```

## Test Structure

**Suite Organization:**
```text
No example test suite exists in the workspace today
```

**Patterns:**
- Verification currently leans on workflow-driven manual or agent-based checks rather than repository-local automated tests
- Planning and verification templates exist under `.codex/get-shit-done/templates/`, but they are documentation artifacts rather than executable test code

## Mocking

**Framework:** Not detected

**Patterns:**
```text
No mocking helpers or test doubles were found in the repo
```

**What to Mock:**
- If tests are added, mock shell boundaries and filesystem-heavy helpers first, especially functions in `.codex/get-shit-done/bin/lib/core.cjs` and command handlers that call `execSync`

**What NOT to Mock:**
- Keep parsing and roadmap/state transformation helpers real where possible so file-shape regressions are caught early

## Fixtures and Factories

**Test Data:**
```text
No fixture or factory directories detected
```

**Location:**
- Not applicable in current state

## Coverage

**Requirements:** None enforced

**View Coverage:**
```bash
Coverage tooling is not configured
```

## Test Types

**Unit Tests:**
- Not used in the current workspace
- Best candidate targets are `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/config.cjs`, and `.codex/get-shit-done/bin/lib/roadmap.cjs`

**Integration Tests:**
- Not used in the current workspace
- Highest-value future coverage would exercise `node .codex/get-shit-done/bin/gsd-tools.cjs` against a temporary `.planning/` sandbox

**E2E Tests:**
- Not used

## Common Patterns

**Async Testing:**
```text
No automated async test examples exist
```

**Error Testing:**
```text
No automated error-path test examples exist
```

## Practical Guidance For New Tests

- Place new tests near the CLI libraries they cover or introduce a dedicated test tree only if the project adds a real test runner first.
- Prioritize regression tests around path handling, roadmap parsing, config merging, and commit-guard behavior because those are the most workflow-critical code paths in `.codex/get-shit-done/bin/lib/`.
- Add a runnable test command before expanding the workflow surface further; today there is no executable safety net inside the repo itself.

---

*Testing analysis: 2026-04-08*
*Update when test patterns change*
