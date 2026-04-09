<!-- GSD:project-start source:PROJECT.md -->
## Project

**MGC Backtesting and Optimization System**

A local Windows-based research system for backtesting and parameter optimization of a Micro Gold Futures (MGC) trend-following pullback strategy using `nautilus_trader`. It ingests existing Databento historical files into a Nautilus catalog, runs deterministic backtests, and executes Optuna-based parameter searches through a small CLI with separate `ingest`, `backtest`, and `optimize` commands.

This is a structured Python project for one local user, not a notebook or loose-script workflow. The implementation must follow Nautilus Trader's event-driven architecture, where strategies extend the `Strategy` class and react to engine events rather than iterating vectorized bars in a pandas-style loop.

Always use `nautilus_trader`'s native infrastructure as the foundation. Extend and build on top of what `nautilus_trader` provides natively, never reimplement or work around it. When in doubt, check `nt_docs/` first to see if `nautilus_trader` already handles something before writing custom code.

**Core Value:** Reliable MGC data ingestion and trustworthy event-driven backtests that make optimization results credible enough to act on.

### Constraints

- **Platform**: Windows 11 native with PowerShell - implementation and commands must work in the user's local environment
- **Package Management**: Use `uv` and `uv pip install` only - aligns with the existing environment and user requirement
- **Runtime**: Python 3.13.11 with `nautilus_trader 1.225.0` already installed - compatibility matters for all package and API choices
- **Architecture**: Must follow Nautilus Trader's event-driven `Strategy` model - avoids invalid vectorized backtest design
- **Data Source**: Use only the existing Databento files already available locally - v1 assumes no extra downloads or alternate vendors
- **Execution Model**: Completed 1-minute bars only for signal evaluation - keeps v1 behavior deterministic and bounded
- **Cost Model**: Include approximately `$0.50` commission per side and `1` tick (`$0.10`) slippage per fill from day one - realism matters for trustworthy results
- **Interface**: Small CLI with `ingest`, `backtest`, and `optimize` commands - user wants clean explicit steps without rerunning unnecessary work
- **Outputs**: Results must include summary statistics, ranked optimization output, and saved equity-curve PNGs - these define "done" for v1
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- JavaScript (CommonJS on Node.js) - CLI utilities and library modules under `.codex/get-shit-done/bin/gsd-tools.cjs` and `.codex/get-shit-done/bin/lib/*.cjs`
- Markdown - Workflow definitions, skill adapters, templates, and reference material under `.codex/skills/`, `.codex/get-shit-done/workflows/`, and `.codex/get-shit-done/templates/`
- TOML - Agent and runtime registration in `.codex/config.toml` and `.codex/agents/*.toml`
- JSON - Installed manifest/config data in `.codex/gsd-file-manifest.json` and generated planning config files handled by `.codex/get-shit-done/bin/lib/config.cjs`
## Runtime
- Node.js - Required to execute `.codex/get-shit-done/bin/gsd-tools.cjs` and the `.cjs` modules it dispatches to
- Codex-compatible local workspace - The repo is structured as an installed GSD workspace rooted in `.codex/`, not as a packaged npm application
- Not detected - No `package.json`, `package-lock.json`, `pnpm-lock.yaml`, or `yarn.lock` exists at `C:\dev\nautilustrader`
- Lockfile: missing
## Frameworks
- Custom GSD CLI runtime - `node .codex/get-shit-done/bin/gsd-tools.cjs` routes commands into focused modules such as `.codex/get-shit-done/bin/lib/init.cjs`, `.codex/get-shit-done/bin/lib/state.cjs`, and `.codex/get-shit-done/bin/lib/roadmap.cjs`
- Markdown-driven workflow engine - Skills such as `.codex/skills/gsd-new-project/SKILL.md` point into workflow documents like `.codex/get-shit-done/workflows/new-project.md`
- Not detected - No `jest.config.*`, `vitest.config.*`, `*.test.*`, or `*.spec.*` files were found under `.codex/`
- Node built-ins - Modules rely on `fs`, `path`, `os`, `crypto`, and `child_process` as seen in `.codex/get-shit-done/bin/lib/core.cjs`
- Git CLI - Workflow and commit helpers shell out through functions such as `execGit` and `execSync` in `.codex/get-shit-done/bin/lib/core.cjs` and `.codex/get-shit-done/bin/lib/commands.cjs`
## Key Dependencies
- Node built-in `fs` - Synchronous file IO and directory walking across `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/config.cjs`, and `.codex/get-shit-done/bin/lib/docs.cjs`
- Node built-in `path` - Cross-platform path resolution and `.planning` location logic in `.codex/get-shit-done/bin/lib/core.cjs`
- Node built-in `child_process` - Git execution and shell command delegation in `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/init.cjs`, and `.codex/get-shit-done/bin/lib/commands.cjs`
- Local model-profile registry - `.codex/get-shit-done/bin/lib/model-profiles.cjs` is imported by `.codex/get-shit-done/bin/lib/core.cjs` and `.codex/get-shit-done/bin/lib/config.cjs` to resolve agent models
- Local frontmatter utilities - `.codex/get-shit-done/bin/lib/frontmatter.cjs` is consumed by `.codex/get-shit-done/bin/lib/commands.cjs` and `.codex/get-shit-done/bin/lib/template.cjs`
- Git repository presence - Many workflows assume `git` is available before planning docs are committed
- Codex agent config - `.codex/config.toml` registers all `gsd-*` agents and the `SessionStart` hook
## Configuration
- Primary runtime configuration lives in `.codex/config.toml`
- Per-project planning settings are expected in `.planning/config.json`, created and updated through `.codex/get-shit-done/bin/lib/config.cjs`
- User-level defaults and API-key toggles are inferred from files under `~/.gsd/`, as shown in `.codex/get-shit-done/bin/lib/config.cjs`
- No formal build config detected - there is no `tsconfig.json`, bundler config, or package manifest in the repo root
- Content templates and workflows act as the main authoring assets under `.codex/get-shit-done/templates/` and `.codex/get-shit-done/workflows/`
## Platform Requirements
- Windows-friendly absolute paths are embedded throughout `.codex/config.toml`, `.codex/skills/*/SKILL.md`, and `.codex/get-shit-done/workflows/*.md`
- Node.js and Git must be installed locally for the CLI helpers and planning commits to work
- No separate deployment target is defined; this repo behaves like a local automation/workflow workspace rather than a deployed service
- Artifacts are meant to run from the checked-out filesystem rooted at `C:\dev\nautilustrader`
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Use `.cjs` for Node modules in `.codex/get-shit-done/bin/` and `.codex/get-shit-done/bin/lib/`
- Use lowercase kebab-case for most Markdown workflow/template/reference files such as `.codex/get-shit-done/workflows/new-project.md`
- Use `SKILL.md` for each skill entry under `.codex/skills/<skill-name>/`
- Use paired `gsd-*.md` and `gsd-*.toml` filenames for agent definitions in `.codex/agents/`
- Use `camelCase` for helpers and command handlers, for example `findProjectRoot`, `cmdInitPlanPhase`, and `buildNewProjectConfig` in `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/init.cjs`, and `.codex/get-shit-done/bin/lib/config.cjs`
- Prefix CLI handlers with `cmd` in command modules such as `.codex/get-shit-done/bin/lib/commands.cjs`
- Use `camelCase` for local variables and object fields in `.codex/get-shit-done/bin/lib/*.cjs`
- Use `UPPER_SNAKE_CASE` for module-level constants like `WORKSTREAM_SESSION_ENV_KEYS`, `CONFIG_DEFAULTS`, and `VALID_CONFIG_KEYS`
- No TypeScript types or interfaces are present
- Structured data is represented with plain JavaScript objects and documented through comments or templates
## Code Style
- No formatter config was detected at the repo root
- Favor multi-line block comments for section headers and function docs, as seen throughout `.codex/get-shit-done/bin/lib/core.cjs` and `.codex/get-shit-done/bin/lib/template.cjs`
- Use semicolons consistently in `.cjs` files
- Prefer synchronous filesystem APIs for deterministic CLI behavior
- No ESLint/Biome config was detected
- Consistency is enforced informally through existing file patterns rather than a checked-in linter
## Import Organization
- None detected
- Use relative CommonJS paths such as `require('./lib/core.cjs')` in `.codex/get-shit-done/bin/gsd-tools.cjs`
## Error Handling
- Use the shared `error()` helper from `.codex/get-shit-done/bin/lib/core.cjs` for fatal command failures
- Wrap optional filesystem scans in `try/catch` and continue on failure, especially in `.codex/get-shit-done/bin/lib/docs.cjs`, `.codex/get-shit-done/bin/lib/commands.cjs`, and `.codex/get-shit-done/bin/lib/roadmap.cjs`
- Return structured JSON or raw scalar output through `output()` rather than throwing user-facing strings directly
## Logging
- Emit machine-readable JSON by default through `output()`
- Emit concise human-readable raw strings only when a command explicitly requests `--raw`
- Avoid verbose diagnostic logging in the library modules
## Comments
- Explain purpose and constraints with block comments above helpers or sections
- Document CLI contracts and edge cases, especially where workflows depend on exact behavior
- Avoid inline explanatory noise for obvious assignment statements
- Lightweight JSDoc-style block comments are common for non-trivial helpers in `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/docs.cjs`, and `.codex/get-shit-done/bin/lib/template.cjs`
- Public module exports are usually self-described by function names rather than full typed annotations
## Function Design
## Module Design
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Workflow behavior is authored as Markdown skills and workflow documents rather than application code alone
- Operational logic is centralized in a single CLI entry point, `.codex/get-shit-done/bin/gsd-tools.cjs`
- State is file-based and rooted in `.planning/`, with `.codex/` acting as the installed tool/runtime bundle
## Layers
- Purpose: Accept CLI commands and route them to the right module handler
- Location: `.codex/get-shit-done/bin/gsd-tools.cjs`
- Contains: argument parsing, command routing, raw/json output selection
- Depends on: library modules in `.codex/get-shit-done/bin/lib/*.cjs`
- Used by: workflow documents and skills that invoke `node .../gsd-tools.cjs ...`
- Purpose: Provide shared path, IO, git, locking, config-default, and output helpers
- Location: `.codex/get-shit-done/bin/lib/core.cjs`
- Contains: `planningDir`, `findProjectRoot`, `execGit`, `output`, `error`, and common helpers reused across the CLI
- Depends on: Node built-ins plus local model-profile definitions in `.codex/get-shit-done/bin/lib/model-profiles.cjs`
- Used by: nearly every command module in `.codex/get-shit-done/bin/lib/`
- Purpose: Implement focused planning behaviors such as init, config, roadmap, state, docs, verify, and phase operations
- Location: `.codex/get-shit-done/bin/lib/init.cjs`, `.codex/get-shit-done/bin/lib/config.cjs`, `.codex/get-shit-done/bin/lib/roadmap.cjs`, `.codex/get-shit-done/bin/lib/state.cjs`, `.codex/get-shit-done/bin/lib/docs.cjs`
- Contains: feature-specific command handlers and structured JSON emitters
- Depends on: the core utility layer and selected sibling modules
- Used by: `.codex/get-shit-done/bin/gsd-tools.cjs`
## Data Flow
- File-based state only
- `.planning/` is the mutable project memory root
- `.codex/` is effectively the tool bundle and source of operational truth for workflows, templates, and agent definitions
## Key Abstractions
- Purpose: Encapsulate one area of workflow behavior behind CLI commands
- Examples: `.codex/get-shit-done/bin/lib/init.cjs`, `.codex/get-shit-done/bin/lib/commands.cjs`, `.codex/get-shit-done/bin/lib/template.cjs`
- Pattern: CommonJS module exporting `cmd*` functions collected by the CLI router
- Purpose: Encode the multi-step orchestration logic that higher-level skills follow
- Examples: `.codex/get-shit-done/workflows/new-project.md`, `.codex/get-shit-done/workflows/map-codebase.md`, `.codex/get-shit-done/workflows/plan-phase.md`
- Pattern: Markdown with structured sections, embedded shell snippets, and file references
- Purpose: Bind a user-facing command to a workflow and execution context
- Examples: `.codex/skills/gsd-new-project/SKILL.md`, `.codex/skills/gsd-map-codebase/SKILL.md`
- Pattern: Thin Markdown wrapper around one workflow plus runtime-specific notes
## Entry Points
- Location: `.codex/get-shit-done/bin/gsd-tools.cjs`
- Triggers: Shell calls from workflows or direct manual execution
- Responsibilities: parse args, call the right `cmd*` handler, and emit raw or JSON output
- Location: `.codex/skills/*/SKILL.md`
- Triggers: User-invoked skill references in the Codex runtime
- Responsibilities: define invocation semantics, load workflow context, and route control into a workflow file
- Location: `.codex/config.toml`
- Triggers: Codex session startup and agent registration
- Responsibilities: register `gsd-*` agents and declare the `SessionStart` update hook
## Error Handling
- Hard-stop errors use the shared `error()` helper from `.codex/get-shit-done/bin/lib/core.cjs`
- Optional scans frequently swallow filesystem failures to keep workflows moving, as seen in `.codex/get-shit-done/bin/lib/docs.cjs`, `.codex/get-shit-done/bin/lib/commands.cjs`, and `.codex/get-shit-done/bin/lib/roadmap.cjs`
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
