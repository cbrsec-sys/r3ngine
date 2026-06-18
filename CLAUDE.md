# CLAUDE.md
## Current version: 3.6.2

Start with:
1. `README.md`
2. `documents/README.md`
3. `documents/architecture-overview.md`
4. `documents/scan-pipeline.md`
5. `.github/workflows/temporal-scan-flow.md`

Optional local note:
- `documents/PROJECT_SCHEMA.md` can exist as a local untracked project map. Use it if present, but do not rely on it as a tracked source of truth.

## Goal
Build a fast, accurate mental model without rescanning the whole repository.

## Key Facts
- `frontend/`: UI
- `web/api/`: HTTP API
- `web/reNgine/temporal_workflows.py`: orchestration
- `web/reNgine/temporal_activities.py`: workflow bridge
- `web/reNgine/tasks.py`: task execution and parsing
- `web/startScan/`: persistence
- `web/apme/`: graph and attack-path logic

## Working Heuristic
Trace behavior as:
`API view -> workflow starter -> workflow -> activity -> task function -> model write`

## Theme Guidance
- Prefer `useThemeTokens()`, `useSemanticColors()`, and `frontend/src/theme/semanticColors.ts`.
- Keep theme selectors aligned through `selectableThemes`.
- Reuse shared theme helpers for dialogs, menus, cards, and form fields.
- Avoid introducing new hardcoded UI colors outside `frontend/src/theme/`.

## Validation
- Prefer targeted checks over assuming the full stack can start.
- Good defaults: `npx tsc -b`, `npm run lint`, targeted Django tests, and `python3 -m py_compile` for touched backend modules.
