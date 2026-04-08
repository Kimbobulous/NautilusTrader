# External Integrations

**Analysis Date:** 2026-04-08

## APIs & External Services

**LLM Runtime / Agent Host:**
- Codex runtime - Executes skills, developer tools, and agent registration declared in `.codex/config.toml`
  - SDK/Client: Native Codex tool runtime, no local SDK package detected
  - Auth: Managed by the host environment, not by this repo

**Web Search Providers:**
- Optional Brave, Firecrawl, and Exa integrations - Detected by key-file or environment-variable checks in `.codex/get-shit-done/bin/lib/config.cjs`
  - Integration method: Shell-invoked helper commands through `.codex/get-shit-done/bin/gsd-tools.cjs`
  - Auth: `BRAVE_API_KEY`, `FIRECRAWL_API_KEY`, `EXA_API_KEY`, or files under `~/.gsd/`

## Data Storage

**Databases:**
- None detected
  - Connection: Not applicable
  - Client: Not applicable

**File Storage:**
- Local filesystem only
  - Primary workspace content lives under `.codex/`
  - Planning artifacts are generated under `.planning/`

**Caching:**
- No dedicated cache service detected
  - Temporary JSON output can be written into the OS temp directory by `.codex/get-shit-done/bin/lib/core.cjs`

## Authentication & Identity

**Auth Provider:**
- None implemented inside the repo
  - Implementation: Authentication is delegated to the surrounding Codex host runtime

**OAuth Integrations:**
- Not detected

## Monitoring & Observability

**Error Tracking:**
- None detected

**Analytics:**
- None detected

**Logs:**
- Standard output and standard error only
  - `.codex/get-shit-done/bin/lib/core.cjs` writes directly with `fs.writeSync(1, ...)` and `fs.writeSync(2, ...)`

## CI/CD & Deployment

**Hosting:**
- Not detected
  - No `Dockerfile`, `vercel.json`, `netlify.toml`, GitHub workflow, or package-based deploy target exists at the repo root

**CI Pipeline:**
- None detected

## Environment Configuration

**Required env vars:**
- `BRAVE_API_KEY`, `FIRECRAWL_API_KEY`, and `EXA_API_KEY` are optionally consumed by `.codex/get-shit-done/bin/lib/config.cjs`
- Workstream/session detection reads environment keys such as `CODEX_THREAD_ID`, `TERM_SESSION_ID`, `WT_SESSION`, and related session variables in `.codex/get-shit-done/bin/lib/core.cjs`

**Secrets location:**
- Expected outside the repo in process environment variables or `~/.gsd/*_api_key` files
- `.env`-style files are explicitly treated as sensitive by the mapper guidance; none were read during mapping

## Webhooks & Callbacks

**Incoming:**
- Codex `SessionStart` hook declaration in `.codex/config.toml`
  - Command target: `node C:/dev/nautilustrader/.codex/hooks/gsd-check-update.js`
  - Current state: referenced hook target is missing from the workspace

**Outgoing:**
- Git subprocess calls from `.codex/get-shit-done/bin/lib/core.cjs` and `.codex/get-shit-done/bin/lib/commands.cjs`
- Optional web-search helper invocations routed through `.codex/get-shit-done/bin/gsd-tools.cjs`

## Integration Notes

- This repo is primarily self-contained. Most integrations are host-runtime assumptions, local shell commands, and optional API-key-backed search helpers rather than direct application SDKs.
- The most important external dependency to verify before using the workspace is the Codex host configuration in `.codex/config.toml`, because agent registration and the missing hook target both live there.

---

*Integration audit: 2026-04-08*
*Update when adding or removing external services*
