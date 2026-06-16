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

## Branch heuristic: `feat/themes-bulk_targets` and manual subdomains
- Assume this branch is multi-domain, not “just theme work”.
- Manual subdomain additions (single or bulk):
  - Backend: `AddManualSubdomain` API view at `/api/action/subdomain/add/` in `web/api/views.py`.
  - Frontend: `useAddManualSubdomain` hook in `frontend/src/features/subdomains/api/index.ts` and UI in `frontend/src/features/scans/components/SubdomainsTab.tsx`.
- Theme changes usually start in `frontend/src/theme/`, `frontend/src/context/ThemeContext.tsx`, and the affected feature screen. All modals/dialogs in `SubdomainsTab.tsx` must use dynamic `tokens.surface.elevated` (instead of hardcoded dark colors) to support both dark themes and `v3_light`.
- Ignore local ad-hoc helper scripts and `scratch/` artifacts unless the user explicitly asks about them.
