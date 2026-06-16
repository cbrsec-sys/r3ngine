# CLAUDE.md

Start with:
1. `documents/PROJECT_SCHEMA.md`
2. `.github/workflows/temporal-scan-flow.md`
3. `README.md`
4. `documents/README.md`
5. `documents/architecture-overview.md`
6. `documents/scan-pipeline.md`

## Goal
Build a quick, accurate mental model of the repository without a full rescan.

## Key facts
- `frontend/`: React/Vite/TypeScript UI
- `web/api/`: DRF entrypoints
- `web/reNgine/temporal_workflows.py`: durable orchestration
- `web/reNgine/temporal_activities.py`: workflow-to-task bridge
- `web/reNgine/tasks.py`: tool execution, parsing, DB writes
- `web/startScan/`: scan persistence and result models
- `web/apme/`: attack-path modeling and graph intelligence

## Working heuristic
When tracing behavior, follow:
`API view -> workflow starter in tasks.py -> workflow -> activity -> task function -> model write`

## Token-saving rule
Do not broadly scan the repository if the request is about scan flow, architecture, or feature ownership. Use `documents/PROJECT_SCHEMA.md` as the navigation index first.

## Branch heuristic: `dev-latest`, `feat/themes-bulk_targets`, and manual subdomains
- Local `dev-latest` is the freshest integration branch when present/current.
- Assume this branch family is multi-domain, not “just theme work”.
- Manual subdomain additions (single or bulk):
  - Backend: `AddManualSubdomain` API view at `/api/action/subdomain/add/` in `web/api/views.py`.
  - Frontend: `useAddManualSubdomain` hook in `frontend/src/features/subdomains/api/index.ts` and UI in `frontend/src/features/scans/components/SubdomainsTab.tsx`.
- Theme changes usually start in `frontend/src/theme/`, `frontend/src/context/ThemeContext.tsx`, and the affected feature screen.
- Theme contract:
  - Prefer `useThemeTokens()`, `useSemanticColors()`, and helpers from `frontend/src/theme/semanticColors.ts`.
  - Use `getDialogPaperSx`, `getMenuPaperSx`, `getSurfaceSx`, and `getFieldSx` for Dialog/Menu/Card/Form surfaces.
  - Keep selectable themes centralized through `selectableThemes`; do not let header/sidebar theme menus diverge.
  - Avoid new hardcoded `#...`, `rgb(...)`, or `rgba(...)` colors outside `frontend/src/theme/` unless the color is intentionally data/brand-driven.
  - All modals/dialogs in `SubdomainsTab.tsx` must use dynamic theme surfaces to support both dark themes and `v3_light`.
- Ignore local ad-hoc helper scripts and `scratch/` artifacts unless the user explicitly asks about them.

## Local validation
- Do not assume the local web stack starts successfully. Prefer static checks such as `npm run build`, `npm run lint`, targeted TypeScript checks, and Django unit tests.
- `npx` one-off tooling is acceptable when it does not require starting the full stack.
