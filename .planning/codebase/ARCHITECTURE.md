# Architecture

**Analysis Date:** 2026-04-08

## Pattern Overview

**Overall:** Markdown-orchestrated CLI workspace with a Node.js utility core

**Key Characteristics:**
- Workflow behavior is authored as Markdown skills and workflow documents rather than application code alone
- Operational logic is centralized in a single CLI entry point, `.codex/get-shit-done/bin/gsd-tools.cjs`
- State is file-based and rooted in `.planning/`, with `.codex/` acting as the installed tool/runtime bundle

## Layers

**Entry / Dispatch Layer:**
- Purpose: Accept CLI commands and route them to the right module handler
- Location: `.codex/get-shit-done/bin/gsd-tools.cjs`
- Contains: argument parsing, command routing, raw/json output selection
- Depends on: library modules in `.codex/get-shit-done/bin/lib/*.cjs`
- Used by: workflow documents and skills that invoke `node .../gsd-tools.cjs ...`

**Core Utility Layer:**
- Purpose: Provide shared path, IO, git, locking, config-default, and output helpers
- Location: `.codex/get-shit-done/bin/lib/core.cjs`
- Contains: `planningDir`, `findProjectRoot`, `execGit`, `output`, `error`, and common helpers reused across the CLI
- Depends on: Node built-ins plus local model-profile definitions in `.codex/get-shit-done/bin/lib/model-profiles.cjs`
- Used by: nearly every command module in `.codex/get-shit-done/bin/lib/`

**Domain Command Layer:**
- Purpose: Implement focused planning behaviors such as init, config, roadmap, state, docs, verify, and phase operations
- Location: `.codex/get-shit-done/bin/lib/init.cjs`, `.codex/get-shit-done/bin/lib/config.cjs`, `.codex/get-shit-done/bin/lib/roadmap.cjs`, `.codex/get-shit-done/bin/lib/state.cjs`, `.codex/get-shit-done/bin/lib/docs.cjs`
- Contains: feature-specific command handlers and structured JSON emitters
- Depends on: the core utility layer and selected sibling modules
- Used by: `.codex/get-shit-done/bin/gsd-tools.cjs`

## Data Flow

**Workflow Invocation:**

1. The user invokes a skill such as `.codex/skills/gsd-new-project/SKILL.md`.
2. The skill points to a workflow file like `.codex/get-shit-done/workflows/new-project.md`.
3. The workflow shells out to `.codex/get-shit-done/bin/gsd-tools.cjs` for init, config, roadmap, or commit operations.
4. `gsd-tools.cjs` dispatches into a focused module under `.codex/get-shit-done/bin/lib/`.
5. The module reads or writes `.planning/*` artifacts, emits structured output, and may spawn or configure downstream agents through the host runtime.

**State Management:**
- File-based state only
- `.planning/` is the mutable project memory root
- `.codex/` is effectively the tool bundle and source of operational truth for workflows, templates, and agent definitions

## Key Abstractions

**Command Module:**
- Purpose: Encapsulate one area of workflow behavior behind CLI commands
- Examples: `.codex/get-shit-done/bin/lib/init.cjs`, `.codex/get-shit-done/bin/lib/commands.cjs`, `.codex/get-shit-done/bin/lib/template.cjs`
- Pattern: CommonJS module exporting `cmd*` functions collected by the CLI router

**Workflow Document:**
- Purpose: Encode the multi-step orchestration logic that higher-level skills follow
- Examples: `.codex/get-shit-done/workflows/new-project.md`, `.codex/get-shit-done/workflows/map-codebase.md`, `.codex/get-shit-done/workflows/plan-phase.md`
- Pattern: Markdown with structured sections, embedded shell snippets, and file references

**Skill Adapter:**
- Purpose: Bind a user-facing command to a workflow and execution context
- Examples: `.codex/skills/gsd-new-project/SKILL.md`, `.codex/skills/gsd-map-codebase/SKILL.md`
- Pattern: Thin Markdown wrapper around one workflow plus runtime-specific notes

## Entry Points

**CLI Entry:**
- Location: `.codex/get-shit-done/bin/gsd-tools.cjs`
- Triggers: Shell calls from workflows or direct manual execution
- Responsibilities: parse args, call the right `cmd*` handler, and emit raw or JSON output

**Skill Entry:**
- Location: `.codex/skills/*/SKILL.md`
- Triggers: User-invoked skill references in the Codex runtime
- Responsibilities: define invocation semantics, load workflow context, and route control into a workflow file

**Host Runtime Config:**
- Location: `.codex/config.toml`
- Triggers: Codex session startup and agent registration
- Responsibilities: register `gsd-*` agents and declare the `SessionStart` update hook

## Error Handling

**Strategy:** Fail fast for invalid top-level conditions, but use best-effort `try/catch` around optional reads and probes

**Patterns:**
- Hard-stop errors use the shared `error()` helper from `.codex/get-shit-done/bin/lib/core.cjs`
- Optional scans frequently swallow filesystem failures to keep workflows moving, as seen in `.codex/get-shit-done/bin/lib/docs.cjs`, `.codex/get-shit-done/bin/lib/commands.cjs`, and `.codex/get-shit-done/bin/lib/roadmap.cjs`

## Cross-Cutting Concerns

**Logging:** Minimal and synchronous via `fs.writeSync` in `.codex/get-shit-done/bin/lib/core.cjs`

**Validation:** Centralized helper validation plus command-specific parsing in modules such as `.codex/get-shit-done/bin/lib/config.cjs` and `.codex/get-shit-done/bin/lib/roadmap.cjs`

**Authentication:** Delegated to the surrounding Codex host; no in-repo auth layer is implemented

---

*Architecture analysis: 2026-04-08*
*Update when major patterns change*
