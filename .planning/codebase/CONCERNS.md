# Codebase Concerns

**Analysis Date:** 2026-04-08

## Tech Debt

**Hard-coded workspace paths:**
- Issue: Many skills, workflows, and runtime config entries embed the absolute path `C:/dev/nautilustrader/.codex/...`
- Files: `.codex/config.toml`, `.codex/skills/gsd-new-project/SKILL.md`, `.codex/skills/gsd-map-codebase/SKILL.md`, `.codex/get-shit-done/workflows/new-project.md`
- Impact: The workspace is tightly coupled to one machine path and is harder to relocate or reuse on another checkout
- Fix approach: Centralize path resolution through runtime variables or shared helper expansion instead of repeating absolute literals in Markdown/TOML

**Large monolithic library modules:**
- Issue: Core workflow behavior is concentrated in a few very large files
- Files: `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/init.cjs`, `.codex/get-shit-done/bin/lib/state.cjs`
- Impact: Changes in path handling, init behavior, or state parsing are harder to isolate and review safely
- Fix approach: Split these modules by concern and add focused regression coverage before moving shared helpers

## Known Bugs

**Missing session-start hook target:**
- Symptoms: `.codex/config.toml` registers a `SessionStart` hook command, but the referenced script is absent
- Files: `.codex/config.toml`
- Trigger: Any runtime that tries to execute `node C:/dev/nautilustrader/.codex/hooks/gsd-check-update.js`
- Workaround: Remove or replace the hook declaration before relying on startup-update behavior

## Security Considerations

**Shell execution surface across planning commands:**
- Risk: Many workflows and helpers call out to `git` and shell commands via `execSync` and related helpers
- Files: `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/commands.cjs`, `.codex/get-shit-done/bin/lib/init.cjs`
- Current mitigation: Some path validation and command-specific checks exist, and sensitive file types are explicitly forbidden in mapper guidance
- Recommendations: Add stronger command input validation and automated tests around user-controlled path/argument flows

**Host-managed credentials with optional external APIs:**
- Risk: Search integrations rely on ambient environment variables or `~/.gsd/*_api_key` files outside the repo
- Files: `.codex/get-shit-done/bin/lib/config.cjs`
- Current mitigation: The repo does not store those secrets directly
- Recommendations: Document required secret locations clearly and keep generated docs from ever quoting their values

## Performance Bottlenecks

**Repeated full-tree scans in CLI helpers:**
- Problem: Several commands walk directories recursively and read many files synchronously
- Files: `.codex/get-shit-done/bin/lib/docs.cjs`, `.codex/get-shit-done/bin/lib/commands.cjs`, `.codex/get-shit-done/bin/lib/init.cjs`
- Cause: Simplicity-first synchronous filesystem traversal
- Improvement path: Cache inventory results where possible and narrow scans to relevant directories per command

## Fragile Areas

**Roadmap parsing via regex-heavy Markdown assumptions:**
- Files: `.codex/get-shit-done/bin/lib/roadmap.cjs`
- Why fragile: Parsing depends on exact heading and checklist formats in `ROADMAP.md`
- Safe modification: Preserve existing section formats or add tests before changing regexes and heading conventions
- Test coverage: No automated coverage detected

**Planning-root detection and sub-repo heuristics:**
- Files: `.codex/get-shit-done/bin/lib/core.cjs`
- Why fragile: `findProjectRoot` and related helpers infer ownership from `.planning/`, `.git`, and config structure
- Safe modification: Validate behavior against nested repos and workstreams before changing path logic
- Test coverage: No automated coverage detected

## Scaling Limits

**Workflow growth without package/test infrastructure:**
- Current capacity: The repo can support manual evolution of the current Markdown-and-CommonJS workspace
- Limit: Reliability falls as more skills and workflows are added without automated verification
- Scaling path: Add a package manifest, runnable test suite, and smoke tests for core CLI commands

## Dependencies at Risk

**Node runtime assumptions without explicit version pinning:**
- Risk: The CLI depends on current Node built-ins and behavior but does not pin a version with `.nvmrc`, `package.json`, or equivalent
- Impact: Cross-machine behavior may drift, especially for filesystem and child-process behavior
- Migration plan: Add an explicit runtime version contract and a lightweight local setup script

## Missing Critical Features

**Automated regression coverage for core workflow helpers:**
- Problem: There is no executable test suite for path resolution, config merging, roadmap parsing, or commit guards
- Blocks: Safe refactoring of `.codex/get-shit-done/bin/lib/` and confident portability improvements

## Test Coverage Gaps

**All CLI library modules are effectively untested in-repo:**
- What's not tested: Core helpers and command handlers under `.codex/get-shit-done/bin/lib/`
- Files: `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/config.cjs`, `.codex/get-shit-done/bin/lib/init.cjs`, `.codex/get-shit-done/bin/lib/roadmap.cjs`
- Risk: Parsing or path regressions can break multiple workflows without a fast local signal
- Priority: High

**Runtime integration between config, agents, and hooks:**
- What's not tested: Whether `.codex/config.toml` references valid, existing files and commands
- Files: `.codex/config.toml`, `.codex/agents/*.toml`, `.codex/skills/*/SKILL.md`
- Risk: Missing files like the startup hook can silently degrade expected automation
- Priority: High

---

*Concerns audit: 2026-04-08*
*Update as issues are fixed or new ones are discovered*
