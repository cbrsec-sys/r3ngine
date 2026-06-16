# AGENTS.md

## Purpose
This repository includes AI-oriented onboarding docs so new agents do not need to rescan the full codebase before making useful changes.

## Read This First
1. `documents/PROJECT_SCHEMA.md` — project map, ownership boundaries, workflow inventory, and change-impact guide.
2. `.github/workflows/temporal-scan-flow.md` — source-of-truth scan orchestration diagram.
3. `README.md` — product overview, operational notes, and setup context.
4. `documents/README.md` — index of branch-era architecture docs.
5. `documents/architecture-overview.md` and `documents/scan-pipeline.md` for current durable-workflow behavior.

## Fast Mental Model
- Frontend lives in `frontend/`.
- Backend lives in `web/`.
- Durable orchestration lives in `web/reNgine/temporal_workflows.py`.
- Temporal activities live in `web/reNgine/temporal_activities.py`.
- Tool execution and parsing logic live in `web/reNgine/tasks.py`.
- Scan persistence lives in `web/startScan/`.
- Attack-path and graph intelligence live in `web/apme/` and Tier 7 workflow steps.

## How To Navigate Changes
- API behavior: start in `web/api/`.
- Scan orchestration changes: start in `web/reNgine/temporal_workflows.py`.
- Tool/task execution changes: start in `web/reNgine/tasks.py`.
- Frontend feature changes: start in `frontend/src/features/`.
- Monitoring and schedules: start in `web/targetApp/` and scheduled-scan APIs.

## Branch Context: `feat/themes-bulk_targets` and manual subdomains
- Active local branch may be `dev-latest`; treat it as the freshest local integration line unless the user asks to switch. The older `feat/themes-bulk_targets` context still matters for theme/bulk-target/manual-subdomain work.
- This branch family combines theme refreshes, bulk target support, scan-profile UX, standalone workflows, and manual subdomain additions.
- For manual subdomain additions (single or bulk):
  - Backend: `AddManualSubdomain` API view at `/api/action/subdomain/add/` in `web/api/views.py`.
  - Frontend: Hook `useAddManualSubdomain` in `frontend/src/features/subdomains/api/index.ts` and UI in `frontend/src/features/scans/components/SubdomainsTab.tsx`.
- For theme work, start in `frontend/src/theme/`, `frontend/src/context/ThemeContext.tsx`, and the affected feature page under `frontend/src/features/`.
- Theme contract:
  - Prefer `useThemeTokens()`, `useSemanticColors()`, and helpers from `frontend/src/theme/semanticColors.ts`.
  - Dialog/Menu/Card/Form surfaces should use helpers such as `getDialogPaperSx`, `getMenuPaperSx`, `getSurfaceSx`, and `getFieldSx` rather than hardcoded dark colors.
  - Keep `ThemeContext`, `ThemeSwitcher`, and `Shell/HeaderThemeSwitcher` aligned with `selectableThemes`.
  - Do not add new hardcoded `#...`, `rgb(...)`, or `rgba(...)` UI colors outside the theme layer unless the value is a data/brand swatch with a clear reason.
  - All Dialogs/Modals in `SubdomainsTab.tsx` must use dynamic theme surfaces (for example `tokens.surface.elevated` or `getDialogPaperSx`) instead of `#0a0a0a` so dark themes and `v3_light` both work.
- When the request mentions “themes” plus “targets”, assume there may be cross-cutting UI regressions from shared tokens or shared table components.

## Working Rules For Agents
- Prefer the new documents under `documents/` before reverse-engineering architecture from code.
- Do not modify or rely on ad-hoc local helper scripts such as `fix_colors.py`, `fix_quotes.py`, files under `scratch/`, or similar untracked debugging artifacts unless the user explicitly asks.
- Expect a dirty worktree; avoid reverting user-created helper files or branch-local experiments.
- On this branch, verify whether a change is local to theming, target routing, or workflow orchestration before editing, because many screens share the same tokens and status models.
- Local app services are not expected to start reliably in this workspace. Prefer static checks (`npm run build`, `npm run lint`, TypeScript, Django unit tests) and `npx`-driven one-off tooling when needed instead of assuming a running web stack.

## Important Architecture Notes
- Temporal is the primary orchestration layer; do not assume Celery-era execution flow.
- `PROJECT_SCHEMA.md` and `temporal-scan-flow.md` are the preferred low-token entrypoints for understanding the project.
- Before proposing architectural changes, compare both `MasterScanWorkflow` and `SubScanWorkflow`.
- Prefer targeted file reads over broad repo rescans.
