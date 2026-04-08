# Codebase Structure

**Analysis Date:** 2026-04-08

## Directory Layout

```text
nautilustrader/
|-- .codex/                     # Installed GSD workspace and Codex runtime assets
|   |-- agents/                # Specialist agent prompts and TOML configs
|   |-- get-shit-done/         # Core workflows, templates, references, and CLI code
|   |   |-- bin/              # CLI entry point plus library modules
|   |   |-- contexts/         # Context presets
|   |   |-- references/       # Guidance and reference docs
|   |   |-- templates/        # Markdown templates for generated artifacts
|   |   `-- workflows/        # Multi-step workflow definitions
|   `-- skills/               # User-invokable skill adapters
|-- .git/                      # Local git repo initialized for planning-doc tracking
`-- .planning/                 # Generated planning artifacts, including codebase map
```

## Directory Purposes

**`.codex/`:**
- Purpose: Root of the installed Codex/GSD tool workspace
- Contains: runtime config, agent definitions, skills, and the `get-shit-done` bundle
- Key files: `.codex/config.toml`, `.codex/gsd-file-manifest.json`
- Subdirectories: `agents/`, `get-shit-done/`, `skills/`

**`.codex/agents/`:**
- Purpose: Register specialist agents used by higher-level workflows
- Contains: paired `.md` and `.toml` files such as `.codex/agents/gsd-codebase-mapper.md` and `.codex/agents/gsd-codebase-mapper.toml`
- Key files: `.codex/agents/gsd-roadmapper.md`, `.codex/agents/gsd-executor.toml`

**`.codex/get-shit-done/bin/`:**
- Purpose: CLI entry and supporting library modules
- Contains: `.codex/get-shit-done/bin/gsd-tools.cjs` and `lib/*.cjs`
- Key files: `.codex/get-shit-done/bin/gsd-tools.cjs`, `.codex/get-shit-done/bin/lib/core.cjs`, `.codex/get-shit-done/bin/lib/init.cjs`

**`.codex/get-shit-done/workflows/`:**
- Purpose: Markdown workflow source of truth
- Contains: files like `.codex/get-shit-done/workflows/new-project.md`, `.codex/get-shit-done/workflows/map-codebase.md`, `.codex/get-shit-done/workflows/plan-phase.md`
- Key files: the workflow named after the skill being executed

**`.codex/get-shit-done/templates/`:**
- Purpose: Templates for generated planning documents and codebase docs
- Contains: project, roadmap, state, summary, and `codebase/*.md` templates
- Key files: `.codex/get-shit-done/templates/project.md`, `.codex/get-shit-done/templates/requirements.md`, `.codex/get-shit-done/templates/codebase/structure.md`

**`.codex/skills/`:**
- Purpose: Thin adapters that bind user-facing commands to workflows
- Contains: one directory per skill, each with a `SKILL.md`
- Key files: `.codex/skills/gsd-new-project/SKILL.md`, `.codex/skills/gsd-map-codebase/SKILL.md`

**`.planning/`:**
- Purpose: Mutable planning and execution state generated while using GSD
- Contains: project docs, phase directories, and this codebase map
- Key files: expected artifacts such as `.planning/PROJECT.md`, `.planning/ROADMAP.md`, and `.planning/codebase/*.md`

## Key File Locations

**Entry Points:**
- `.codex/get-shit-done/bin/gsd-tools.cjs`: Main CLI entry point
- `.codex/config.toml`: Runtime/agent registration entry point for Codex
- `.codex/skills/*/SKILL.md`: User-facing skill entry points

**Configuration:**
- `.codex/config.toml`: Agent registration and hook configuration
- `.codex/gsd-file-manifest.json`: Installed asset manifest
- `.planning/config.json`: Project-specific planning config once initialized

**Core Logic:**
- `.codex/get-shit-done/bin/lib/core.cjs`: Shared helpers and path logic
- `.codex/get-shit-done/bin/lib/init.cjs`: Workflow initialization
- `.codex/get-shit-done/bin/lib/state.cjs`: STATE.md parsing and updates
- `.codex/get-shit-done/bin/lib/roadmap.cjs`: ROADMAP parsing and updates

**Testing:**
- No dedicated test directory detected
- No collocated `*.test.*` or `*.spec.*` files detected under `.codex/`

**Documentation:**
- `.codex/get-shit-done/references/*.md`: Reference guidance
- `.codex/get-shit-done/workflows/*.md`: Executable documentation/workflow specs
- `.planning/codebase/*.md`: Generated codebase map for planning use

## Naming Conventions

**Files:**
- `*.cjs` for executable/library Node modules under `.codex/get-shit-done/bin/`
- `SKILL.md` for skill adapter files under `.codex/skills/*/`
- lowercase kebab-case `.md` filenames for most workflows and templates
- uppercase destination docs for generated codebase artifacts such as `STACK.md` and `ARCHITECTURE.md`

**Directories:**
- lowercase kebab-case for most directories such as `.codex/get-shit-done/`
- `gsd-*` prefixes for agent and skill names in `.codex/agents/` and `.codex/skills/`

## Where to Add New Code

**New CLI Feature:**
- Primary code: `.codex/get-shit-done/bin/lib/`
- Command router hookup: `.codex/get-shit-done/bin/gsd-tools.cjs`
- Planning docs for behavior changes: `.codex/get-shit-done/workflows/` and `.codex/get-shit-done/templates/` as needed

**New Skill:**
- Implementation: `.codex/skills/<skill-name>/SKILL.md`
- Workflow backing it: `.codex/get-shit-done/workflows/<workflow-name>.md`
- Agent metadata if specialized: `.codex/agents/gsd-<agent-name>.md` and `.codex/agents/gsd-<agent-name>.toml`

**Utilities:**
- Shared helpers: `.codex/get-shit-done/bin/lib/core.cjs` or a new focused module under `.codex/get-shit-done/bin/lib/`
- New templates: `.codex/get-shit-done/templates/`

## Special Directories

**`.codex/get-shit-done/`:**
- Purpose: Source bundle for the GSD workflow system
- Generated: No
- Committed: Yes

**`.planning/`:**
- Purpose: Local project memory and generated planning artifacts
- Generated: Yes
- Committed: Intended to be committed when `commit_docs` is enabled

**`.git/`:**
- Purpose: Repository metadata for local commits
- Generated: Yes
- Committed: No

---

*Structure analysis: 2026-04-08*
*Update when directory structure changes*
