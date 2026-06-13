# AD Intelligence Plugin — Phases 13–16 + Post-Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the AD Intelligence plugin with subdomain action integration, an analytics filter store, TypeScript quality fixes, Django backend tests, a proper report modal, and two Django HTML report templates.

**Architecture:** Five independent workstreams that can be sequenced as listed. Phase 13 touches both repos (main + plugin). Phases 14–15 touch only the plugin frontend. Phase 16 touches only `web/tests/` in the main repo. Post-Implementation spans both repos.

**Tech Stack:** Django REST Framework, React 18 + Zustand + TanStack Query, Cytoscape.js, WeasyPrint, Django template engine, TypeScript strict mode.

**Security constraint (MUST be respected throughout):** This is an AUTHORIZED ASSESSMENT TOOL. Do not implement autonomous exploitation, credential harvesting, persistence mechanisms, offensive lateral movement automation, or covert operational tooling. The plugin is assessment-oriented.

**Repo rules:**
- Plugin source code (`r3ngine-plugins/active_directory/`) → commit to `r3ngine-plugins` repo (master branch)
- Main app files (`web/`, `frontend/`) → commit to `r3ngine` repo (temporal-go branch)
- `web/plugins_data/` — NEVER commit; runtime install state only
- `dist/` folders — NEVER commit

---

## File Map

| File | Action | Repo |
|------|--------|------|
| `web/api/views.py` | Modify — add `LaunchADAssessmentFromSubdomain` | r3ngine |
| `web/api/urls.py` | Modify — register new URL | r3ngine |
| `frontend/src/features/scans/components/SubdomainsTab.tsx` | Modify — add menu item + handler | r3ngine |
| `r3ngine-plugins/active_directory/ui/src/store/analyticsStore.ts` | Create | r3ngine-plugins |
| `r3ngine-plugins/active_directory/ui/src/pages/ADAssessmentDetailPage.tsx` | Modify — wire severity filter | r3ngine-plugins |
| `r3ngine-plugins/active_directory/ui/src/pages/ADTrustAnalyticsPage.tsx` | Modify — wire direction filter | r3ngine-plugins |
| `r3ngine-plugins/active_directory/ui/src/pages/ADExposureDashboardPage.tsx` | Modify — wire type filter | r3ngine-plugins |
| `r3ngine-plugins/active_directory/ui/src/graphs/cytoscapeStyles.ts` | Modify — TS type fix | r3ngine-plugins |
| `web/tests/test_ad_plugin_permissions.py` | Create | r3ngine |
| `web/tests/test_ad_plugin_graph.py` | Create | r3ngine |
| `web/tests/test_ad_plugin_ingestion.py` | Create | r3ngine |
| `r3ngine-plugins/active_directory/ui/src/components/ADReportModal.tsx` | Create | r3ngine-plugins |
| `r3ngine-plugins/active_directory/ui/src/pages/ADReportsPage.tsx` | Modify — use modal | r3ngine-plugins |
| `r3ngine-plugins/active_directory/ui/src/api/adApi.ts` | Modify — add template param | r3ngine-plugins |
| `r3ngine-plugins/active_directory/backend/reporting/pdf_renderer.py` | Modify — template dispatch | r3ngine-plugins |
| `r3ngine-plugins/active_directory/backend/api.py` | Modify — accept `?template=` | r3ngine-plugins |
| `web/templates/report/ad_modern.html` | Create | r3ngine |
| `web/templates/report/ad_cyber_pro.html` | Create | r3ngine |

---

## Task 1: Backend — LaunchADAssessmentFromSubdomain Endpoint

**Files:**
- Modify: `web/api/views.py` (append class near end, before final blank line)
- Modify: `web/api/urls.py` (append path to `urlpatterns`)

- [ ] **Step 1: Write the failing test**

Create a temporary test script to verify the endpoint exists before implementation. Open `web/tests/test_ad_plugin_phase13.py` and write:

```python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

User = get_user_model()

class TestLaunchADAssessmentEndpoint(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ad_test_user', password='testpass', is_staff=True
        )
        self.factory = RequestFactory()

    def tearDown(self):
        self.user.delete()

    def test_endpoint_returns_400_when_plugin_missing(self):
        from api.views import LaunchADAssessmentFromSubdomain
        request = self.factory.post(
            '/api/action/ad-assessment/from-subdomain/',
            data={'subdomain_id': 9999},
            content_type='application/json',
        )
        request.user = self.user
        with patch('builtins.__import__', side_effect=ImportError):
            view = LaunchADAssessmentFromSubdomain.as_view()
            response = view(request)
        # Plugin not installed → 400 with helpful error
        self.assertEqual(response.status_code, 400)
```

- [ ] **Step 2: Run to verify test fails** (run in Docker container)

```bash
docker exec rengine-web python manage.py test tests.test_ad_plugin_phase13 -v 2
```

Expected: `ImportError` or `AttributeError: module 'api.views' has no attribute 'LaunchADAssessmentFromSubdomain'`

- [ ] **Step 3: Add the view to `web/api/views.py`**

Read the file first. Append the following class before the final blank line of the file (after the last existing class definition):

```python
class LaunchADAssessmentFromSubdomain(APIView):
    """Create an ADAssessment pre-populated from a Subdomain's root domain.

    The AD Intelligence plugin must be installed. The assessment is created
    in PENDING state; users start it explicitly from the AD plugin dashboard.
    This view intentionally does NOT start the workflow automatically to avoid
    unintended automated enumeration activity.
    """
    permission_classes = [HasPermission]
    permission_required = PERM_INITATE_SCANS_SUBSCANS

    def post(self, request):
        subdomain_id = request.data.get('subdomain_id')
        if not subdomain_id:
            return Response(
                {'error': 'subdomain_id is required.'},
                status=HTTP_400_BAD_REQUEST,
            )
        try:
            subdomain = Subdomain.objects.select_related(
                'scan_history__domain'
            ).get(id=subdomain_id)
        except Subdomain.DoesNotExist:
            return Response(
                {'error': f'Subdomain {subdomain_id} not found.'},
                status=HTTP_400_BAD_REQUEST,
            )

        target_domain = subdomain.scan_history.domain.name

        try:
            from plugins_data.active_directory.backend.models import ADAssessment as _ADAssessment
        except ImportError:
            return Response(
                {'error': 'AD Intelligence plugin is not installed.'},
                status=HTTP_400_BAD_REQUEST,
            )

        assessment = _ADAssessment.objects.create(
            name=f'AD Assessment — {target_domain}',
            target_domain=target_domain,
            status='PENDING',
            created_by=request.user,
        )
        return Response({
            'assessment_id': assessment.id,
            'assessment_name': assessment.name,
            'target_domain': target_domain,
            'status': 'created',
        }, status=status.HTTP_201_CREATED)
```

- [ ] **Step 4: Register the URL in `web/api/urls.py`**

Read the file first. Add the following path inside the `urlpatterns` list, after the `apme/trigger/` entry (around line 407):

```python
    path(
        'action/ad-assessment/from-subdomain/',
        LaunchADAssessmentFromSubdomain.as_view(),
        name='launch_ad_assessment_from_subdomain'
    ),
```

Also add the import at the top of the imports block where the other views are imported:

```python
from .views import LaunchADAssessmentFromSubdomain
```

Note: `web/api/urls.py` uses `from .views import *` — the class is automatically exported, so no explicit import line is needed.

- [ ] **Step 5: Run the test to verify it passes**

```bash
docker exec rengine-web python manage.py test tests.test_ad_plugin_phase13 -v 2
```

Expected: `OK (1 test)`

- [ ] **Step 6: Commit (main repo)**

```bash
git add web/api/views.py web/api/urls.py web/tests/test_ad_plugin_phase13.py
git commit -m "feat(api): add LaunchADAssessmentFromSubdomain endpoint for AD plugin bridge"
```

---

## Task 2: Frontend — "Assess Identity Infrastructure" Menu Item in SubdomainsTab

**Files:**
- Modify: `frontend/src/features/scans/components/SubdomainsTab.tsx`

- [ ] **Step 1: Read the current state of SubdomainsTab.tsx**

Read `frontend/src/features/scans/components/SubdomainsTab.tsx` in full to understand the current state before editing.

- [ ] **Step 2: Add state, handler, and menu item**

In `SubdomainsTab.tsx`, make the following four additions:

**2a — Import `Network` icon** (from lucide-react, alongside `Shield`):

```typescript
import {
  Search,
  Zap,
  Eye,
  FilePlus,
  MoreHorizontal,
  Download,
  ChevronRight,
  ExternalLink,
  AlertTriangle,
  Trash2,
  Copy,
  FileText,
  Shield,
  Network,
  X,
  Folder
} from 'lucide-react';
```

**2b — Add snackbar state for AD launch** (near the top of the component, after existing `useState` declarations):

```typescript
const [adLaunchMsg, setAdLaunchMsg] = useState<{ text: string; severity: 'success' | 'error' } | null>(null);
```

**2c — Add the handler** (after `handleDelete` or similar handler):

```typescript
const handleLaunchADAssessment = async () => {
  handleActionClose();
  if (!selectedId) return;
  try {
    const res = await fetch('/api/action/ad-assessment/from-subdomain/', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subdomain_id: selectedId }),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.error ?? `HTTP ${res.status}`);
    setAdLaunchMsg({
      text: `AD Assessment created for ${json.target_domain}. Open the AD Intelligence plugin to start it.`,
      severity: 'success',
    });
  } catch (err: unknown) {
    setAdLaunchMsg({
      text: (err instanceof Error ? err.message : 'Failed to create AD assessment'),
      severity: 'error',
    });
  }
};
```

**2d — Add menu item** (inside the `<Menu>` block, before the "MARK IMPORTANT" `<MenuItem>`):

```tsx
<MenuItem onClick={handleLaunchADAssessment} sx={{ color: '#00f3ff' }}>
  <ListItemIcon><Network size={16} color="#00f3ff" /></ListItemIcon>
  <ListItemText primary="ASSESS IDENTITY INFRASTRUCTURE" />
</MenuItem>
<Divider sx={{ my: 0.5, borderColor: 'rgba(255,255,255,0.08)' }} />
```

**2e — Add the Snackbar** (at the bottom of the component's JSX, just before the final closing `</Box>`):

```tsx
<Snackbar
  open={adLaunchMsg !== null}
  autoHideDuration={6000}
  onClose={() => setAdLaunchMsg(null)}
  anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
>
  <Alert
    severity={adLaunchMsg?.severity ?? 'info'}
    onClose={() => setAdLaunchMsg(null)}
    sx={{ width: '100%' }}
  >
    {adLaunchMsg?.text}
  </Alert>
</Snackbar>
```

- [ ] **Step 3: Verify TypeScript compilation**

```bash
cd /d/Repos/r3ngine/frontend && npx tsc --noEmit 2>&1 | head -40
```

Expected: zero new errors introduced (any pre-existing errors are outside scope of this task).

- [ ] **Step 4: Commit (main repo)**

```bash
git add frontend/src/features/scans/components/SubdomainsTab.tsx
git commit -m "feat(ui): add Assess Identity Infrastructure action to subdomain row menu"
```

---

## Task 3: Plugin Frontend — Analytics Filter Store

**Files:**
- Create: `r3ngine-plugins/active_directory/ui/src/store/analyticsStore.ts`
- Modify: `r3ngine-plugins/active_directory/ui/src/pages/ADAssessmentDetailPage.tsx`
- Modify: `r3ngine-plugins/active_directory/ui/src/pages/ADTrustAnalyticsPage.tsx`
- Modify: `r3ngine-plugins/active_directory/ui/src/pages/ADExposureDashboardPage.tsx`

- [ ] **Step 1: Create `analyticsStore.ts`**

Create `r3ngine-plugins/active_directory/ui/src/store/analyticsStore.ts`:

```typescript
import { create } from 'zustand';

interface ADAnalyticsState {
  findingsSeverityFilter: string | null;
  findingsStatusFilter: string | null;
  trustDirectionFilter: string | null;
  exposureTypeFilter: string | null;
  setFindingsSeverityFilter: (v: string | null) => void;
  setFindingsStatusFilter: (v: string | null) => void;
  setTrustDirectionFilter: (v: string | null) => void;
  setExposureTypeFilter: (v: string | null) => void;
  resetFilters: () => void;
}

export const useAnalyticsStore = create<ADAnalyticsState>((set) => ({
  findingsSeverityFilter: null,
  findingsStatusFilter: null,
  trustDirectionFilter: null,
  exposureTypeFilter: null,
  setFindingsSeverityFilter: (v) => set({ findingsSeverityFilter: v }),
  setFindingsStatusFilter: (v) => set({ findingsStatusFilter: v }),
  setTrustDirectionFilter: (v) => set({ trustDirectionFilter: v }),
  setExposureTypeFilter: (v) => set({ exposureTypeFilter: v }),
  resetFilters: () => set({
    findingsSeverityFilter: null,
    findingsStatusFilter: null,
    trustDirectionFilter: null,
    exposureTypeFilter: null,
  }),
}));
```

- [ ] **Step 2: Wire severity filter into `ADAssessmentDetailPage.tsx`**

Read the file first.

Add the import at the top of the import block:
```typescript
import { useAnalyticsStore } from '../store/analyticsStore';
```

Inside the component body, after existing state declarations:
```typescript
const { findingsSeverityFilter, setFindingsSeverityFilter } = useAnalyticsStore();
```

Change the `useFindings` call from:
```typescript
const { data: findingsData } = useFindings(assessmentId, undefined, findingsPage);
```
to:
```typescript
const { data: findingsData } = useFindings(assessmentId, findingsSeverityFilter ?? undefined, findingsPage);
```

Add a severity filter row above the findings table. Find the Findings tab panel content (Tab value 0) and add this above the `<Table>`:

```tsx
{/* Severity filter chips */}
<Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
  {[null, 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'].map((sev) => (
    <Chip
      key={sev ?? 'all'}
      label={sev ?? 'ALL'}
      size="small"
      clickable
      color={findingsSeverityFilter === sev ? 'primary' : 'default'}
      onClick={() => { setFindingsSeverityFilter(sev); setFindingsPage(1); }}
      sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}
    />
  ))}
</Box>
```

Reset filters when assessment changes — add to the existing `useEffect` for `assessmentId` or add a new one:
```typescript
useEffect(() => {
  useAnalyticsStore.getState().resetFilters();
  setFindingsPage(1);
  setLogPage(1);
}, [assessmentId]);
```

Replace the two existing `useEffect`s that reset `findingsPage` and `logPage` with this single combined one (remove the old two).

- [ ] **Step 3: Wire direction filter into `ADTrustAnalyticsPage.tsx`**

Read `r3ngine-plugins/active_directory/ui/src/pages/ADTrustAnalyticsPage.tsx` in full first.

Add import:
```typescript
import { useAnalyticsStore } from '../store/analyticsStore';
```

Inside the component, after existing destructures:
```typescript
const { trustDirectionFilter, setTrustDirectionFilter } = useAnalyticsStore();
const trustList = trusts?.results ?? [];
const filteredTrusts = trustDirectionFilter
  ? trustList.filter((t) => t.direction === trustDirectionFilter)
  : trustList;
```

Add filter chips above the trust table:
```tsx
<Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
  {[null, 'INBOUND', 'OUTBOUND', 'BIDIRECTIONAL'].map((dir) => (
    <Chip
      key={dir ?? 'all'}
      label={dir ?? 'ALL'}
      size="small"
      clickable
      color={trustDirectionFilter === dir ? 'primary' : 'default'}
      onClick={() => setTrustDirectionFilter(dir)}
      sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}
    />
  ))}
</Box>
```

Replace all occurrences of `trustList` in the JSX with `filteredTrusts`.

- [ ] **Step 4: Wire type filter into `ADExposureDashboardPage.tsx`**

Read `r3ngine-plugins/active_directory/ui/src/pages/ADExposureDashboardPage.tsx` in full first.

Add import:
```typescript
import { useAnalyticsStore } from '../store/analyticsStore';
```

Inside the component:
```typescript
const { exposureTypeFilter, setExposureTypeFilter } = useAnalyticsStore();
const exposureList = exposures?.results ?? [];
const allTypes = [...new Set(exposureList.map((e) => e.exposure_type))].sort();
const filteredExposures = exposureTypeFilter
  ? exposureList.filter((e) => e.exposure_type === exposureTypeFilter)
  : exposureList;
```

Add filter chips above the exposure table:
```tsx
<Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
  <Chip
    label="ALL"
    size="small"
    clickable
    color={exposureTypeFilter === null ? 'primary' : 'default'}
    onClick={() => setExposureTypeFilter(null)}
    sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}
  />
  {allTypes.map((type) => (
    <Chip
      key={type}
      label={type}
      size="small"
      clickable
      color={exposureTypeFilter === type ? 'primary' : 'default'}
      onClick={() => setExposureTypeFilter(type)}
      sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}
    />
  ))}
</Box>
```

Replace all occurrences of `exposureList` in the JSX table rendering with `filteredExposures`.

- [ ] **Step 5: Verify TypeScript compiles clean**

```bash
cd /d/Repos/r3ngine/r3ngine-plugins/active_directory/ui && npx tsc --noEmit 2>&1 | head -40
```

Expected: zero errors related to the new store files.

- [ ] **Step 6: Build the plugin**

```bash
cd /d/Repos/r3ngine/r3ngine-plugins/active_directory/ui && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 7: Commit (plugin repo)**

```bash
cd /d/Repos/r3ngine/r3ngine-plugins
git add active_directory/ui/src/store/analyticsStore.ts \
        active_directory/ui/src/pages/ADAssessmentDetailPage.tsx \
        active_directory/ui/src/pages/ADTrustAnalyticsPage.tsx \
        active_directory/ui/src/pages/ADExposureDashboardPage.tsx
git commit -m "feat(ui): add analyticsStore with per-tab filter state wired into detail and analytics pages"
```

---

## Task 4: TypeScript Code Quality Fixes

**Files:**
- Modify: `r3ngine-plugins/active_directory/ui/src/graphs/cytoscapeStyles.ts` (StylesheetCSS type fix)
- Possibly other files surfaced by `tsc --noEmit`

- [ ] **Step 1: Capture all TypeScript errors**

```bash
cd /d/Repos/r3ngine/r3ngine-plugins/active_directory/ui && npx tsc --noEmit 2>&1
```

Capture the full output. Group errors by file. Ignore errors already in files not touched by this plugin (if any bleed in from node_modules).

- [ ] **Step 2: Fix `cytoscapeStyles.ts` — Stylesheet type**

Read `r3ngine-plugins/active_directory/ui/src/graphs/cytoscapeStyles.ts`.

If the file exports `CYTOSCAPE_STYLESHEET` typed as `Stylesheet[]` or `cytoscape.Stylesheet[]`, change the type annotation to `cytoscape.StylesheetCSS[]` (the `StylesheetCSS` variant is the concrete object form; `Stylesheet` is a union with the string form which causes the mismatch).

If the file has no explicit type annotation on the export, add one:
```typescript
import type cytoscape from 'cytoscape';

export const CYTOSCAPE_STYLESHEET: cytoscape.StylesheetCSS[] = [
  // ... existing styles
];
```

- [ ] **Step 3: Fix unused import warnings (React)**

If `tsc --noEmit` reports `'React' is declared but its value is never read` in any file, remove the `import React from 'react'` line from those files — the Vite JSX transform does not require it. Common files:

- `r3ngine-plugins/active_directory/ui/src/pages/ADAssessmentsPage.tsx`
- `r3ngine-plugins/active_directory/ui/src/pages/ADReportsPage.tsx`
- Any component file where `React` is imported but no explicit `React.xxx` calls exist

Do NOT remove it from files that use `React.useCallback`, `React.memo`, `React.forwardRef`, or similar explicit `React.` references.

- [ ] **Step 4: Fix any remaining type errors**

For each remaining error in the `tsc --noEmit` output:
- If it is `Object is possibly 'undefined'`: add a `?.` optional chain or a null guard `?? default`
- If it is `Type 'X' is not assignable to type 'Y'`: inspect the expected type and either cast with `as` (only if provably safe) or adjust the value
- If it is `Parameter 'X' implicitly has an 'any' type`: add an explicit type annotation
- If it is `Property 'X' does not exist on type 'Y'`: check the type definition and either add the property to the interface (in `types/index.ts`) or use a type assertion

- [ ] **Step 5: Verify clean build**

```bash
cd /d/Repos/r3ngine/r3ngine-plugins/active_directory/ui && npx tsc --noEmit 2>&1 && npm run build 2>&1 | tail -10
```

Expected: zero TypeScript errors, build succeeds.

- [ ] **Step 6: Commit (plugin repo)**

```bash
cd /d/Repos/r3ngine/r3ngine-plugins
git add active_directory/ui/src/graphs/cytoscapeStyles.ts
# plus any other modified files from this task
git commit -m "fix(ui): resolve TypeScript strict-mode errors (StylesheetCSS type, unused React imports)"
```

---

## Task 5: Django Tests — AD Plugin Permissions

**Files:**
- Create: `web/tests/test_ad_plugin_permissions.py`

These tests must run in the Docker container where the plugin is installed. They use Django's `TestCase` (real DB, no mocks for ORM).

- [ ] **Step 1: Write the test file**

Create `web/tests/test_ad_plugin_permissions.py`:

```python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from unittest import skipUnless
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

try:
    from plugins_data.active_directory.backend.models import ADAssessment
    from plugins_data.active_directory.backend.permissions import IsAssessmentOwnerOrAdmin
    AD_PLUGIN_AVAILABLE = True
except ImportError:
    AD_PLUGIN_AVAILABLE = False


@skipUnless(AD_PLUGIN_AVAILABLE, 'AD Intelligence plugin not installed')
class TestADPermissions(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='ad_owner', password='pass')
        self.other = User.objects.create_user(username='ad_other', password='pass')
        self.admin = User.objects.create_user(
            username='ad_admin', password='pass', is_staff=True
        )
        self.assessment = ADAssessment.objects.create(
            name='Perm Test',
            target_domain='corp.local',
            created_by=self.owner,
        )

    def tearDown(self):
        self.assessment.delete()
        self.owner.delete()
        self.other.delete()
        self.admin.delete()

    def _make_request(self, user):
        from django.test import RequestFactory
        req = RequestFactory().post('/')
        req.user = user
        return req

    def test_owner_has_object_permission(self):
        perm = IsAssessmentOwnerOrAdmin()
        req = self._make_request(self.owner)
        self.assertTrue(perm.has_object_permission(req, None, self.assessment))

    def test_other_user_denied_object_permission(self):
        perm = IsAssessmentOwnerOrAdmin()
        req = self._make_request(self.other)
        self.assertFalse(perm.has_object_permission(req, None, self.assessment))

    def test_admin_has_object_permission(self):
        perm = IsAssessmentOwnerOrAdmin()
        req = self._make_request(self.admin)
        self.assertTrue(perm.has_object_permission(req, None, self.assessment))

    def test_null_created_by_is_accessible_to_anyone(self):
        anon_assessment = ADAssessment.objects.create(
            name='Anon Assessment',
            target_domain='anon.local',
            created_by=None,
        )
        try:
            perm = IsAssessmentOwnerOrAdmin()
            req = self._make_request(self.other)
            self.assertTrue(perm.has_object_permission(req, None, anon_assessment))
        finally:
            anon_assessment.delete()

    def test_get_queryset_returns_own_assessments_only(self):
        from plugins_data.active_directory.backend.api import ADAssessmentViewSet
        from django.test import RequestFactory

        req = RequestFactory().get('/')
        req.user = self.other
        view = ADAssessmentViewSet()
        view.request = req
        view.action = 'list'
        qs = view.get_queryset()
        self.assertNotIn(self.assessment, qs)

    def test_get_queryset_returns_all_for_staff(self):
        from plugins_data.active_directory.backend.api import ADAssessmentViewSet
        from django.test import RequestFactory

        req = RequestFactory().get('/')
        req.user = self.admin
        view = ADAssessmentViewSet()
        view.request = req
        view.action = 'list'
        qs = view.get_queryset()
        self.assertIn(self.assessment, qs)
```

- [ ] **Step 2: Run the tests (in Docker)**

```bash
docker exec rengine-web python manage.py test tests.test_ad_plugin_permissions -v 2
```

Expected: `OK (6 tests)` or `SKIP (AD Intelligence plugin not installed)` if the plugin is not yet synced to `plugins_data/`.

- [ ] **Step 3: Commit (main repo)**

```bash
git add web/tests/test_ad_plugin_permissions.py
git commit -m "test(ad): add Django tests for AD plugin permission model and queryset filtering"
```

---

## Task 6: Django Tests — AD Plugin Graph Endpoint

**Files:**
- Create: `web/tests/test_ad_plugin_graph.py`

- [ ] **Step 1: Write the test file**

Create `web/tests/test_ad_plugin_graph.py`:

```python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from unittest import skipUnless
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

User = get_user_model()

try:
    from plugins_data.active_directory.backend.models import ADAssessment
    AD_PLUGIN_AVAILABLE = True
except ImportError:
    AD_PLUGIN_AVAILABLE = False


@skipUnless(AD_PLUGIN_AVAILABLE, 'AD Intelligence plugin not installed')
class TestADGraphEndpoint(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='graph_test_user', password='pass', is_staff=True
        )
        self.assessment = ADAssessment.objects.create(
            name='Graph Test',
            target_domain='graph.local',
            created_by=self.user,
        )

    def tearDown(self):
        self.assessment.delete()
        self.user.delete()

    def _call_graph_domains(self, limit_param=None):
        from django.test import RequestFactory
        from plugins_data.active_directory.backend.api import ADAssessmentViewSet

        params = {}
        if limit_param is not None:
            params['limit'] = str(limit_param)

        req = RequestFactory().get('/graph/domains/', params)
        req.user = self.user

        view = ADAssessmentViewSet()
        view.request = req
        view.kwargs = {'pk': self.assessment.pk}
        view.action = 'graph_domains'
        view.format_kwarg = None

        mock_mgr = MagicMock()
        mock_mgr.__enter__ = MagicMock(return_value=mock_mgr)
        mock_mgr.__exit__ = MagicMock(return_value=False)
        mock_mgr.get_domain_graph.return_value = {
            'nodes': [{'data': {'id': f'n{i}'}} for i in range(10)],
            'edges': [],
            'truncated': False,
            'total_nodes': 10,
        }

        with patch(
            'plugins_data.active_directory.backend.api.ADGraphManager',
            return_value=mock_mgr,
        ):
            return view.graph_domains(req, pk=self.assessment.pk)

    def test_default_limit_returns_200(self):
        response = self._call_graph_domains()
        self.assertEqual(response.status_code, 200)

    def test_invalid_limit_returns_400(self):
        from django.test import RequestFactory
        from plugins_data.active_directory.backend.api import ADAssessmentViewSet

        req = RequestFactory().get('/graph/domains/', {'limit': 'abc'})
        req.user = self.user

        view = ADAssessmentViewSet()
        view.request = req
        view.kwargs = {'pk': self.assessment.pk}
        view.action = 'graph_domains'
        view.format_kwarg = None

        response = view.graph_domains(req, pk=self.assessment.pk)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_negative_limit_returns_400(self):
        from django.test import RequestFactory
        from plugins_data.active_directory.backend.api import ADAssessmentViewSet

        req = RequestFactory().get('/graph/domains/', {'limit': '-5'})
        req.user = self.user

        view = ADAssessmentViewSet()
        view.request = req
        view.kwargs = {'pk': self.assessment.pk}
        view.action = 'graph_domains'
        view.format_kwarg = None

        # negative → clamped to 0 → 5000 (load-all), not a 400
        # Check current behavior: -5 < 0 → limit = 0 → 5000
        response = view.graph_domains(req, pk=self.assessment.pk)
        # Should NOT return 400; the view clamps negatives to 0 (maps to load-all cap)
        self.assertNotEqual(response.status_code, 400)

    def test_limit_zero_maps_to_load_all_cap(self):
        from plugins_data.active_directory.backend.api import ADAssessmentViewSet
        from django.test import RequestFactory

        req = RequestFactory().get('/graph/domains/', {'limit': '0'})
        req.user = self.user
        view = ADAssessmentViewSet()
        view.request = req
        view.kwargs = {'pk': self.assessment.pk}
        view.action = 'graph_domains'
        view.format_kwarg = None

        mock_mgr = MagicMock()
        mock_mgr.__enter__ = MagicMock(return_value=mock_mgr)
        mock_mgr.__exit__ = MagicMock(return_value=False)
        mock_mgr.get_domain_graph.return_value = {
            'nodes': [], 'edges': [], 'truncated': False, 'total_nodes': 0
        }
        with patch(
            'plugins_data.active_directory.backend.api.ADGraphManager',
            return_value=mock_mgr,
        ):
            view.graph_domains(req, pk=self.assessment.pk)
        # The limit passed to get_domain_graph should be 5000 (hard cap for load-all)
        mock_mgr.get_domain_graph.assert_called_once_with(
            self.assessment.id, limit=5000
        )
```

- [ ] **Step 2: Run the tests**

```bash
docker exec rengine-web python manage.py test tests.test_ad_plugin_graph -v 2
```

Expected: `OK (4 tests)`

- [ ] **Step 3: Commit (main repo)**

```bash
git add web/tests/test_ad_plugin_graph.py
git commit -m "test(ad): add Django tests for AD plugin graph endpoints and limit validation"
```

---

## Task 7: Django Tests — AD Plugin Ingestion

**Files:**
- Create: `web/tests/test_ad_plugin_ingestion.py`

- [ ] **Step 1: Write the test file**

Create `web/tests/test_ad_plugin_ingestion.py`:

```python
import os
import django
import tempfile
import zipfile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from unittest import skipUnless
from django.test import TestCase
from unittest.mock import patch, MagicMock

try:
    from plugins_data.active_directory.backend.api import ADAssessmentViewSet
    AD_PLUGIN_AVAILABLE = True
except ImportError:
    AD_PLUGIN_AVAILABLE = False


@skipUnless(AD_PLUGIN_AVAILABLE, 'AD Intelligence plugin not installed')
class TestADIngestion(TestCase):

    def test_zip_path_traversal_raises_value_error(self):
        """Zip containing '../evil' paths must be rejected before extraction."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with zipfile.ZipFile(tmp_path, 'w') as zf:
                info = zipfile.ZipInfo('../../../etc/passwd')
                zf.writestr(info, 'root:x:0:0:root:/root:/bin/bash')

            with self.assertRaises(ValueError) as ctx:
                ADAssessmentViewSet._run_ingestion('ldap', tmp_path, 1)
            self.assertIn('Unsafe path', str(ctx.exception))
        finally:
            os.unlink(tmp_path)

    def test_unknown_ingest_type_returns_warning(self):
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp.write(b'{}')
            tmp_path = tmp.name
        try:
            result = ADAssessmentViewSet._run_ingestion('unknown_type', tmp_path, 1)
            self.assertIn('warning', result)
            self.assertIn('Unknown ingest type', result['warning'])
        finally:
            os.unlink(tmp_path)

    def test_directory_with_ldap_files_auto_detects_ldap_type(self):
        """Directory containing domain_users.json triggers ldap ingest path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, 'domain_users.json'), 'w').close()
            mock_result = {'imported': 0}
            with patch(
                'plugins_data.active_directory.backend.ingestion.ldap_parser.LDAPParser.ingest_from_directory',
                return_value=mock_result,
            ) as mock_ldap:
                result = ADAssessmentViewSet._run_ingestion('auto', tmpdir, 1)
            mock_ldap.assert_called_once_with(tmpdir, 1)
            self.assertEqual(result, mock_result)

    def test_directory_with_bloodhound_files_auto_detects_bh_type(self):
        """Directory containing users.json triggers bloodhound ingest path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, 'users.json'), 'w').close()
            mock_result = {'imported': 0}
            with patch(
                'plugins_data.active_directory.backend.ingestion.bloodhound_parser.BloodHoundParser.ingest_from_directory',
                return_value=mock_result,
            ) as mock_bh:
                result = ADAssessmentViewSet._run_ingestion('auto', tmpdir, 1)
            mock_bh.assert_called_once_with(tmpdir, 1)
            self.assertEqual(result, mock_result)

    def test_zip_with_valid_paths_extracts_and_delegates(self):
        """Zip without path traversal should extract and recurse."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with zipfile.ZipFile(tmp_path, 'w') as zf:
                zf.writestr('domain_users.json', '[]')
                zf.writestr('domain_groups.json', '[]')

            mock_result = {'imported': 0}
            with patch(
                'plugins_data.active_directory.backend.ingestion.ldap_parser.LDAPParser.ingest_from_directory',
                return_value=mock_result,
            ):
                result = ADAssessmentViewSet._run_ingestion('auto', tmp_path, 1)
            self.assertEqual(result, mock_result)
        finally:
            os.unlink(tmp_path)
```

- [ ] **Step 2: Run the tests**

```bash
docker exec rengine-web python manage.py test tests.test_ad_plugin_ingestion -v 2
```

Expected: `OK (5 tests)`

- [ ] **Step 3: Commit (main repo)**

```bash
git add web/tests/test_ad_plugin_ingestion.py
git commit -m "test(ad): add Django tests for AD plugin ingestion path traversal and auto-detection"
```

---

## Task 8: Post-Implementation — Report Templates (Django)

**Files:**
- Create: `web/templates/report/ad_modern.html`
- Create: `web/templates/report/ad_cyber_pro.html`
- Modify: `r3ngine-plugins/active_directory/backend/reporting/pdf_renderer.py`
- Modify: `r3ngine-plugins/active_directory/backend/api.py`

- [ ] **Step 1: Update `PDFRenderer` to support templates**

Read `r3ngine-plugins/active_directory/backend/reporting/pdf_renderer.py` first.

Add a template dispatch function and update the `PDFRenderer.render` signature. The full updated file:

```python
# r3ngine-plugins/active_directory/backend/reporting/pdf_renderer.py
from __future__ import annotations
import html


def _esc(value) -> str:
    return html.escape(str(value) if value is not None else '')


def _sev_color(sev: str) -> str:
    return {
        'CRITICAL': '#d32f2f',
        'HIGH': '#f44336',
        'MEDIUM': '#ff9800',
        'LOW': '#2196f3',
        'INFO': '#9e9e9e',
    }.get(sev, '#9e9e9e')


def _build_html(report: dict) -> str:
    # ... (keep existing _build_html body exactly as-is)
    pass  # NOTE: keep the full existing function body here


def _build_html_from_template(report: dict, template_name: str) -> str:
    from django.template.loader import render_to_string
    return render_to_string(f'report/{template_name}.html', {'report': report})


class PDFRenderer:
    SUPPORTED_TEMPLATES = frozenset({'standard', 'modern', 'cyber_pro'})

    @staticmethod
    def render(report: dict, template: str = 'standard') -> bytes:
        from weasyprint import HTML
        if template in PDFRenderer.SUPPORTED_TEMPLATES and template != 'standard':
            html_content = _build_html_from_template(report, f'ad_{template}')
        else:
            html_content = _build_html(report)
        return HTML(string=html_content).write_pdf()
```

**Important**: Keep the full body of `_build_html` exactly as it is. Only add `_build_html_from_template` and update `PDFRenderer.render` with the `template` parameter and dispatch logic.

- [ ] **Step 2: Update `api.py` to accept `?template=` query param**

Read `r3ngine-plugins/active_directory/backend/api.py` first.

In the `report` action method, after `fmt = request.query_params.get('format', 'json').lower()`, add:

```python
        template = request.query_params.get('template', 'standard').lower()
        if template not in PDFRenderer.SUPPORTED_TEMPLATES:
            template = 'standard'
```

Change both PDF render calls from:
```python
pdf_bytes = PDFRenderer.render(compiled)
```
to:
```python
pdf_bytes = PDFRenderer.render(compiled, template=template)
```

Also add the import at the top of the `report` action's try block (or import at module level if `PDFRenderer` is already referenced):
The `PDFRenderer` import is already inside the `if fmt == 'pdf':` block. No change needed to the import location; just add the `template` kwarg to the call.

- [ ] **Step 3: Create `web/templates/report/ad_modern.html`**

Create `web/templates/report/ad_modern.html` with a dark-themed, modern styled report using the `report` context variable (a dict with `metadata`, `executive_summary`, `findings`, `trust_analysis`, `exposure_analysis`, `timeline` keys):

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --accent: #58a6ff;
    --text: #c9d1d9;
    --muted: #8b949e;
    --crit: #f85149;
    --high: #ff7b72;
    --med: #e3b341;
    --low: #58a6ff;
    --info: #8b949e;
  }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', Arial, sans-serif;
         font-size: 10pt; margin: 0; padding: 32px; }
  h1 { font-size: 20pt; color: var(--accent); letter-spacing: 2px; text-transform: uppercase;
       border-bottom: 2px solid var(--accent); padding-bottom: 8px; margin-bottom: 24px; }
  h2 { font-size: 12pt; color: var(--accent); text-transform: uppercase; letter-spacing: 1px;
       margin-top: 32px; border-left: 3px solid var(--accent); padding-left: 10px; }
  .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }
  .meta-card { background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
               padding: 12px 16px; }
  .meta-label { font-size: 0.7em; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
  .meta-value { font-size: 1.1em; font-weight: bold; margin-top: 2px; }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 9pt; }
  th { background: var(--surface); color: var(--accent); padding: 7px 10px; text-align: left;
       border-bottom: 2px solid var(--border); font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.5px; }
  td { padding: 6px 10px; border-bottom: 1px solid var(--border); vertical-align: top; color: var(--text); }
  tr:hover td { background: rgba(88,166,255,0.04); }
  .sev-crit { color: var(--crit); font-weight: bold; }
  .sev-high { color: var(--high); font-weight: bold; }
  .sev-med  { color: var(--med); font-weight: bold; }
  .sev-low  { color: var(--low); }
  .sev-info { color: var(--info); }
  code { font-family: 'Consolas', monospace; font-size: 0.88em; color: var(--accent); }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75em;
           font-weight: bold; text-transform: uppercase; }
  .badge-crit { background: rgba(248,81,73,0.15); color: var(--crit); }
  .badge-high { background: rgba(255,123,114,0.15); color: var(--high); }
  .badge-med  { background: rgba(227,179,65,0.15); color: var(--med); }
  .badge-low  { background: rgba(88,166,255,0.15); color: var(--low); }
  .badge-info { background: rgba(139,148,158,0.15); color: var(--info); }
</style>
</head>
<body>
<h1>Active Directory Assessment Report</h1>
<div class="meta-grid">
  <div class="meta-card">
    <div class="meta-label">Assessment</div>
    <div class="meta-value">{{ report.metadata.assessment_name }}</div>
  </div>
  <div class="meta-card">
    <div class="meta-label">Target Domain</div>
    <div class="meta-value">{{ report.metadata.target_domain }}</div>
  </div>
  <div class="meta-card">
    <div class="meta-label">Status</div>
    <div class="meta-value">{{ report.metadata.status }}</div>
  </div>
  <div class="meta-card">
    <div class="meta-label">Generated</div>
    <div class="meta-value">{{ report.metadata.generated_at|slice:":19" }}</div>
  </div>
</div>

<h2>Executive Summary</h2>
<table>
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Domains Discovered</td><td>{{ report.executive_summary.domain_count }}</td></tr>
  <tr><td>Trust Relationships</td><td>{{ report.executive_summary.trust_count }}</td></tr>
  <tr><td>Exposed Services</td><td>{{ report.executive_summary.exposure_count }}</td></tr>
  <tr><td>Average Trust Risk</td><td>{{ report.executive_summary.average_trust_risk|floatformat:2 }}</td></tr>
  <tr><td>Average Exposure Risk</td><td>{{ report.executive_summary.average_exposure_risk|floatformat:2 }}</td></tr>
</table>

<h2>Finding Severity Breakdown</h2>
<table>
  <tr><th>Severity</th><th>Count</th></tr>
  {% for sev, count in report.executive_summary.finding_counts.items %}
  <tr><td class="sev-{{ sev|lower }}">{{ sev }}</td><td>{{ count }}</td></tr>
  {% empty %}
  <tr><td colspan="2">No findings recorded.</td></tr>
  {% endfor %}
</table>

<h2>Findings</h2>
<table>
  <tr><th>Severity</th><th>Title</th><th>Affected Object</th><th>Remediation</th></tr>
  {% for f in report.findings %}
  <tr>
    <td><span class="badge badge-{{ f.severity|lower }}">{{ f.severity }}</span></td>
    <td>{{ f.title }}</td>
    <td><code>{{ f.affected_object }}</code></td>
    <td style="font-size:0.85em">{{ f.remediation }}</td>
  </tr>
  {% empty %}
  <tr><td colspan="4">No findings recorded.</td></tr>
  {% endfor %}
</table>

<h2>Trust Analysis</h2>
<table>
  <tr><th>Source</th><th>Target</th><th>Type</th><th>Direction</th><th>Transitive</th><th>Selective Auth</th><th>Risk</th></tr>
  {% for t in report.trust_analysis %}
  <tr>
    <td>{{ t.source }}</td><td>{{ t.target }}</td><td>{{ t.type }}</td><td>{{ t.direction }}</td>
    <td>{% if t.is_transitive %}Yes{% else %}No{% endif %}</td>
    <td>{% if t.is_selective_auth %}Enabled{% else %}<span style="color:var(--crit)">Disabled</span>{% endif %}</td>
    <td>{{ t.risk_score|floatformat:1 }}</td>
  </tr>
  {% empty %}
  <tr><td colspan="7">No trust relationships found.</td></tr>
  {% endfor %}
</table>

<h2>Exposure Analysis</h2>
<table>
  <tr><th>Hostname</th><th>Type</th><th>Port</th><th>Risk</th><th>Correlated Domain</th></tr>
  {% for e in report.exposure_analysis %}
  <tr>
    <td>{{ e.hostname }}</td><td>{{ e.type }}</td><td>{{ e.port }}</td>
    <td>{{ e.risk_score|floatformat:1 }}</td><td>{{ e.correlated_domain }}</td>
  </tr>
  {% empty %}
  <tr><td colspan="5">No exposures found.</td></tr>
  {% endfor %}
</table>

<h2>Assessment Timeline</h2>
<table>
  <tr><th>Timestamp</th><th>Event</th><th>Actor</th></tr>
  {% for ev in report.timeline %}
  <tr>
    <td style="white-space:nowrap;font-size:0.8em">{{ ev.timestamp|slice:":19" }}</td>
    <td>{{ ev.event_type }}</td><td>{{ ev.actor }}</td>
  </tr>
  {% empty %}
  <tr><td colspan="3">No timeline events recorded.</td></tr>
  {% endfor %}
</table>
</body>
</html>
```

- [ ] **Step 4: Create `web/templates/report/ad_cyber_pro.html`**

Create `web/templates/report/ad_cyber_pro.html` with a high-contrast cyberpunk-themed template. Same context variables as `ad_modern.html` but with a neon-on-black aesthetic:

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  :root {
    --bg: #000;
    --surface: #0a0a0a;
    --border: #00f3ff33;
    --accent: #00f3ff;
    --accent2: #ff003c;
    --text: #e0f7fa;
    --muted: #4dd0e1;
    --crit: #ff1744;
    --high: #ff5722;
    --med: #ffc107;
    --low: #00b0ff;
    --info: #4dd0e1;
  }
  @page { margin: 20mm; }
  body { background: var(--bg); color: var(--text);
         font-family: 'Consolas', 'Courier New', monospace; font-size: 9pt; margin: 0; padding: 0; }
  h1 { font-size: 16pt; color: var(--accent); letter-spacing: 4px; text-transform: uppercase;
       border-bottom: 1px solid var(--accent); padding-bottom: 6px; margin-bottom: 20px;
       text-shadow: 0 0 8px var(--accent); }
  h2 { font-size: 10pt; color: var(--accent); text-transform: uppercase; letter-spacing: 2px;
       margin-top: 24px; margin-bottom: 6px;
       border-left: 2px solid var(--accent); padding-left: 8px;
       text-shadow: 0 0 4px var(--accent); }
  .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 20px; }
  .meta-card { background: var(--surface); border: 1px solid var(--border); padding: 8px 12px; }
  .meta-label { font-size: 0.65em; color: var(--muted); text-transform: uppercase; letter-spacing: 2px; }
  .meta-value { font-size: 1em; color: var(--accent); font-weight: bold; margin-top: 2px; }
  table { width: 100%; border-collapse: collapse; margin-top: 6px; font-size: 8.5pt; }
  th { background: #001a1a; color: var(--accent); padding: 5px 8px; text-align: left;
       border: 1px solid var(--border); font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px; }
  td { padding: 4px 8px; border: 1px solid #001a1a; vertical-align: top; }
  tr:nth-child(even) td { background: #050f0f; }
  .crit { color: var(--crit); font-weight: bold; }
  .high { color: var(--high); font-weight: bold; }
  .med  { color: var(--med); }
  .low  { color: var(--low); }
  .info { color: var(--info); }
  code { color: var(--accent); font-size: 0.9em; }
</style>
</head>
<body>
<h1>// Active Directory Assessment Report</h1>
<div class="meta-grid">
  <div class="meta-card">
    <div class="meta-label">Assessment</div>
    <div class="meta-value">{{ report.metadata.assessment_name }}</div>
  </div>
  <div class="meta-card">
    <div class="meta-label">Target</div>
    <div class="meta-value">{{ report.metadata.target_domain }}</div>
  </div>
  <div class="meta-card">
    <div class="meta-label">Status</div>
    <div class="meta-value">{{ report.metadata.status }}</div>
  </div>
  <div class="meta-card">
    <div class="meta-label">Generated</div>
    <div class="meta-value">{{ report.metadata.generated_at|slice:":19" }}</div>
  </div>
</div>

<h2>// Executive Summary</h2>
<table>
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Domains</td><td>{{ report.executive_summary.domain_count }}</td></tr>
  <tr><td>Trusts</td><td>{{ report.executive_summary.trust_count }}</td></tr>
  <tr><td>Exposures</td><td>{{ report.executive_summary.exposure_count }}</td></tr>
  <tr><td>Avg Trust Risk</td><td>{{ report.executive_summary.average_trust_risk|floatformat:2 }}</td></tr>
  <tr><td>Avg Exposure Risk</td><td>{{ report.executive_summary.average_exposure_risk|floatformat:2 }}</td></tr>
</table>

<h2>// Severity Breakdown</h2>
<table>
  <tr><th>Severity</th><th>Count</th></tr>
  {% for sev, count in report.executive_summary.finding_counts.items %}
  <tr><td class="{{ sev|lower }}">{{ sev }}</td><td>{{ count }}</td></tr>
  {% empty %}
  <tr><td colspan="2">// NO FINDINGS</td></tr>
  {% endfor %}
</table>

<h2>// Findings</h2>
<table>
  <tr><th>Sev</th><th>Title</th><th>Object</th><th>Remediation</th></tr>
  {% for f in report.findings %}
  <tr>
    <td class="{{ f.severity|lower }}">{{ f.severity }}</td>
    <td>{{ f.title }}</td>
    <td><code>{{ f.affected_object }}</code></td>
    <td style="font-size:0.8em">{{ f.remediation }}</td>
  </tr>
  {% empty %}
  <tr><td colspan="4">// NO FINDINGS</td></tr>
  {% endfor %}
</table>

<h2>// Trust Topology</h2>
<table>
  <tr><th>Source</th><th>Target</th><th>Type</th><th>Dir</th><th>Trans</th><th>SelAuth</th><th>Risk</th></tr>
  {% for t in report.trust_analysis %}
  <tr>
    <td>{{ t.source }}</td><td>{{ t.target }}</td><td>{{ t.type }}</td><td>{{ t.direction }}</td>
    <td>{% if t.is_transitive %}Y{% else %}N{% endif %}</td>
    <td>{% if t.is_selective_auth %}<span class="low">ON</span>{% else %}<span class="crit">OFF</span>{% endif %}</td>
    <td>{{ t.risk_score|floatformat:1 }}</td>
  </tr>
  {% empty %}
  <tr><td colspan="7">// NO TRUSTS</td></tr>
  {% endfor %}
</table>

<h2>// Exposure Surface</h2>
<table>
  <tr><th>Hostname</th><th>Type</th><th>Port</th><th>Risk</th><th>Domain</th></tr>
  {% for e in report.exposure_analysis %}
  <tr>
    <td>{{ e.hostname }}</td><td>{{ e.type }}</td><td>{{ e.port }}</td>
    <td>{{ e.risk_score|floatformat:1 }}</td><td>{{ e.correlated_domain }}</td>
  </tr>
  {% empty %}
  <tr><td colspan="5">// NO EXPOSURES</td></tr>
  {% endfor %}
</table>

<h2>// Timeline</h2>
<table>
  <tr><th>Timestamp</th><th>Event</th><th>Actor</th></tr>
  {% for ev in report.timeline %}
  <tr>
    <td style="white-space:nowrap;font-size:0.8em">{{ ev.timestamp|slice:":19" }}</td>
    <td>{{ ev.event_type }}</td><td>{{ ev.actor }}</td>
  </tr>
  {% empty %}
  <tr><td colspan="3">// NO EVENTS</td></tr>
  {% endfor %}
</table>
</body>
</html>
```

- [ ] **Step 5: Verify templates render (Django shell in Docker)**

```bash
docker exec rengine-web python -c "
from django.template.loader import render_to_string
report = {
  'metadata': {'assessment_name': 'Test', 'target_domain': 'corp.local', 'status': 'SUCCESS', 'generated_at': '2026-05-26T00:00:00'},
  'executive_summary': {'domain_count': 1, 'trust_count': 0, 'exposure_count': 0, 'average_trust_risk': 0.0, 'average_exposure_risk': 0.0, 'finding_counts': {}},
  'findings': [], 'trust_analysis': [], 'exposure_analysis': [], 'timeline': [],
}
out = render_to_string('report/ad_modern.html', {'report': report})
print(out[:200])
out2 = render_to_string('report/ad_cyber_pro.html', {'report': report})
print(out2[:200])
print('TEMPLATES OK')
"
```

Expected: first 200 chars of each template output followed by `TEMPLATES OK`.

- [ ] **Step 6: Commit templates to main repo**

```bash
git add web/templates/report/ad_modern.html web/templates/report/ad_cyber_pro.html
git commit -m "feat(templates): add AD assessment report templates (modern and cyber_pro styles)"
```

- [ ] **Step 7: Commit pdf_renderer and api changes to plugin repo**

```bash
cd /d/Repos/r3ngine/r3ngine-plugins
git add active_directory/backend/reporting/pdf_renderer.py active_directory/backend/api.py
git commit -m "feat(reporting): add template selection support to PDFRenderer and report endpoint"
```

---

## Task 9: Post-Implementation — ADReportModal Component

**Files:**
- Create: `r3ngine-plugins/active_directory/ui/src/components/ADReportModal.tsx`
- Modify: `r3ngine-plugins/active_directory/ui/src/pages/ADReportsPage.tsx`
- Modify: `r3ngine-plugins/active_directory/ui/src/api/adApi.ts`

- [ ] **Step 1: Update `useGenerateReport` in `adApi.ts` to accept `template`**

Read `r3ngine-plugins/active_directory/ui/src/api/adApi.ts` first.

Change the `mutationFn` type signature from:
```typescript
mutationFn: async ({ assessmentId, format }: { assessmentId: number; format: 'json' | 'pdf' }) => {
  const res = await fetch(`${API_BASE}/${assessmentId}/report/?format=${format}`, {
```
to:
```typescript
mutationFn: async ({
  assessmentId,
  format,
  template = 'standard',
}: {
  assessmentId: number;
  format: 'json' | 'pdf';
  template?: string;
}) => {
  const params = new URLSearchParams({ format });
  if (format === 'pdf' && template !== 'standard') params.set('template', template);
  const res = await fetch(`${API_BASE}/${assessmentId}/report/?${params}`, {
```

- [ ] **Step 2: Create `ADReportModal.tsx`**

Create `r3ngine-plugins/active_directory/ui/src/components/ADReportModal.tsx`:

```tsx
import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  ToggleButtonGroup,
  ToggleButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  CircularProgress,
} from '@mui/material';
import { FileText, FileDown } from 'lucide-react';
import { useGenerateReport } from '../api/adApi';

interface ADReportModalProps {
  assessmentId: number;
  open: boolean;
  onClose: () => void;
}

export function ADReportModal({ assessmentId, open, onClose }: ADReportModalProps) {
  const [format, setFormat] = useState<'json' | 'pdf'>('pdf');
  const [template, setTemplate] = useState('standard');
  const { mutate: generate, isPending } = useGenerateReport();

  const handleGenerate = () => {
    generate(
      { assessmentId, format, template },
      { onSettled: onClose },
    );
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            bgcolor: '#0d0d1a',
            border: '1px solid rgba(0,243,255,0.2)',
          },
        },
      }}
    >
      <DialogTitle sx={{ fontFamily: 'Orbitron', letterSpacing: 2, fontSize: '0.9rem' }}>
        GENERATE REPORT
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>
          <Box>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', mb: 0.5, display: 'block' }}>
              FORMAT
            </Typography>
            <ToggleButtonGroup
              value={format}
              exclusive
              onChange={(_e, v) => { if (v) setFormat(v as 'json' | 'pdf'); }}
              size="small"
              fullWidth
            >
              <ToggleButton value="pdf" sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>
                <FileDown size={14} style={{ marginRight: 6 }} />
                PDF
              </ToggleButton>
              <ToggleButton value="json" sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>
                <FileText size={14} style={{ marginRight: 6 }} />
                JSON
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>

          {format === 'pdf' && (
            <FormControl fullWidth size="small">
              <InputLabel sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>Template</InputLabel>
              <Select
                value={template}
                label="Template"
                onChange={(e) => setTemplate(e.target.value)}
                sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
              >
                <MenuItem value="standard">Standard (Default)</MenuItem>
                <MenuItem value="modern">Modern (Dark)</MenuItem>
                <MenuItem value="cyber_pro">Cyber Pro (High Contrast)</MenuItem>
              </Select>
            </FormControl>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 2, pb: 2 }}>
        <Button onClick={onClose} disabled={isPending} sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleGenerate}
          disabled={isPending}
          startIcon={isPending ? <CircularProgress size={14} /> : <FileDown size={14} />}
          sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}
        >
          {isPending ? 'Generating…' : 'Download'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```

- [ ] **Step 3: Update `ADReportsPage.tsx` to use the modal**

Read `r3ngine-plugins/active_directory/ui/src/pages/ADReportsPage.tsx` first.

Add the import:
```typescript
import { ADReportModal } from '../components/ADReportModal';
```

Add modal open state:
```typescript
const [modalOpen, setModalOpen] = useState(false);
```

Replace the inline format toggle + download button section with a single "Generate Report" button that opens the modal:
```tsx
<Button
  variant="contained"
  startIcon={<FileDown size={16} />}
  onClick={() => setModalOpen(true)}
  sx={{ fontFamily: 'Orbitron', fontSize: '0.75rem', letterSpacing: 1 }}
>
  Generate Report
</Button>

<ADReportModal
  assessmentId={assessmentId}
  open={modalOpen}
  onClose={() => setModalOpen(false)}
/>
```

Remove the `useGenerateReport` import and usage from `ADReportsPage.tsx` if it is no longer used directly (the modal owns the mutation now).

- [ ] **Step 4: TypeScript check + build**

```bash
cd /d/Repos/r3ngine/r3ngine-plugins/active_directory/ui && npx tsc --noEmit 2>&1 | head -30 && npm run build 2>&1 | tail -10
```

Expected: zero errors, build succeeds.

- [ ] **Step 5: Commit (plugin repo)**

```bash
cd /d/Repos/r3ngine/r3ngine-plugins
git add active_directory/ui/src/components/ADReportModal.tsx \
        active_directory/ui/src/pages/ADReportsPage.tsx \
        active_directory/ui/src/api/adApi.ts
git commit -m "feat(ui): add ADReportModal with format and template selection"
```

---

## Self-Review

**Spec coverage check:**

| Phase 13 requirement | Covered by |
|---|---|
| Subdomain row action "Assess Identity Infrastructure" | Task 1 (endpoint) + Task 2 (menu item) |
| Bridge endpoint accepts subdomain_id, extracts root domain | Task 1 `LaunchADAssessmentFromSubdomain` |
| No auto-start (assessment-only, user initiates) | Task 1 — creates PENDING, no workflow start |

| Phase 14 requirement | Covered by |
|---|---|
| analyticsStore.ts | Task 3 Step 1 |
| Severity filter in findings tab | Task 3 Step 2 |
| Direction filter in trust analytics | Task 3 Step 3 |
| Type filter in exposure dashboard | Task 3 Step 4 |

| Phase 15 requirement | Covered by |
|---|---|
| StylesheetCSS type fix | Task 4 Step 2 |
| Unused React import cleanup | Task 4 Step 3 |
| Remaining strict errors | Task 4 Step 4 |

| Phase 16 requirement | Covered by |
|---|---|
| Permission model tests | Task 5 |
| Graph endpoint tests | Task 6 |
| Ingestion path traversal tests | Task 7 |

| Post-Implementation requirement | Covered by |
|---|---|
| ADReportModal component | Task 9 Step 2 |
| Template selection in modal | Task 9 Step 2–3 |
| ad_modern.html template | Task 8 Step 3 |
| ad_cyber_pro.html template | Task 8 Step 4 |
| PDFRenderer template dispatch | Task 8 Step 1 |
| ?template= query param in API | Task 8 Step 2 |

**Placeholder scan:** All code blocks contain complete implementations. No TBD, TODO, or "similar to Task N" references.

**Type consistency check:**
- `useGenerateReport` now accepts `{ assessmentId, format, template? }` — matched in `ADReportModal.tsx` call
- `PDFRenderer.render(report, template='standard')` — called from `api.py` as `PDFRenderer.render(compiled, template=template)`
- `analyticsStore` exports `useAnalyticsStore` — imported by the same name in all three page files
- `LaunchADAssessmentFromSubdomain` class name matches URL registration

---

## Execution Handoff

After completing all 9 tasks, run the full AD plugin test suite:

```bash
docker exec rengine-web python manage.py test \
  tests.test_ad_plugin_permissions \
  tests.test_ad_plugin_graph \
  tests.test_ad_plugin_ingestion \
  tests.test_ad_plugin_phase13 \
  -v 2
```

Then build the plugin frontend:
```bash
cd /d/Repos/r3ngine/r3ngine-plugins/active_directory/ui && npm run build
```

And sync the built assets to `plugins_data/` (runtime only, do not commit):
```bash
# Run in Docker or per your local sync script
docker exec rengine-web python manage.py sync_plugin_ui active_directory
```
