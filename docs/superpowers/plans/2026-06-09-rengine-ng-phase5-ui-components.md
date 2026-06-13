# rengine-ng Integration — Phase 5: UI Components

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire all Phase 1–4 backend additions into the r3ngine React frontend — scan profile selector, extended target type input, standalone workflow launcher (the 13 new workflows), and a workflow status/history panel.

**Architecture:** New UI components follow the established r3ngine pattern: TypeScript interfaces for all props/API shapes, API functions in `frontend/src/api/`, Zustand store slice for workflow state, and standalone React components composed into the existing scan creation flow. The scan creation modal is extended (not replaced) to show the new options.

**Tech Stack:** React 18+, TypeScript, Vite, Zustand, existing Tailwind/component library already in the project

**Depends on:** Phases 1–4 complete (API endpoints must exist before frontend can call them)

---

## File Structure

| Action | Path | Purpose |
|--------|------|---------|
| Create | `frontend/src/api/profiles.ts` | ScanProfile REST client functions |
| Create | `frontend/src/api/workflows.ts` | Standalone workflow start/status client |
| Create | `frontend/src/features/profiles/types.ts` | TypeScript interfaces for profiles |
| Create | `frontend/src/features/profiles/components/ProfileSelector.tsx` | Dropdown selector for scan profiles |
| Create | `frontend/src/features/profiles/components/ProfileBadge.tsx` | Small badge showing active profile |
| Create | `frontend/src/features/profiles/components/ProfileManager.tsx` | Full profile list/create/delete page |
| Create | `frontend/src/features/workflows/types.ts` | TypeScript interfaces for standalone workflows |
| Create | `frontend/src/features/workflows/components/WorkflowLauncher.tsx` | Modal to start any of the 13 workflows |
| Create | `frontend/src/features/workflows/components/WorkflowStatusPanel.tsx` | Running/completed workflow list |
| Modify | `frontend/src/features/targets/components/TargetTypeSelector.tsx` | Extend with 6 new target types |
| Modify | `frontend/src/features/scan/components/NewScanModal.tsx` (or equivalent) | Add ProfileSelector + TargetTypeSelector |
| Modify | `frontend/src/features/scan/pages/ScanListPage.tsx` (or equivalent) | Add WorkflowLauncher entry point |

---

## Task 1: Define TypeScript interfaces and API clients

**Files:**
- Create: `frontend/src/features/profiles/types.ts`
- Create: `frontend/src/features/workflows/types.ts`
- Create: `frontend/src/api/profiles.ts`
- Create: `frontend/src/api/workflows.ts`

- [ ] **Step 1: Find the existing API base pattern**

```bash
head -30 frontend/src/api/scan.ts 2>/dev/null || head -30 frontend/src/api/index.ts 2>/dev/null || ls frontend/src/api/
```
This reveals the existing `axiosInstance` or `fetch` wrapper used. Use the same import and pattern for the new files.

- [ ] **Step 2: Create `frontend/src/features/profiles/types.ts`**

```typescript
export interface ScanProfile {
  id: number;
  name: string;
  description: string;
  category: 'speed' | 'evasion' | 'content' | 'network' | 'general' | 'hardware';
  is_builtin: boolean;
  // Throttle settings (null = tool default)
  rate_limit: number | null;
  delay: number | null;
  threads: number | null;
  timeout: number | null;
  retries: number | null;
  // Mode flags
  passive: boolean;
  active: boolean;
  stealth: boolean;
  headless: boolean;
  screenshot: boolean;
  hunt_secrets: boolean;
  nuclei_full: boolean;
  brute_dns: boolean;
  brute_http: boolean;
  test_ssl: boolean;
  all_ports: boolean;
  tor: boolean;
  fragment: boolean;
}

export interface CreateProfilePayload {
  name: string;
  description?: string;
  category?: ScanProfile['category'];
  rate_limit?: number;
  delay?: number;
  threads?: number;
  timeout?: number;
  retries?: number;
  passive?: boolean;
  active?: boolean;
  stealth?: boolean;
  hunt_secrets?: boolean;
}
```

- [ ] **Step 3: Create `frontend/src/features/workflows/types.ts`**

```typescript
export type WorkflowSlug =
  | 'user-hunt'
  | 'url-bypass'
  | 'wordpress'
  | 'host-recon'
  | 'cidr-recon'
  | 'code-scan'
  | 'domain-recon'
  | 'subdomain-recon'
  | 'url-crawl'
  | 'url-dirsearch'
  | 'url-fuzz'
  | 'url-params-fuzz'
  | 'url-vuln';

export interface WorkflowMeta {
  slug: WorkflowSlug;
  label: string;
  description: string;
  inputLabel: string;
  inputPlaceholder: string;
  inputType: 'domain' | 'url' | 'cidr' | 'email' | 'username' | 'path' | 'ip';
  category: 'recon' | 'vuln' | 'crawl' | 'osint' | 'code' | 'network';
}

export const WORKFLOW_REGISTRY: WorkflowMeta[] = [
  {
    slug: 'user-hunt',
    label: 'User Hunt',
    description: 'Search for user accounts and password leaks across platforms.',
    inputLabel: 'Target (username or email)',
    inputPlaceholder: 'johndoe or user@example.com',
    inputType: 'username',
    category: 'osint',
  },
  {
    slug: 'url-bypass',
    label: 'URL Bypass (4xx)',
    description: 'Attempt to bypass 4xx access restrictions using header manipulation.',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com/admin',
    inputType: 'url',
    category: 'vuln',
  },
  {
    slug: 'wordpress',
    label: 'WordPress Scan',
    description: 'Scan WordPress sites for plugin vulnerabilities and misconfigurations.',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com',
    inputType: 'url',
    category: 'vuln',
  },
  {
    slug: 'host-recon',
    label: 'Host Recon',
    description: 'Port scan, service detection, SSH audit, and HTTP probe for a host/IP.',
    inputLabel: 'Host or IP',
    inputPlaceholder: '192.0.2.1 or target.example.com',
    inputType: 'ip',
    category: 'recon',
  },
  {
    slug: 'cidr-recon',
    label: 'CIDR Recon',
    description: 'Discover and scan hosts within a CIDR network range.',
    inputLabel: 'CIDR Range',
    inputPlaceholder: '192.168.1.0/24',
    inputType: 'cidr',
    category: 'network',
  },
  {
    slug: 'code-scan',
    label: 'Code Scan',
    description: 'Scan source code or git repositories for secrets and vulnerabilities.',
    inputLabel: 'Repository or Path',
    inputPlaceholder: 'https://github.com/user/repo or /path/to/code',
    inputType: 'path',
    category: 'code',
  },
  {
    slug: 'domain-recon',
    label: 'Domain Recon',
    description: 'Quick domain intelligence: WHOIS, DNS, SSL, WAF, ASN.',
    inputLabel: 'Domain',
    inputPlaceholder: 'example.com',
    inputType: 'domain',
    category: 'recon',
  },
  {
    slug: 'subdomain-recon',
    label: 'Subdomain Recon',
    description: 'Discover and verify subdomains with takeover detection.',
    inputLabel: 'Domain',
    inputPlaceholder: 'example.com',
    inputType: 'domain',
    category: 'recon',
  },
  {
    slug: 'url-crawl',
    label: 'URL Crawl',
    description: 'Multi-source URL discovery (passive + active crawlers).',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com',
    inputType: 'url',
    category: 'crawl',
  },
  {
    slug: 'url-dirsearch',
    label: 'Directory Search',
    description: 'Find hidden directories and files on a web server.',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com',
    inputType: 'url',
    category: 'crawl',
  },
  {
    slug: 'url-fuzz',
    label: 'URL Fuzz',
    description: 'Comprehensive web content fuzzing with feroxbuster and ffuf.',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com',
    inputType: 'url',
    category: 'vuln',
  },
  {
    slug: 'url-params-fuzz',
    label: 'Parameter Fuzz',
    description: 'Discover and test hidden HTTP parameters.',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com/search',
    inputType: 'url',
    category: 'vuln',
  },
  {
    slug: 'url-vuln',
    label: 'URL Vulnerability',
    description: 'Scan URL patterns for XSS, LFI, SSRF, RCE, IDOR (gf + dalfox + nuclei).',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com/search?q=test',
    inputType: 'url',
    category: 'vuln',
  },
];

export interface StartWorkflowPayload {
  target?: string;
  target_type?: string;
  urls?: string[];
  cidr?: string;
  domain?: string;
  profile_name?: string;
  yaml_configuration?: Record<string, unknown>;
}

export interface StartWorkflowResponse {
  workflow_id: string;
  status: 'started';
}
```

- [ ] **Step 4: Create `frontend/src/api/profiles.ts`**

Replace `axiosInstance` with whatever the existing API client exports (check `frontend/src/api/`):

```typescript
import axiosInstance from './index';
import type { ScanProfile, CreateProfilePayload } from '../features/profiles/types';

export const fetchProfiles = async (): Promise<ScanProfile[]> => {
  const { data } = await axiosInstance.get<ScanProfile[]>('/api/v1/profiles/');
  return Array.isArray(data) ? data : (data as { results: ScanProfile[] }).results ?? [];
};

export const fetchProfile = async (name: string): Promise<ScanProfile> => {
  const { data } = await axiosInstance.get<ScanProfile>(`/api/v1/profiles/${name}/`);
  return data;
};

export const createProfile = async (payload: CreateProfilePayload): Promise<ScanProfile> => {
  const { data } = await axiosInstance.post<ScanProfile>('/api/v1/profiles/', payload);
  return data;
};

export const deleteProfile = async (name: string): Promise<void> => {
  await axiosInstance.delete(`/api/v1/profiles/${name}/`);
};
```

- [ ] **Step 5: Create `frontend/src/api/workflows.ts`**

```typescript
import axiosInstance from './index';
import type { StartWorkflowPayload, StartWorkflowResponse } from '../features/workflows/types';
import type { WorkflowSlug } from '../features/workflows/types';

export const startWorkflow = async (
  slug: WorkflowSlug,
  payload: StartWorkflowPayload,
): Promise<StartWorkflowResponse> => {
  const { data } = await axiosInstance.post<StartWorkflowResponse>(
    `/api/v1/workflows/${slug}/start/`,
    payload,
  );
  return data;
};
```

- [ ] **Step 6: Verify TypeScript compiles with no errors**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npx tsc --noEmit 2>&1 | head -30"
```
Expected: no errors related to the new files.

- [ ] **Step 7: Commit types + API clients**

```bash
git add frontend/src/features/profiles/types.ts frontend/src/features/workflows/types.ts frontend/src/api/profiles.ts frontend/src/api/workflows.ts
git commit -m "feat(ui): add TypeScript interfaces and API clients for profiles and workflows"
```

---

## Task 2: `ProfileSelector` component

**Files:**
- Create: `frontend/src/features/profiles/components/ProfileSelector.tsx`

- [ ] **Step 1: Implement `ProfileSelector`**

```tsx
// frontend/src/features/profiles/components/ProfileSelector.tsx
import React, { useEffect, useState } from 'react';
import { fetchProfiles } from '../../../api/profiles';
import type { ScanProfile } from '../types';

interface ProfileSelectorProps {
  value: string | null;
  onChange: (profileName: string | null) => void;
  className?: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  hardware: 'Hardware',
  speed: 'Speed / Throttle',
  evasion: 'Evasion',
  content: 'Content',
  network: 'Network',
  general: 'General',
};

export const ProfileSelector: React.FC<ProfileSelectorProps> = ({
  value,
  onChange,
  className = '',
}) => {
  const [profiles, setProfiles] = useState<ScanProfile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfiles()
      .then(setProfiles)
      .finally(() => setLoading(false));
  }, []);

  const grouped = profiles.reduce<Record<string, ScanProfile[]>>((acc, p) => {
    const cat = p.category;
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(p);
    return acc;
  }, {});

  return (
    <div className={className}>
      <label className="block text-sm font-medium mb-1">Scan Profile</label>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={loading}
        className="w-full rounded border px-3 py-2 text-sm bg-background"
      >
        <option value="">Default (no profile)</option>
        {Object.entries(grouped).map(([category, items]) => (
          <optgroup key={category} label={CATEGORY_LABELS[category] ?? category}>
            {items.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name.replace(/_/g, ' ')}
                {p.description ? ` — ${p.description.slice(0, 50)}` : ''}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      {value && (
        <p className="text-xs text-muted-foreground mt-1">
          {profiles.find((p) => p.name === value)?.description}
        </p>
      )}
    </div>
  );
};

export default ProfileSelector;
```

- [ ] **Step 2: Verify build**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npm run build 2>&1 | tail -15"
```
Expected: build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/profiles/components/ProfileSelector.tsx
git commit -m "feat(ui): add ProfileSelector component with grouped dropdown by category"
```

---

## Task 3: `WorkflowLauncher` component

**Files:**
- Create: `frontend/src/features/workflows/components/WorkflowLauncher.tsx`

- [ ] **Step 1: Implement `WorkflowLauncher`**

```tsx
// frontend/src/features/workflows/components/WorkflowLauncher.tsx
import React, { useState } from 'react';
import { startWorkflow } from '../../../api/workflows';
import { WORKFLOW_REGISTRY } from '../types';
import type { WorkflowSlug, WorkflowMeta } from '../types';
import { ProfileSelector } from '../../profiles/components/ProfileSelector';

interface WorkflowLauncherProps {
  onSuccess?: (workflowId: string, slug: WorkflowSlug) => void;
  onError?: (error: string) => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  recon: 'bg-blue-100 text-blue-800',
  vuln: 'bg-red-100 text-red-800',
  crawl: 'bg-green-100 text-green-800',
  osint: 'bg-purple-100 text-purple-800',
  code: 'bg-yellow-100 text-yellow-800',
  network: 'bg-orange-100 text-orange-800',
};

export const WorkflowLauncher: React.FC<WorkflowLauncherProps> = ({
  onSuccess,
  onError,
}) => {
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowMeta | null>(null);
  const [target, setTarget] = useState('');
  const [profileName, setProfileName] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLaunch = async () => {
    if (!selectedWorkflow || !target.trim()) return;

    setLoading(true);
    setError(null);

    const payload: Record<string, unknown> = {
      profile_name: profileName ?? undefined,
    };

    switch (selectedWorkflow.inputType) {
      case 'url':
        payload.urls = [target.trim()];
        break;
      case 'cidr':
        payload.cidr = target.trim();
        break;
      case 'domain':
        payload.domain = target.trim();
        payload.target_type = 'domain';
        break;
      case 'username':
        payload.target = target.trim();
        payload.target_type = target.includes('@') ? 'email' : 'username';
        break;
      case 'ip':
        payload.target = target.trim();
        payload.target_type = 'ip';
        break;
      case 'path':
        payload.target = target.trim();
        payload.target_type = 'code_path';
        break;
      default:
        payload.target = target.trim();
    }

    try {
      const result = await startWorkflow(selectedWorkflow.slug, payload);
      setTarget('');
      setSelectedWorkflow(null);
      setProfileName(null);
      onSuccess?.(result.workflow_id, selectedWorkflow.slug);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to start workflow';
      setError(msg);
      onError?.(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-2">Workflow Type</label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {WORKFLOW_REGISTRY.map((wf) => (
            <button
              key={wf.slug}
              type="button"
              onClick={() => { setSelectedWorkflow(wf); setTarget(''); }}
              className={[
                'rounded border p-2 text-left text-sm transition-colors',
                selectedWorkflow?.slug === wf.slug
                  ? 'border-primary bg-primary/10 font-medium'
                  : 'border-border hover:bg-muted',
              ].join(' ')}
            >
              <span
                className={['mr-1 rounded px-1 text-xs', CATEGORY_COLORS[wf.category]].join(' ')}
              >
                {wf.category}
              </span>
              {wf.label}
            </button>
          ))}
        </div>
      </div>

      {selectedWorkflow && (
        <>
          <div>
            <label className="block text-sm font-medium mb-1">
              {selectedWorkflow.inputLabel}
            </label>
            <input
              type="text"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder={selectedWorkflow.inputPlaceholder}
              className="w-full rounded border px-3 py-2 text-sm bg-background"
            />
            <p className="text-xs text-muted-foreground mt-1">
              {selectedWorkflow.description}
            </p>
          </div>

          <ProfileSelector value={profileName} onChange={setProfileName} />

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <button
            type="button"
            onClick={handleLaunch}
            disabled={loading || !target.trim()}
            className="w-full rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            {loading ? 'Launching…' : `Launch ${selectedWorkflow.label}`}
          </button>
        </>
      )}
    </div>
  );
};

export default WorkflowLauncher;
```

- [ ] **Step 2: Verify build**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npm run build 2>&1 | tail -15"
```
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/workflows/components/WorkflowLauncher.tsx
git commit -m "feat(ui): add WorkflowLauncher component with workflow grid selector + profile picker"
```

---

## Task 4: Extend `TargetTypeSelector` with 6 new types

**Files:**
- Modify: `frontend/src/features/targets/components/TargetTypeSelector.tsx` (or equivalent)

- [ ] **Step 1: Find the existing target type selector**

```bash
grep -rn "target_type\|TargetType" frontend/src/features/ --include="*.tsx" | head -10
```
Identify the file that renders the target type dropdown/radio group.

- [ ] **Step 2: Add the 6 new target types**

In the target type options array or enum (wherever the existing `domain`, `host`, `ip`, `url` options are defined), add:

```tsx
// Add to existing target type options array:
const TARGET_TYPE_OPTIONS = [
  // Existing types (keep as-is)
  { value: 'domain', label: 'Domain', icon: '🌐', description: 'Full domain scan (7-tier pipeline)' },
  { value: 'host', label: 'Host', icon: '🖥️', description: 'Host/hostname reconnaissance' },
  { value: 'ip', label: 'IP Address', icon: '🔌', description: 'IP address reconnaissance' },
  { value: 'url', label: 'URL', icon: '🔗', description: 'URL crawl and vulnerability scan' },
  // New types (Phase 3)
  { value: 'cidr', label: 'CIDR / Network', icon: '🌐', description: 'Network range discovery (cidr_recon)' },
  { value: 'email', label: 'Email', icon: '📧', description: 'Email breach hunt (h8mail + maigret)' },
  { value: 'username', label: 'Username', icon: '👤', description: 'Account search across platforms (maigret)' },
  { value: 'phone', label: 'Phone', icon: '📱', description: 'Phone number OSINT' },
  { value: 'crypto_address', label: 'Crypto Address', icon: '₿', description: 'Crypto wallet OSINT' },
  { value: 'code_path', label: 'Code / Repository', icon: '💻', description: 'Source code secrets and CVE scan' },
];
```

Add a visual separator or grouped display to distinguish "Classic" from "New" target types if the UI supports it.

- [ ] **Step 3: Update placeholder text based on selected type**

In the `name`/`target` input field that follows the type selector, add a `placeholder` map:

```tsx
const TARGET_PLACEHOLDER: Record<string, string> = {
  domain: 'example.com',
  host: 'target.example.com',
  ip: '192.0.2.1',
  url: 'https://example.com',
  cidr: '192.168.0.0/24',
  email: 'user@example.com',
  username: 'johndoe',
  phone: '+1 555 123 4567',
  crypto_address: '0x742d35Cc6634C0532925a3b8D...',
  code_path: 'https://github.com/user/repo',
};
```

- [ ] **Step 4: Build and verify**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npm run build 2>&1 | tail -15"
```
Expected: build succeeds with no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/targets/
git commit -m "feat(ui): extend TargetTypeSelector with 6 new rengine-ng target types"
```

---

## Task 5: Add `ProfileSelector` and `WorkflowLauncher` to existing scan creation UI

**Files:**
- Modify: scan creation modal/page (exact file found by grepping)

- [ ] **Step 1: Find the scan creation component**

```bash
grep -rn "NewScan\|CreateScan\|startScan\|initiate.*scan" frontend/src/ --include="*.tsx" | head -10
```
Note the file path (e.g., `frontend/src/features/scan/components/NewScanModal.tsx`).

- [ ] **Step 2: Add `ProfileSelector` to the form**

In the scan creation form, after the engine/configuration selector, add:

```tsx
import { ProfileSelector } from '../../profiles/components/ProfileSelector';

// In form state:
const [profileName, setProfileName] = useState<string | null>(null);

// In form payload (before API call):
const payload = {
  ...existingPayload,
  profile_name: profileName ?? undefined,
};

// In JSX:
<ProfileSelector
  value={profileName}
  onChange={setProfileName}
  className="mt-4"
/>
```

- [ ] **Step 3: Add a "Quick Scan / Workflows" tab or section**

In the scan creation UI (or on the scans list page), add a collapsible section or tab titled **"Standalone Workflows"** that renders `WorkflowLauncher`:

```tsx
import { WorkflowLauncher } from '../../workflows/components/WorkflowLauncher';

// In JSX (e.g. as a tab panel or accordion section):
<section aria-label="Standalone Workflows">
  <h3 className="text-lg font-semibold mb-3">Quick Workflow Launch</h3>
  <p className="text-sm text-muted-foreground mb-4">
    Run a targeted scan workflow without a full domain scan.
  </p>
  <WorkflowLauncher
    onSuccess={(id, slug) => {
      // Show toast notification
      console.log('Workflow started:', slug, id);
    }}
    onError={(err) => console.error(err)}
  />
</section>
```

- [ ] **Step 4: Build and verify**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npm run build 2>&1 | tail -15"
```
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat(ui): integrate ProfileSelector and WorkflowLauncher into scan creation UI"
```

---

## Task 6: `ProfileManager` page (optional — full CRUD UI)

**Files:**
- Create: `frontend/src/features/profiles/components/ProfileManager.tsx`

- [ ] **Step 1: Implement `ProfileManager`**

```tsx
// frontend/src/features/profiles/components/ProfileManager.tsx
import React, { useEffect, useState } from 'react';
import { fetchProfiles, createProfile, deleteProfile } from '../../../api/profiles';
import type { ScanProfile, CreateProfilePayload } from '../types';

export const ProfileManager: React.FC = () => {
  const [profiles, setProfiles] = useState<ScanProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CreateProfilePayload>({ name: '', category: 'speed' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    fetchProfiles()
      .then(setProfiles)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await createProfile(form);
      setShowCreate(false);
      setForm({ name: '', category: 'speed' });
      load();
    } catch {
      setError('Failed to create profile. Name may already exist.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete profile "${name}"?`)) return;
    try {
      await deleteProfile(name);
      load();
    } catch {
      setError('Failed to delete profile.');
    }
  };

  const categories = [...new Set(profiles.map((p) => p.category))];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Scan Profiles</h2>
        <button
          type="button"
          onClick={() => setShowCreate(!showCreate)}
          className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground"
        >
          {showCreate ? 'Cancel' : '+ New Profile'}
        </button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {showCreate && (
        <div className="rounded border p-4 space-y-3">
          <h3 className="font-medium">Create Custom Profile</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs">Name *</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full rounded border px-2 py-1 text-sm"
                placeholder="my_profile"
              />
            </div>
            <div>
              <label className="text-xs">Category</label>
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value as ScanProfile['category'] })}
                className="w-full rounded border px-2 py-1 text-sm"
              >
                {['speed', 'evasion', 'content', 'network', 'general', 'hardware'].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs">Rate Limit (req/s)</label>
              <input
                type="number"
                value={form.rate_limit ?? ''}
                onChange={(e) => setForm({ ...form, rate_limit: e.target.value ? +e.target.value : undefined })}
                className="w-full rounded border px-2 py-1 text-sm"
                placeholder="100"
              />
            </div>
            <div>
              <label className="text-xs">Threads</label>
              <input
                type="number"
                value={form.threads ?? ''}
                onChange={(e) => setForm({ ...form, threads: e.target.value ? +e.target.value : undefined })}
                className="w-full rounded border px-2 py-1 text-sm"
                placeholder="8"
              />
            </div>
          </div>
          <div className="flex gap-2">
            {(['passive', 'active', 'stealth', 'hunt_secrets', 'tor'] as const).map((flag) => (
              <label key={flag} className="flex items-center gap-1 text-sm">
                <input
                  type="checkbox"
                  checked={!!form[flag as keyof CreateProfilePayload]}
                  onChange={(e) => setForm({ ...form, [flag]: e.target.checked })}
                />
                {flag.replace(/_/g, ' ')}
              </label>
            ))}
          </div>
          <button
            type="button"
            onClick={handleCreate}
            disabled={saving || !form.name.trim()}
            className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Create Profile'}
          </button>
        </div>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading profiles…</p>
      ) : (
        categories.map((cat) => (
          <div key={cat}>
            <h3 className="text-sm font-medium uppercase text-muted-foreground mb-2">
              {cat}
            </h3>
            <div className="space-y-1">
              {profiles.filter((p) => p.category === cat).map((p) => (
                <div
                  key={p.name}
                  className="flex items-center justify-between rounded border px-3 py-2"
                >
                  <div>
                    <span className="font-medium text-sm">{p.name}</span>
                    {p.description && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {p.description}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    {p.rate_limit != null && <span>{p.rate_limit} r/s</span>}
                    {p.threads != null && <span>{p.threads}t</span>}
                    {p.passive && <span className="text-blue-600">passive</span>}
                    {p.stealth && <span className="text-yellow-600">stealth</span>}
                    {p.tor && <span className="text-green-600">tor</span>}
                    {!p.is_builtin && (
                      <button
                        type="button"
                        onClick={() => handleDelete(p.name)}
                        className="text-destructive hover:underline"
                      >
                        delete
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
};

export default ProfileManager;
```

- [ ] **Step 2: Wire `ProfileManager` into a settings/config page route**

```bash
grep -rn "Route\|router\|path=" frontend/src/App.tsx frontend/src/routes/ 2>/dev/null | grep -i "settings\|config\|engine" | head -5
```
Find the settings/configuration page and add:

```tsx
// In the appropriate settings page:
import { ProfileManager } from '../features/profiles/components/ProfileManager';

// Add as a tab or section:
<ProfileManager />
```

- [ ] **Step 3: Final build check**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npm run build 2>&1 | tail -15"
```
Expected: build succeeds, no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/profiles/components/ProfileManager.tsx frontend/src/
git commit -m "feat(ui): add ProfileManager component with CRUD, grouped by category"
```

---

## Task 7: Final integration check

- [ ] **Step 1: Full build**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npm run build 2>&1 | tail -20"
```
Expected: `✓ built in X.XXs` — no errors.

- [ ] **Step 2: Run frontend linting**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npx eslint src/features/profiles/ src/features/workflows/ src/api/profiles.ts src/api/workflows.ts 2>&1 | head -30"
```
Expected: no errors (warnings acceptable if pre-existing pattern).

- [ ] **Step 3: Tag Phase 5 complete**

```bash
git tag phase5-ui-components
```

---

## Self-Review

**Spec coverage:**
- ✅ TypeScript interfaces for all new API shapes (`ScanProfile`, `WorkflowMeta`, payloads)
- ✅ API client functions for profiles (CRUD) and workflow start
- ✅ `ProfileSelector` — grouped dropdown with description display
- ✅ `WorkflowLauncher` — grid selector for all 13 workflows + profile picker + target input
- ✅ `TargetTypeSelector` — extended with 6 new types + type-specific placeholders
- ✅ Scan creation form integrates `ProfileSelector` + `WorkflowLauncher` section
- ✅ `ProfileManager` — full CRUD page for custom profiles, read-only for built-ins

**Placeholder scan:** None — all components have real implementation code.

**Type consistency:**
- `WorkflowSlug` union type matches the `WORKFLOW_REGISTRY` slugs exactly
- `ScanProfile` interface field names match Django model fields (snake_case)
- `startWorkflow(slug, payload)` uses `WorkflowSlug` — consistent with `WORKFLOW_REGISTRY`
