# Coding Conventions

**Analysis Date:** 2026-04-08

## Naming Patterns

**Files:**
- Use `.cjs` for Node modules in `.codex/get-shit-done/bin/` and `.codex/get-shit-done/bin/lib/`
- Use lowercase kebab-case for most Markdown workflow/template/reference files such as `.codex/get-shit-done/workflows/new-project.md`
- Use `SKILL.md` for each skill entry under `.codex/skills/<skill-name>/`
- Use paired `gsd-*.md` and `gsd-*.toml` filenames for agent definitions in `.codex/agents/`

**Functions:**
- Use `camelCase` for helpers and command handlers, for example `findProjectRoot`, `cmdInitPlanPhase`, and `buildNewProjectConfig` in `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/init.cjs`, and `.codex/get-shit-done/bin/lib/config.cjs`
- Prefix CLI handlers with `cmd` in command modules such as `.codex/get-shit-done/bin/lib/commands.cjs`

**Variables:**
- Use `camelCase` for local variables and object fields in `.codex/get-shit-done/bin/lib/*.cjs`
- Use `UPPER_SNAKE_CASE` for module-level constants like `WORKSTREAM_SESSION_ENV_KEYS`, `CONFIG_DEFAULTS`, and `VALID_CONFIG_KEYS`

**Types:**
- No TypeScript types or interfaces are present
- Structured data is represented with plain JavaScript objects and documented through comments or templates

## Code Style

**Formatting:**
- No formatter config was detected at the repo root
- Favor multi-line block comments for section headers and function docs, as seen throughout `.codex/get-shit-done/bin/lib/core.cjs` and `.codex/get-shit-done/bin/lib/template.cjs`
- Use semicolons consistently in `.cjs` files
- Prefer synchronous filesystem APIs for deterministic CLI behavior

**Linting:**
- No ESLint/Biome config was detected
- Consistency is enforced informally through existing file patterns rather than a checked-in linter

## Import Organization

**Order:**
1. Node built-ins first, usually `fs`, `path`, `os`, `crypto`, or `child_process`
2. Local sibling modules from `.codex/get-shit-done/bin/lib/`
3. Destructured imports from those local modules after direct `require()` bindings

**Path Aliases:**
- None detected
- Use relative CommonJS paths such as `require('./lib/core.cjs')` in `.codex/get-shit-done/bin/gsd-tools.cjs`

## Error Handling

**Patterns:**
- Use the shared `error()` helper from `.codex/get-shit-done/bin/lib/core.cjs` for fatal command failures
- Wrap optional filesystem scans in `try/catch` and continue on failure, especially in `.codex/get-shit-done/bin/lib/docs.cjs`, `.codex/get-shit-done/bin/lib/commands.cjs`, and `.codex/get-shit-done/bin/lib/roadmap.cjs`
- Return structured JSON or raw scalar output through `output()` rather than throwing user-facing strings directly

## Logging

**Framework:** direct stdout/stderr writes via `.codex/get-shit-done/bin/lib/core.cjs`

**Patterns:**
- Emit machine-readable JSON by default through `output()`
- Emit concise human-readable raw strings only when a command explicitly requests `--raw`
- Avoid verbose diagnostic logging in the library modules

## Comments

**When to Comment:**
- Explain purpose and constraints with block comments above helpers or sections
- Document CLI contracts and edge cases, especially where workflows depend on exact behavior
- Avoid inline explanatory noise for obvious assignment statements

**JSDoc/TSDoc:**
- Lightweight JSDoc-style block comments are common for non-trivial helpers in `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/docs.cjs`, and `.codex/get-shit-done/bin/lib/template.cjs`
- Public module exports are usually self-described by function names rather than full typed annotations

## Function Design

**Size:** Functions range from small helpers to very large command handlers; large files such as `.codex/get-shit-done/bin/lib/core.cjs` and `.codex/get-shit-done/bin/lib/init.cjs` group many related helpers in one module

**Parameters:** Prefer explicit positional parameters for CLI handlers, with optional `options = {}` objects for extended behavior as in `.codex/get-shit-done/bin/lib/init.cjs`

**Return Values:** Return plain objects for structured results, then hand them to `output()`; use early returns to short-circuit error or empty states

## Module Design

**Exports:** Use named exports collected in `module.exports = { ... }` at the bottom of each `.cjs` module

**Barrel Files:** No barrel-file layer is used; `.codex/get-shit-done/bin/gsd-tools.cjs` imports modules directly and acts as the central dispatcher

---

*Convention analysis: 2026-04-08*
*Update when patterns change*
