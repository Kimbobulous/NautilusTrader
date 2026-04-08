# Technology Stack

**Analysis Date:** 2026-04-08

## Languages

**Primary:**
- JavaScript (CommonJS on Node.js) - CLI utilities and library modules under `.codex/get-shit-done/bin/gsd-tools.cjs` and `.codex/get-shit-done/bin/lib/*.cjs`
- Markdown - Workflow definitions, skill adapters, templates, and reference material under `.codex/skills/`, `.codex/get-shit-done/workflows/`, and `.codex/get-shit-done/templates/`

**Secondary:**
- TOML - Agent and runtime registration in `.codex/config.toml` and `.codex/agents/*.toml`
- JSON - Installed manifest/config data in `.codex/gsd-file-manifest.json` and generated planning config files handled by `.codex/get-shit-done/bin/lib/config.cjs`

## Runtime

**Environment:**
- Node.js - Required to execute `.codex/get-shit-done/bin/gsd-tools.cjs` and the `.cjs` modules it dispatches to
- Codex-compatible local workspace - The repo is structured as an installed GSD workspace rooted in `.codex/`, not as a packaged npm application

**Package Manager:**
- Not detected - No `package.json`, `package-lock.json`, `pnpm-lock.yaml`, or `yarn.lock` exists at `C:\dev\nautilustrader`
- Lockfile: missing

## Frameworks

**Core:**
- Custom GSD CLI runtime - `node .codex/get-shit-done/bin/gsd-tools.cjs` routes commands into focused modules such as `.codex/get-shit-done/bin/lib/init.cjs`, `.codex/get-shit-done/bin/lib/state.cjs`, and `.codex/get-shit-done/bin/lib/roadmap.cjs`
- Markdown-driven workflow engine - Skills such as `.codex/skills/gsd-new-project/SKILL.md` point into workflow documents like `.codex/get-shit-done/workflows/new-project.md`

**Testing:**
- Not detected - No `jest.config.*`, `vitest.config.*`, `*.test.*`, or `*.spec.*` files were found under `.codex/`

**Build/Dev:**
- Node built-ins - Modules rely on `fs`, `path`, `os`, `crypto`, and `child_process` as seen in `.codex/get-shit-done/bin/lib/core.cjs`
- Git CLI - Workflow and commit helpers shell out through functions such as `execGit` and `execSync` in `.codex/get-shit-done/bin/lib/core.cjs` and `.codex/get-shit-done/bin/lib/commands.cjs`

## Key Dependencies

**Critical:**
- Node built-in `fs` - Synchronous file IO and directory walking across `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/config.cjs`, and `.codex/get-shit-done/bin/lib/docs.cjs`
- Node built-in `path` - Cross-platform path resolution and `.planning` location logic in `.codex/get-shit-done/bin/lib/core.cjs`
- Node built-in `child_process` - Git execution and shell command delegation in `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/init.cjs`, and `.codex/get-shit-done/bin/lib/commands.cjs`
- Local model-profile registry - `.codex/get-shit-done/bin/lib/model-profiles.cjs` is imported by `.codex/get-shit-done/bin/lib/core.cjs` and `.codex/get-shit-done/bin/lib/config.cjs` to resolve agent models
- Local frontmatter utilities - `.codex/get-shit-done/bin/lib/frontmatter.cjs` is consumed by `.codex/get-shit-done/bin/lib/commands.cjs` and `.codex/get-shit-done/bin/lib/template.cjs`

**Infrastructure:**
- Git repository presence - Many workflows assume `git` is available before planning docs are committed
- Codex agent config - `.codex/config.toml` registers all `gsd-*` agents and the `SessionStart` hook

## Configuration

**Environment:**
- Primary runtime configuration lives in `.codex/config.toml`
- Per-project planning settings are expected in `.planning/config.json`, created and updated through `.codex/get-shit-done/bin/lib/config.cjs`
- User-level defaults and API-key toggles are inferred from files under `~/.gsd/`, as shown in `.codex/get-shit-done/bin/lib/config.cjs`

**Build:**
- No formal build config detected - there is no `tsconfig.json`, bundler config, or package manifest in the repo root
- Content templates and workflows act as the main authoring assets under `.codex/get-shit-done/templates/` and `.codex/get-shit-done/workflows/`

## Platform Requirements

**Development:**
- Windows-friendly absolute paths are embedded throughout `.codex/config.toml`, `.codex/skills/*/SKILL.md`, and `.codex/get-shit-done/workflows/*.md`
- Node.js and Git must be installed locally for the CLI helpers and planning commits to work

**Production:**
- No separate deployment target is defined; this repo behaves like a local automation/workflow workspace rather than a deployed service
- Artifacts are meant to run from the checked-out filesystem rooted at `C:\dev\nautilustrader`

---

*Stack analysis: 2026-04-08*
*Update after major dependency or runtime changes*
