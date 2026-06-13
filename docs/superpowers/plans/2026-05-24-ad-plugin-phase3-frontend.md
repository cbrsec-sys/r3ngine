# Active Directory Intelligence Plugin — Phase 3: Frontend & Visualization

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete React frontend for the AD Intelligence plugin — assessment management, graph explorer (Cytoscape.js), trust analytics, exposure dashboard, and real-time WebSocket progress — integrated into the existing r3ngine frontend shell.

**Architecture:** Frontend lives in `frontend/src/features/active_directory/`. Routes are added to `router.tsx`. Nav appears automatically via `manifest.ui.menu_item` (read by Shell.tsx from `/api/plugins/registry/`). Zustand manages local graph state and WebSocket sync. TanStack Query handles all server state. Cytoscape.js with `react-cytoscapejs` renders the graph with semantic layouts via `cytoscape-dagre`.

**Prerequisites:** Phase 1 + Phase 2 complete. Backend API running at `/api/plugins/active_directory/`.

**Tech Stack:** React 18, TypeScript, TanStack Router, TanStack Query, Zustand, Cytoscape.js, react-cytoscapejs, cytoscape-dagre, Apache ECharts, MUI, Framer Motion

**Spec coverage:** agint.md Phases 6, 7, 8 (React frontend, graph visualization, realtime streaming)

---

## File Map

| File | Action |
|---|---|
| `frontend/src/features/active_directory/index.ts` | **Create** |
| `frontend/src/features/active_directory/api/adApi.ts` | **Create** — all REST hooks |
| `frontend/src/features/active_directory/store/adStore.ts` | **Create** — Zustand store |
| `frontend/src/features/active_directory/hooks/useADWebSocket.ts` | **Create** |
| `frontend/src/features/active_directory/pages/ADAssessmentsPage.tsx` | **Create** |
| `frontend/src/features/active_directory/pages/ADAssessmentDetailPage.tsx` | **Create** |
| `frontend/src/features/active_directory/pages/ADGraphExplorerPage.tsx` | **Create** — Cytoscape.js |
| `frontend/src/features/active_directory/pages/ADTrustAnalyticsPage.tsx` | **Create** |
| `frontend/src/features/active_directory/pages/ADExposureDashboardPage.tsx` | **Create** |
| `frontend/src/features/active_directory/components/AssessmentStatusBadge.tsx` | **Create** |
| `frontend/src/features/active_directory/components/CreateAssessmentDialog.tsx` | **Create** |
| `frontend/src/features/active_directory/components/IngestDataDialog.tsx` | **Create** |
| `frontend/src/features/active_directory/components/GraphControlBar.tsx` | **Create** |
| `frontend/src/router.tsx` | **Modify** — add 5 AD routes |

---

## Task 1: Install frontend dependencies

**Context:** `react-cytoscapejs` is the React wrapper for Cytoscape.js. `cytoscape-dagre` provides the hierarchical layout. `echarts` and `echarts-for-react` provide the charts. `zustand` and `@tanstack/react-query` are already installed.

**Files:**
- No source files — dependency install step

- [ ] **Step 1.1: Install dependencies**

```bash
cd frontend
npm install cytoscape react-cytoscapejs cytoscape-dagre echarts echarts-for-react
npm install --save-dev @types/cytoscape @types/react-cytoscapejs
```

- [ ] **Step 1.2: Verify install**

```bash
cd frontend && node -e "require('cytoscape'); require('react-cytoscapejs'); console.log('deps OK')"
```

Expected: `deps OK`

- [ ] **Step 1.3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "deps(frontend): add cytoscape, react-cytoscapejs, cytoscape-dagre, echarts"
```

---

## Task 2: API hooks (adApi.ts)

**Context:** All REST calls go through TanStack Query hooks. The `useStartAssessment` and `useCancelAssessment` mutations also update the Zustand store's `activeAssessmentId`.

**Files:**
- Create: `frontend/src/features/active_directory/api/adApi.ts`

- [ ] **Step 2.1: Create adApi.ts**

```typescript
// frontend/src/features/active_directory/api/adApi.ts
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const BASE = '/api/plugins/active_directory/assessments';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ADAssessment {
  id: number;
  name: string;
  target_domain: string;
  status: 'PENDING' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  workflow_id: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  config: Record<string, unknown>;
  progress: Record<string, unknown>;
  domain_count?: number;
  finding_count?: number;
  exposure_count?: number;
}

export interface ADAssessmentDetail extends ADAssessment {
  domains: ADDomain[];
  finding_summary: Record<string, number>;
  exposure_summary: Record<string, number>;
}

export interface ADDomain {
  id: number;
  name: string;
  fqdn: string;
  sid: string;
  forest_root: boolean;
  functional_level: string;
  dc_count: number;
  user_count: number;
  group_count: number;
  computer_count: number;
  neo4j_node_id: string | null;
  discovered_at: string;
}

export interface ADFinding {
  id: number;
  title: string;
  description: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
  finding_type: string;
  affected_object: string | null;
  evidence: Record<string, unknown>;
  remediation: string | null;
  created_at: string;
}

export interface ADTrust {
  id: number;
  source_domain: number;
  source_domain_fqdn: string;
  target_domain_name: string;
  direction: 'INBOUND' | 'OUTBOUND' | 'BIDIRECTIONAL';
  trust_type: 'PARENT_CHILD' | 'CROSS_LINK' | 'EXTERNAL' | 'FOREST' | 'REALM';
  is_transitive: boolean;
  is_selective_auth: boolean;
  risk_score: number;
}

export interface ADExposure {
  id: number;
  hostname: string;
  ip_address: string | null;
  port: number | null;
  exposure_type: string;
  correlated_domain: number | null;
  correlated_domain_fqdn: string | null;
  risk_score: number;
  evidence: Record<string, unknown>;
  discovered_at: string;
}

export interface CytoscapeGraph {
  nodes: Array<{ data: Record<string, unknown> }>;
  edges: Array<{ data: Record<string, unknown> }>;
}

// ---------------------------------------------------------------------------
// Fetchers
// ---------------------------------------------------------------------------

export const fetchAssessments = async (): Promise<ADAssessment[]> => {
  const { data } = await axios.get(`${BASE}/`);
  return Array.isArray(data) ? data : data.results || [];
};

export const fetchAssessmentDetail = async (id: number): Promise<ADAssessmentDetail> => {
  const { data } = await axios.get(`${BASE}/${id}/`);
  return data;
};

export const fetchFindings = async (
  id: number, severity?: string): Promise<ADFinding[]> => {
  const params = severity ? { severity } : {};
  const { data } = await axios.get(`${BASE}/${id}/findings/`, { params });
  return data;
};

export const fetchTrusts = async (id: number): Promise<ADTrust[]> => {
  const { data } = await axios.get(`${BASE}/${id}/trusts/`);
  return data;
};

export const fetchExposures = async (id: number): Promise<ADExposure[]> => {
  const { data } = await axios.get(`${BASE}/${id}/exposures/`);
  return data;
};

export const fetchDomainGraph = async (id: number): Promise<CytoscapeGraph> => {
  const { data } = await axios.get(`${BASE}/${id}/graph/domains/`);
  return data;
};

export const fetchExposureGraph = async (id: number): Promise<CytoscapeGraph> => {
  const { data } = await axios.get(`${BASE}/${id}/graph/exposures/`);
  return data;
};

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export const createAssessment = async (
  payload: { name: string; target_domain: string; config?: Record<string, unknown> }
): Promise<ADAssessment> => {
  const { data } = await axios.post(`${BASE}/`, payload);
  return data;
};

export const startAssessment = async (id: number): Promise<{ workflow_id: string }> => {
  const { data } = await axios.post(`${BASE}/${id}/start/`);
  return data;
};

export const cancelAssessment = async (id: number): Promise<void> => {
  await axios.post(`${BASE}/${id}/cancel/`);
};

export const deleteAssessment = async (id: number): Promise<void> => {
  await axios.delete(`${BASE}/${id}/`);
};

export const ingestFile = async (
  id: number, file: File, type: string): Promise<Record<string, unknown>> => {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('type', type);
  const { data } = await axios.post(`${BASE}/${id}/ingest/`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export const useAssessments = () =>
  useQuery({ queryKey: ['ad-assessments'], queryFn: fetchAssessments });

export const useAssessmentDetail = (id: number) =>
  useQuery({
    queryKey: ['ad-assessment', id],
    queryFn: () => fetchAssessmentDetail(id),
    enabled: !!id,
  });

export const useFindings = (id: number, severity?: string) =>
  useQuery({
    queryKey: ['ad-findings', id, severity],
    queryFn: () => fetchFindings(id, severity),
    enabled: !!id,
  });

export const useTrusts = (id: number) =>
  useQuery({
    queryKey: ['ad-trusts', id],
    queryFn: () => fetchTrusts(id),
    enabled: !!id,
  });

export const useExposures = (id: number) =>
  useQuery({
    queryKey: ['ad-exposures', id],
    queryFn: () => fetchExposures(id),
    enabled: !!id,
  });

export const useDomainGraph = (id: number) =>
  useQuery({
    queryKey: ['ad-graph-domains', id],
    queryFn: () => fetchDomainGraph(id),
    enabled: !!id,
    staleTime: 60_000,
  });

export const useExposureGraph = (id: number) =>
  useQuery({
    queryKey: ['ad-graph-exposures', id],
    queryFn: () => fetchExposureGraph(id),
    enabled: !!id,
    staleTime: 60_000,
  });

export const useCreateAssessment = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createAssessment,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ad-assessments'] }),
  });
};

export const useStartAssessment = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: startAssessment,
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['ad-assessments'] });
      qc.invalidateQueries({ queryKey: ['ad-assessment', id] });
    },
  });
};

export const useCancelAssessment = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: cancelAssessment,
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['ad-assessments'] });
      qc.invalidateQueries({ queryKey: ['ad-assessment', id] });
    },
  });
};

export const useDeleteAssessment = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteAssessment,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ad-assessments'] }),
  });
};

export const useIngestFile = () =>
  useMutation({ mutationFn: ({ id, file, type }: { id: number; file: File; type: string }) =>
    ingestFile(id, file, type) });
```

- [ ] **Step 2.2: Commit**

```bash
git add frontend/src/features/active_directory/api/adApi.ts
git commit -m "feat(ad-frontend): add TanStack Query API hooks for all AD endpoints"
```

---

## Task 3: Zustand store

**Context:** Manages: which assessment is active, graph viewport state (selected node, zoom), WebSocket events buffer, and UI panel state (which side panel is open).

**Files:**
- Create: `frontend/src/features/active_directory/store/adStore.ts`

- [ ] **Step 3.1: Create adStore.ts**

```typescript
// frontend/src/features/active_directory/store/adStore.ts
import { create } from 'zustand';

interface WSEvent {
  type: string;
  phase?: string;
  message?: string;
  [key: string]: unknown;
}

interface ADState {
  // Active assessment
  activeAssessmentId: number | null;
  setActiveAssessmentId: (id: number | null) => void;

  // Graph state
  selectedNodeId: string | null;
  setSelectedNodeId: (id: string | null) => void;
  graphLayout: 'dagre' | 'radial' | 'grid';
  setGraphLayout: (layout: ADState['graphLayout']) => void;

  // Real-time events
  wsEvents: WSEvent[];
  appendWSEvent: (event: WSEvent) => void;
  clearWSEvents: () => void;

  // UI panels
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  activeSidePanel: 'findings' | 'domains' | 'trusts' | 'exposures' | null;
  setActiveSidePanel: (panel: ADState['activeSidePanel']) => void;

  // Ingest state
  ingestDialogOpen: boolean;
  setIngestDialogOpen: (open: boolean) => void;
}

export const useADStore = create<ADState>((set) => ({
  activeAssessmentId: null,
  setActiveAssessmentId: (id) => set({ activeAssessmentId: id }),

  selectedNodeId: null,
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),
  graphLayout: 'dagre',
  setGraphLayout: (layout) => set({ graphLayout: layout }),

  wsEvents: [],
  appendWSEvent: (event) =>
    set((state) => ({
      wsEvents: [...state.wsEvents.slice(-99), event],
    })),
  clearWSEvents: () => set({ wsEvents: [] }),

  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  activeSidePanel: null,
  setActiveSidePanel: (panel) => set({ activeSidePanel: panel }),

  ingestDialogOpen: false,
  setIngestDialogOpen: (open) => set({ ingestDialogOpen: open }),
}));
```

- [ ] **Step 3.2: Commit**

```bash
git add frontend/src/features/active_directory/store/adStore.ts
git commit -m "feat(ad-frontend): add Zustand adStore (assessment, graph, WebSocket, UI state)"
```

---

## Task 4: WebSocket hook

**Context:** Connects to `ws/ad/assessment/{id}/`, appends events to the Zustand store, and invalidates relevant TanStack Query caches when the assessment finishes.

**Files:**
- Create: `frontend/src/features/active_directory/hooks/useADWebSocket.ts`

- [ ] **Step 4.1: Create useADWebSocket.ts**

```typescript
// frontend/src/features/active_directory/hooks/useADWebSocket.ts
import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useADStore } from '../store/adStore';

const WS_BASE = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`;

export function useADWebSocket(assessmentId: number | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const { appendWSEvent, setActiveAssessmentId } = useADStore();
  const qc = useQueryClient();

  useEffect(() => {
    if (!assessmentId) return;

    const ws = new WebSocket(`${WS_BASE}/ws/ad/assessment/${assessmentId}/`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        appendWSEvent(data);

        if (data.type === 'assessment_finished') {
          qc.invalidateQueries({ queryKey: ['ad-assessments'] });
          qc.invalidateQueries({ queryKey: ['ad-assessment', assessmentId] });
          qc.invalidateQueries({ queryKey: ['ad-findings', assessmentId] });
          qc.invalidateQueries({ queryKey: ['ad-graph-domains', assessmentId] });
          qc.invalidateQueries({ queryKey: ['ad-graph-exposures', assessmentId] });
        }

        if (data.type === 'phase_completed') {
          qc.invalidateQueries({ queryKey: ['ad-assessment', assessmentId] });
        }
      } catch {
        // Non-JSON frame — ignore
      }
    };

    ws.onerror = (err) => console.error('[AD WS] Error:', err);

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [assessmentId]);

  const send = (data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  };

  return { send };
}
```

- [ ] **Step 4.2: Commit**

```bash
git add frontend/src/features/active_directory/hooks/useADWebSocket.ts
git commit -m "feat(ad-frontend): add useADWebSocket hook with TanStack Query invalidation on phase completion"
```

---

## Task 5: AssessmentStatusBadge and CreateAssessmentDialog components

**Context:** Reusable components used across all AD pages.

**Files:**
- Create: `frontend/src/features/active_directory/components/AssessmentStatusBadge.tsx`
- Create: `frontend/src/features/active_directory/components/CreateAssessmentDialog.tsx`

- [ ] **Step 5.1: Create AssessmentStatusBadge.tsx**

```tsx
// frontend/src/features/active_directory/components/AssessmentStatusBadge.tsx
import React from 'react';
import { Chip } from '@mui/material';

const STATUS_CONFIG: Record<string, { color: 'default' | 'primary' | 'success' | 'error' | 'warning' | 'info'; label: string }> = {
  PENDING: { color: 'default', label: 'Pending' },
  RUNNING: { color: 'primary', label: 'Running' },
  PAUSED: { color: 'warning', label: 'Paused' },
  COMPLETED: { color: 'success', label: 'Completed' },
  FAILED: { color: 'error', label: 'Failed' },
  CANCELLED: { color: 'default', label: 'Cancelled' },
};

export const AssessmentStatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const cfg = STATUS_CONFIG[status] || { color: 'default', label: status };
  return (
    <Chip
      label={cfg.label}
      color={cfg.color}
      size="small"
      variant={status === 'RUNNING' ? 'filled' : 'outlined'}
      sx={{ fontFamily: 'monospace', fontSize: '0.7rem', letterSpacing: 1 }}
    />
  );
};
```

- [ ] **Step 5.2: Create CreateAssessmentDialog.tsx**

```tsx
// frontend/src/features/active_directory/components/CreateAssessmentDialog.tsx
import React, { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Button, Box, Typography, CircularProgress
} from '@mui/material';
import { useCreateAssessment } from '../api/adApi';

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated?: (id: number) => void;
}

export const CreateAssessmentDialog: React.FC<Props> = ({ open, onClose, onCreated }) => {
  const [name, setName] = useState('');
  const [domain, setDomain] = useState('');
  const { mutate, isPending, error } = useCreateAssessment();

  const handleSubmit = () => {
    if (!name.trim() || !domain.trim()) return;
    mutate(
      { name: name.trim(), target_domain: domain.trim() },
      {
        onSuccess: (assessment) => {
          onCreated?.(assessment.id);
          setName('');
          setDomain('');
          onClose();
        },
      }
    );
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ fontFamily: 'Orbitron', letterSpacing: 2 }}>
        NEW ASSESSMENT
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          <TextField
            label="Assessment Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            fullWidth
            placeholder="e.g. CORP Initial Assessment Q2 2026"
            autoFocus
          />
          <TextField
            label="Target Domain"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            fullWidth
            placeholder="e.g. corp.example.com"
            helperText="Root domain to assess — subdomains are discovered automatically"
          />
          {error && (
            <Typography color="error" variant="body2">
              {String(error)}
            </Typography>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={isPending}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={isPending || !name.trim() || !domain.trim()}
          startIcon={isPending ? <CircularProgress size={16} /> : null}
        >
          Create Assessment
        </Button>
      </DialogActions>
    </Dialog>
  );
};
```

- [ ] **Step 5.3: Commit**

```bash
git add frontend/src/features/active_directory/components/
git commit -m "feat(ad-frontend): add AssessmentStatusBadge and CreateAssessmentDialog"
```

---

## Task 6: Assessment list page

**Context:** The entry point at `/active-directory`. Shows all assessments with status, domain count, finding count. Allows creating new assessments and starting/cancelling them.

**Files:**
- Create: `frontend/src/features/active_directory/pages/ADAssessmentsPage.tsx`

- [ ] **Step 6.1: Create ADAssessmentsPage.tsx**

```tsx
// frontend/src/features/active_directory/pages/ADAssessmentsPage.tsx
import React, { useState } from 'react';
import { useNavigate, useParams } from '@tanstack/react-router';
import {
  Box, Typography, Button, Table, TableHead, TableBody,
  TableRow, TableCell, TableContainer, Paper, IconButton,
  Tooltip, CircularProgress, Alert
} from '@mui/material';
import { Plus, Play, Square, Trash2, ChevronRight, Upload } from 'lucide-react';
import { useAssessments, useStartAssessment, useCancelAssessment, useDeleteAssessment } from '../api/adApi';
import { AssessmentStatusBadge } from '../components/AssessmentStatusBadge';
import { CreateAssessmentDialog } from '../components/CreateAssessmentDialog';
import { IngestDataDialog } from '../components/IngestDataDialog';

export const ADAssessmentsPage: React.FC = () => {
  const { projectSlug } = useParams({ strict: false }) as any;
  const navigate = useNavigate();
  const { data: assessments, isLoading, error } = useAssessments();
  const { mutate: start } = useStartAssessment();
  const { mutate: cancel } = useCancelAssessment();
  const { mutate: deleteA } = useDeleteAssessment();

  const [createOpen, setCreateOpen] = useState(false);
  const [ingestId, setIngestId] = useState<number | null>(null);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', pt: 10 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">Failed to load assessments: {String(error)}</Alert>;
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h5" sx={{ fontFamily: 'Orbitron', letterSpacing: 2, mb: 0.5 }}>
            AD INTELLIGENCE
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            Active Directory assessment and identity intelligence platform
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<Plus size={16} />}
          onClick={() => setCreateOpen(true)}
        >
          New Assessment
        </Button>
      </Box>

      {(!assessments || assessments.length === 0) ? (
        <Paper sx={{ p: 6, textAlign: 'center', opacity: 0.6 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>No assessments yet</Typography>
          <Typography variant="body2">
            Create a new assessment to begin identity infrastructure analysis
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Target Domain</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="center">Domains</TableCell>
                <TableCell align="center">Findings</TableCell>
                <TableCell align="center">Exposures</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(assessments || []).map((a) => (
                <TableRow key={a.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {a.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {a.target_domain}
                    </Typography>
                  </TableCell>
                  <TableCell><AssessmentStatusBadge status={a.status} /></TableCell>
                  <TableCell align="center">{a.domain_count ?? 0}</TableCell>
                  <TableCell align="center">{a.finding_count ?? 0}</TableCell>
                  <TableCell align="center">{a.exposure_count ?? 0}</TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      {new Date(a.created_at).toLocaleDateString()}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                      {['PENDING', 'FAILED', 'CANCELLED'].includes(a.status) && (
                        <Tooltip title="Start">
                          <IconButton size="small" onClick={() => start(a.id)}>
                            <Play size={16} />
                          </IconButton>
                        </Tooltip>
                      )}
                      {a.status === 'RUNNING' && (
                        <Tooltip title="Cancel">
                          <IconButton size="small" onClick={() => cancel(a.id)}>
                            <Square size={16} />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Tooltip title="Import Data">
                        <IconButton size="small" onClick={() => setIngestId(a.id)}>
                          <Upload size={16} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="View Detail">
                        <IconButton
                          size="small"
                          onClick={() => navigate({
                            to: `/${projectSlug}/active-directory/assessment/${a.id}`,
                          })}
                        >
                          <ChevronRight size={16} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => {
                            if (window.confirm('Delete this assessment?')) deleteA(a.id);
                          }}
                        >
                          <Trash2 size={16} />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <CreateAssessmentDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      />
      {ingestId !== null && (
        <IngestDataDialog
          open
          assessmentId={ingestId}
          onClose={() => setIngestId(null)}
        />
      )}
    </Box>
  );
};
```

- [ ] **Step 6.2: Create IngestDataDialog.tsx**

```tsx
// frontend/src/features/active_directory/components/IngestDataDialog.tsx
import React, { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Box, Typography, Select, MenuItem,
  FormControl, InputLabel, CircularProgress, Alert
} from '@mui/material';
import { useIngestFile } from '../api/adApi';

interface Props {
  open: boolean;
  assessmentId: number;
  onClose: () => void;
}

export const IngestDataDialog: React.FC<Props> = ({ open, assessmentId, onClose }) => {
  const [file, setFile] = useState<File | null>(null);
  const [type, setType] = useState('auto');
  const { mutate, isPending, error, isSuccess, data } = useIngestFile();

  const handleSubmit = () => {
    if (!file) return;
    mutate({ id: assessmentId, file, type });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ fontFamily: 'Orbitron', letterSpacing: 1 }}>
        IMPORT ASSESSMENT DATA
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          <FormControl fullWidth>
            <InputLabel>Data Type</InputLabel>
            <Select value={type} onChange={(e) => setType(e.target.value)} label="Data Type">
              <MenuItem value="auto">Auto-detect</MenuItem>
              <MenuItem value="bloodhound">BloodHound JSON export</MenuItem>
              <MenuItem value="ldap">ldapdomaindump JSON export</MenuItem>
            </Select>
          </FormControl>
          <Box
            component="label"
            sx={{
              border: '2px dashed rgba(255,255,255,0.2)',
              borderRadius: 1,
              p: 3,
              textAlign: 'center',
              cursor: 'pointer',
              '&:hover': { borderColor: 'primary.main' },
            }}
          >
            <input
              type="file"
              hidden
              accept=".json,.zip"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              {file ? file.name : 'Click to select file (.json or .zip archive)'}
            </Typography>
          </Box>
          {error && <Alert severity="error">{String(error)}</Alert>}
          {isSuccess && (
            <Alert severity="success">
              Ingestion complete — {JSON.stringify((data as any)?.summary)}
            </Alert>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Close</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={isPending || !file}
          startIcon={isPending ? <CircularProgress size={16} /> : null}
        >
          Import
        </Button>
      </DialogActions>
    </Dialog>
  );
};
```

- [ ] **Step 6.3: Commit**

```bash
git add frontend/src/features/active_directory/pages/ADAssessmentsPage.tsx \
        frontend/src/features/active_directory/components/IngestDataDialog.tsx
git commit -m "feat(ad-frontend): add ADAssessmentsPage and IngestDataDialog"
```

---

## Task 7: Assessment detail page with real-time progress

**Context:** Shows summary stats (domain count, findings by severity, exposure count), live progress events from the WebSocket, and navigation tabs to sub-pages.

**Files:**
- Create: `frontend/src/features/active_directory/pages/ADAssessmentDetailPage.tsx`

- [ ] **Step 7.1: Create ADAssessmentDetailPage.tsx**

```tsx
// frontend/src/features/active_directory/pages/ADAssessmentDetailPage.tsx
import React, { useEffect } from 'react';
import { useParams, useNavigate, Link } from '@tanstack/react-router';
import {
  Box, Typography, Grid, Paper, Chip, Button,
  CircularProgress, Alert, Tabs, Tab, List, ListItem, ListItemText
} from '@mui/material';
import { Share2, AlertTriangle, Globe, BarChart2 } from 'lucide-react';
import { useAssessmentDetail, useStartAssessment, useCancelAssessment } from '../api/adApi';
import { AssessmentStatusBadge } from '../components/AssessmentStatusBadge';
import { useADWebSocket } from '../hooks/useADWebSocket';
import { useADStore } from '../store/adStore';

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#ff003c',
  HIGH: '#ff6b35',
  MEDIUM: '#f7c59f',
  LOW: '#4ecdc4',
  INFO: '#aaa',
};

export const ADAssessmentDetailPage: React.FC = () => {
  const { assessmentId, projectSlug } = useParams({ strict: false }) as any;
  const id = Number(assessmentId);
  const navigate = useNavigate();

  const { data: assessment, isLoading } = useAssessmentDetail(id);
  const { mutate: start } = useStartAssessment();
  const { mutate: cancel } = useCancelAssessment();
  const { wsEvents, clearWSEvents, setActiveAssessmentId } = useADStore();

  useADWebSocket(id);

  useEffect(() => {
    setActiveAssessmentId(id);
    clearWSEvents();
    return () => setActiveAssessmentId(null);
  }, [id]);

  if (isLoading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', pt: 10 }}><CircularProgress /></Box>;
  }
  if (!assessment) {
    return <Alert severity="error">Assessment not found</Alert>;
  }

  const findingSummary = assessment.finding_summary || {};
  const exposureSummary = assessment.exposure_summary || {};

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h5" sx={{ fontFamily: 'Orbitron', letterSpacing: 2, mb: 0.5 }}>
            {assessment.name}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <Typography variant="body2" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
              {assessment.target_domain}
            </Typography>
            <AssessmentStatusBadge status={assessment.status} />
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {['PENDING', 'FAILED', 'CANCELLED'].includes(assessment.status) && (
            <Button variant="contained" onClick={() => start(id)}>Start Assessment</Button>
          )}
          {assessment.status === 'RUNNING' && (
            <Button variant="outlined" color="error" onClick={() => cancel(id)}>Cancel</Button>
          )}
          <Button
            variant="outlined"
            startIcon={<Share2 size={16} />}
            onClick={() => navigate({ to: `/${projectSlug}/active-directory/assessment/${id}/graph` })}
          >
            Graph Explorer
          </Button>
        </Box>
      </Box>

      {/* Summary KPIs */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[
          { label: 'Domains', value: assessment.domains?.length ?? 0, icon: <Globe size={20} /> },
          { label: 'Findings', value: Object.values(findingSummary).reduce((a, b) => a + b, 0), icon: <AlertTriangle size={20} /> },
          { label: 'Exposures', value: Object.values(exposureSummary).reduce((a, b) => a + b, 0), icon: <Share2 size={20} /> },
        ].map((kpi) => (
          <Grid item xs={12} sm={4} key={kpi.label}>
            <Paper sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{ color: 'primary.main' }}>{kpi.icon}</Box>
              <Box>
                <Typography variant="h4" sx={{ fontFamily: 'Orbitron', fontWeight: 900 }}>
                  {kpi.value}
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  {kpi.label}
                </Typography>
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Findings by severity */}
      {Object.keys(findingSummary).length > 0 && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="subtitle2" sx={{ mb: 1, fontFamily: 'Orbitron', fontSize: '0.75rem' }}>
            FINDINGS BY SEVERITY
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {Object.entries(findingSummary).map(([severity, count]) => (
              <Chip
                key={severity}
                label={`${severity}: ${count}`}
                size="small"
                sx={{
                  bgcolor: SEVERITY_COLORS[severity] + '22',
                  color: SEVERITY_COLORS[severity],
                  border: `1px solid ${SEVERITY_COLORS[severity]}44`,
                  fontFamily: 'monospace',
                }}
              />
            ))}
          </Box>
        </Paper>
      )}

      {/* Navigation to sub-pages */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {[
            { label: 'Graph Explorer', path: `/active-directory/assessment/${id}/graph` },
            { label: 'Trust Analytics', path: `/active-directory/assessment/${id}/trusts` },
            { label: 'Exposure Dashboard', path: `/active-directory/assessment/${id}/exposures` },
          ].map((nav) => (
            <Button
              key={nav.label}
              variant="outlined"
              size="small"
              onClick={() => navigate({ to: `/${projectSlug}${nav.path}` })}
            >
              {nav.label}
            </Button>
          ))}
        </Box>
      </Paper>

      {/* Live progress events */}
      {wsEvents.length > 0 && (
        <Paper sx={{ p: 2, maxHeight: 300, overflow: 'auto' }}>
          <Typography variant="subtitle2" sx={{ mb: 1, fontFamily: 'Orbitron', fontSize: '0.75rem' }}>
            LIVE PROGRESS
          </Typography>
          <List dense>
            {wsEvents.slice().reverse().map((ev, idx) => (
              <ListItem key={idx} sx={{ py: 0.25 }}>
                <ListItemText
                  primary={ev.message || ev.type}
                  secondary={ev.phase}
                  primaryTypographyProps={{ variant: 'body2', sx: { fontFamily: 'monospace' } }}
                  secondaryTypographyProps={{ variant: 'caption' }}
                />
              </ListItem>
            ))}
          </List>
        </Paper>
      )}
    </Box>
  );
};
```

- [ ] **Step 7.2: Commit**

```bash
git add frontend/src/features/active_directory/pages/ADAssessmentDetailPage.tsx
git commit -m "feat(ad-frontend): add ADAssessmentDetailPage with KPIs, finding summary, and live WebSocket progress"
```

---

## Task 8: Graph Explorer page (Cytoscape.js)

**Context:** The flagship interface. Uses `react-cytoscapejs` with `cytoscape-dagre` for hierarchical layout. Domain nodes are sized by DC count. Trust edges are colored by direction and type. Side panel opens on node click showing entity details.

**Files:**
- Create: `frontend/src/features/active_directory/pages/ADGraphExplorerPage.tsx`
- Create: `frontend/src/features/active_directory/components/GraphControlBar.tsx`

- [ ] **Step 8.1: Create GraphControlBar.tsx**

```tsx
// frontend/src/features/active_directory/components/GraphControlBar.tsx
import React from 'react';
import { Box, ToggleButtonGroup, ToggleButton, Tooltip, TextField, InputAdornment } from '@mui/material';
import { Network, GitBranch, LayoutGrid, Search } from 'lucide-react';
import { useADStore } from '../store/adStore';

interface Props {
  onSearch?: (query: string) => void;
  onFitView?: () => void;
}

export const GraphControlBar: React.FC<Props> = ({ onSearch, onFitView }) => {
  const { graphLayout, setGraphLayout } = useADStore();
  const [searchVal, setSearchVal] = React.useState('');

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchVal(e.target.value);
    onSearch?.(e.target.value);
  };

  return (
    <Box sx={{
      display: 'flex', gap: 2, alignItems: 'center',
      p: 1.5, borderBottom: '1px solid rgba(255,255,255,0.08)',
    }}>
      <ToggleButtonGroup
        value={graphLayout}
        exclusive
        onChange={(_e, val) => val && setGraphLayout(val)}
        size="small"
      >
        <Tooltip title="Hierarchical (Dagre)">
          <ToggleButton value="dagre"><Network size={16} /></ToggleButton>
        </Tooltip>
        <Tooltip title="Radial">
          <ToggleButton value="radial"><GitBranch size={16} /></ToggleButton>
        </Tooltip>
        <Tooltip title="Grid">
          <ToggleButton value="grid"><LayoutGrid size={16} /></ToggleButton>
        </Tooltip>
      </ToggleButtonGroup>
      <TextField
        size="small"
        placeholder="Search nodes..."
        value={searchVal}
        onChange={handleSearch}
        sx={{ minWidth: 200 }}
        InputProps={{
          startAdornment: <InputAdornment position="start"><Search size={14} /></InputAdornment>,
        }}
      />
    </Box>
  );
};
```

- [ ] **Step 8.2: Create ADGraphExplorerPage.tsx**

```tsx
// frontend/src/features/active_directory/pages/ADGraphExplorerPage.tsx
import React, { useCallback, useRef, useState } from 'react';
import { useParams } from '@tanstack/react-router';
import { Box, Typography, Paper, CircularProgress, Alert, Chip, Divider } from '@mui/material';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import { useDomainGraph, useExposureGraph } from '../api/adApi';
import { useADStore } from '../store/adStore';
import { GraphControlBar } from '../components/GraphControlBar';
import { useADWebSocket } from '../hooks/useADWebSocket';

cytoscape.use(dagre);

const GRAPH_STYLE: cytoscape.Stylesheet[] = [
  {
    selector: 'node[type="domain"]',
    style: {
      'background-color': '#00f3ff',
      'border-color': '#00f3ff',
      'border-width': 2,
      'label': 'data(label)',
      'color': '#ffffff',
      'font-size': 10,
      'text-valign': 'bottom',
      'text-margin-y': 4,
      'width': 'mapData(dc_count, 0, 10, 30, 60)',
      'height': 'mapData(dc_count, 0, 10, 30, 60)',
    },
  },
  {
    selector: 'node[type="domain"][forest_root="true"]',
    style: {
      'background-color': '#7b2fff',
      'border-color': '#7b2fff',
      'border-width': 3,
    },
  },
  {
    selector: 'node[type="exposure"]',
    style: {
      'background-color': '#ff6b35',
      'shape': 'diamond',
      'label': 'data(label)',
      'color': '#ffffff',
      'font-size': 9,
      'text-valign': 'bottom',
      'width': 24,
      'height': 24,
    },
  },
  {
    selector: 'edge[direction="BIDIRECTIONAL"]',
    style: {
      'line-color': '#ff003c',
      'target-arrow-color': '#ff003c',
      'target-arrow-shape': 'triangle',
      'source-arrow-shape': 'triangle',
      'source-arrow-color': '#ff003c',
      'curve-style': 'bezier',
      'width': 2,
    },
  },
  {
    selector: 'edge[direction="OUTBOUND"]',
    style: {
      'line-color': '#00f3ff',
      'target-arrow-color': '#00f3ff',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'width': 1.5,
    },
  },
  {
    selector: 'edge',
    style: {
      'line-color': 'rgba(255,255,255,0.3)',
      'curve-style': 'bezier',
      'width': 1,
    },
  },
  {
    selector: ':selected',
    style: {
      'border-color': '#ffff00',
      'border-width': 3,
      'line-color': '#ffff00',
    },
  },
];

const LAYOUT_MAP: Record<string, cytoscape.LayoutOptions> = {
  dagre: { name: 'dagre', rankDir: 'TB', nodeSep: 50, rankSep: 80 } as any,
  radial: { name: 'circle', radius: 200 } as any,
  grid: { name: 'grid' },
};

type GraphView = 'domains' | 'exposures';

export const ADGraphExplorerPage: React.FC = () => {
  const { assessmentId } = useParams({ strict: false }) as any;
  const id = Number(assessmentId);
  const [view, setView] = useState<GraphView>('domains');
  const { graphLayout, selectedNodeId, setSelectedNodeId } = useADStore();
  const cyRef = useRef<cytoscape.Core | null>(null);

  useADWebSocket(id);

  const { data: domainGraph, isLoading: loadingDomains } = useDomainGraph(id);
  const { data: exposureGraph, isLoading: loadingExposures } = useExposureGraph(id);

  const graphData = view === 'domains' ? domainGraph : exposureGraph;
  const isLoading = view === 'domains' ? loadingDomains : loadingExposures;

  const elements = graphData
    ? [...(graphData.nodes || []), ...(graphData.edges || [])]
    : [];

  const selectedNode = selectedNodeId && graphData
    ? graphData.nodes.find((n) => n.data.id === selectedNodeId)?.data
    : null;

  const handleSearch = useCallback((query: string) => {
    if (!cyRef.current || !query) return;
    cyRef.current.nodes().removeClass('highlighted');
    if (query.length >= 2) {
      cyRef.current
        .nodes(`[label @*= "${query}"]`)
        .addClass('highlighted');
    }
  }, []);

  if (isLoading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', pt: 10 }}><CircularProgress /></Box>;
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, px: 2, py: 1 }}>
        <Typography variant="h6" sx={{ fontFamily: 'Orbitron', fontSize: '0.9rem', letterSpacing: 2 }}>
          GRAPH EXPLORER
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {(['domains', 'exposures'] as GraphView[]).map((v) => (
            <Chip
              key={v}
              label={v.toUpperCase()}
              size="small"
              variant={view === v ? 'filled' : 'outlined'}
              onClick={() => setView(v)}
              sx={{ cursor: 'pointer', fontFamily: 'monospace', fontSize: '0.7rem' }}
            />
          ))}
        </Box>
      </Box>

      <GraphControlBar onSearch={handleSearch} onFitView={() => cyRef.current?.fit()} />

      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Box sx={{ flex: 1, bgcolor: '#0a0a0f', position: 'relative' }}>
          {elements.length === 0 ? (
            <Box sx={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Alert severity="info" sx={{ maxWidth: 400 }}>
                No graph data yet. Start an assessment or import data to populate the graph.
              </Alert>
            </Box>
          ) : (
            <CytoscapeComponent
              elements={elements}
              style={{ width: '100%', height: '100%' }}
              stylesheet={GRAPH_STYLE}
              layout={LAYOUT_MAP[graphLayout]}
              cy={(cy) => {
                cyRef.current = cy;
                cy.on('tap', 'node', (e) => {
                  setSelectedNodeId(e.target.id());
                });
                cy.on('tap', (e) => {
                  if (e.target === cy) setSelectedNodeId(null);
                });
              }}
            />
          )}
        </Box>

        {/* Side panel */}
        {selectedNode && (
          <Paper sx={{ width: 280, overflow: 'auto', borderRadius: 0, borderLeft: '1px solid rgba(255,255,255,0.08)' }}>
            <Box sx={{ p: 2 }}>
              <Typography variant="subtitle2" sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem', letterSpacing: 1, mb: 1 }}>
                {String(selectedNode.type || '').toUpperCase()} DETAILS
              </Typography>
              <Divider sx={{ mb: 1.5 }} />
              {Object.entries(selectedNode).map(([k, v]) => (
                <Box key={k} sx={{ mb: 0.75 }}>
                  <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.65rem' }}>
                    {k}
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
                    {String(v ?? '—')}
                  </Typography>
                </Box>
              ))}
            </Box>
          </Paper>
        )}
      </Box>
    </Box>
  );
};
```

- [ ] **Step 8.3: Commit**

```bash
git add frontend/src/features/active_directory/pages/ADGraphExplorerPage.tsx \
        frontend/src/features/active_directory/components/GraphControlBar.tsx
git commit -m "feat(ad-frontend): add ADGraphExplorerPage with Cytoscape.js (dagre layout, node selection, side panel)"
```

---

## Task 9: Trust Analytics and Exposure Dashboard pages

**Files:**
- Create: `frontend/src/features/active_directory/pages/ADTrustAnalyticsPage.tsx`
- Create: `frontend/src/features/active_directory/pages/ADExposureDashboardPage.tsx`

- [ ] **Step 9.1: Create ADTrustAnalyticsPage.tsx**

```tsx
// frontend/src/features/active_directory/pages/ADTrustAnalyticsPage.tsx
import React from 'react';
import { useParams } from '@tanstack/react-router';
import {
  Box, Typography, Paper, Table, TableHead, TableBody,
  TableRow, TableCell, Chip, CircularProgress, Alert, LinearProgress
} from '@mui/material';
import { useTrusts } from '../api/adApi';

const DIRECTION_COLOR: Record<string, string> = {
  BIDIRECTIONAL: '#ff003c',
  OUTBOUND: '#00f3ff',
  INBOUND: '#7b2fff',
};

export const ADTrustAnalyticsPage: React.FC = () => {
  const { assessmentId } = useParams({ strict: false }) as any;
  const id = Number(assessmentId);
  const { data: trusts, isLoading, error } = useTrusts(id);

  if (isLoading) return <Box sx={{ p: 4 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{String(error)}</Alert>;

  const sorted = [...(trusts || [])].sort((a, b) => b.risk_score - a.risk_score);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" sx={{ fontFamily: 'Orbitron', letterSpacing: 2, mb: 3 }}>
        TRUST ANALYTICS
      </Typography>

      {!sorted.length ? (
        <Alert severity="info">No trust relationships discovered yet.</Alert>
      ) : (
        <Paper>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Source Domain</TableCell>
                <TableCell>Target Domain</TableCell>
                <TableCell>Direction</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Transitive</TableCell>
                <TableCell>Risk Score</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sorted.map((trust) => (
                <TableRow key={trust.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {trust.source_domain_fqdn}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {trust.target_domain_name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={trust.direction}
                      size="small"
                      sx={{
                        color: DIRECTION_COLOR[trust.direction] || '#aaa',
                        borderColor: DIRECTION_COLOR[trust.direction] || '#aaa',
                        border: '1px solid',
                        bgcolor: 'transparent',
                        fontFamily: 'monospace',
                        fontSize: '0.7rem',
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{trust.trust_type.replace('_', ' ')}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={trust.is_transitive ? 'YES' : 'NO'}
                      size="small"
                      color={trust.is_transitive ? 'warning' : 'default'}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell sx={{ minWidth: 120 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={trust.risk_score}
                        sx={{
                          flex: 1, height: 6, borderRadius: 3,
                          bgcolor: 'rgba(255,255,255,0.1)',
                          '& .MuiLinearProgress-bar': {
                            bgcolor: trust.risk_score > 70 ? '#ff003c'
                              : trust.risk_score > 40 ? '#ff6b35' : '#4ecdc4',
                          },
                        }}
                      />
                      <Typography variant="caption" sx={{ minWidth: 30 }}>
                        {trust.risk_score.toFixed(0)}
                      </Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Box>
  );
};
```

- [ ] **Step 9.2: Create ADExposureDashboardPage.tsx**

```tsx
// frontend/src/features/active_directory/pages/ADExposureDashboardPage.tsx
import React from 'react';
import { useParams } from '@tanstack/react-router';
import {
  Box, Typography, Paper, Grid, Chip, CircularProgress,
  Alert, Table, TableHead, TableBody, TableRow, TableCell, LinearProgress
} from '@mui/material';
import { useExposures } from '../api/adApi';

const TYPE_COLOR: Record<string, string> = {
  ADFS: '#7b2fff',
  OWA: '#00f3ff',
  EXCHANGE: '#4ecdc4',
  VPN: '#ff6b35',
  LDAP: '#f7c59f',
  KERBEROS: '#ff003c',
  WINRM: '#ffd700',
  RDP: '#ff69b4',
  SMB: '#87ceeb',
  OTHER: '#aaa',
};

export const ADExposureDashboardPage: React.FC = () => {
  const { assessmentId } = useParams({ strict: false }) as any;
  const id = Number(assessmentId);
  const { data: exposures, isLoading, error } = useExposures(id);

  if (isLoading) return <Box sx={{ p: 4 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{String(error)}</Alert>;

  const sorted = [...(exposures || [])].sort((a, b) => b.risk_score - a.risk_score);

  // Group by type for summary
  const byType = sorted.reduce<Record<string, number>>((acc, e) => {
    acc[e.exposure_type] = (acc[e.exposure_type] || 0) + 1;
    return acc;
  }, {});

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" sx={{ fontFamily: 'Orbitron', letterSpacing: 2, mb: 3 }}>
        EXPOSURE DASHBOARD
      </Typography>

      {/* Type summary chips */}
      {Object.keys(byType).length > 0 && (
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 3 }}>
          {Object.entries(byType).map(([type, count]) => (
            <Chip
              key={type}
              label={`${type} (${count})`}
              size="small"
              sx={{
                bgcolor: TYPE_COLOR[type] + '22',
                color: TYPE_COLOR[type],
                border: `1px solid ${TYPE_COLOR[type]}44`,
                fontFamily: 'monospace',
              }}
            />
          ))}
        </Box>
      )}

      {!sorted.length ? (
        <Alert severity="info">No exposures discovered yet.</Alert>
      ) : (
        <Paper>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Hostname</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>IP Address</TableCell>
                <TableCell>Correlated Domain</TableCell>
                <TableCell>Risk Score</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sorted.map((exp) => (
                <TableRow key={exp.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {exp.hostname}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={exp.exposure_type}
                      size="small"
                      sx={{
                        color: TYPE_COLOR[exp.exposure_type] || '#aaa',
                        bgcolor: (TYPE_COLOR[exp.exposure_type] || '#aaa') + '22',
                        fontFamily: 'monospace',
                        fontSize: '0.7rem',
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                      {exp.ip_address || '—'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {exp.correlated_domain_fqdn || '—'}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ minWidth: 120 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={exp.risk_score}
                        sx={{
                          flex: 1, height: 6, borderRadius: 3,
                          bgcolor: 'rgba(255,255,255,0.1)',
                          '& .MuiLinearProgress-bar': {
                            bgcolor: exp.risk_score > 80 ? '#ff003c'
                              : exp.risk_score > 60 ? '#ff6b35' : '#4ecdc4',
                          },
                        }}
                      />
                      <Typography variant="caption" sx={{ minWidth: 30 }}>
                        {exp.risk_score.toFixed(0)}
                      </Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Box>
  );
};
```

- [ ] **Step 9.3: Commit**

```bash
git add frontend/src/features/active_directory/pages/ADTrustAnalyticsPage.tsx \
        frontend/src/features/active_directory/pages/ADExposureDashboardPage.tsx
git commit -m "feat(ad-frontend): add ADTrustAnalyticsPage and ADExposureDashboardPage"
```

---

## Task 10: Feature index and router integration

**Context:** Export all pages from the feature index, add 5 routes to `router.tsx`, and confirm that the Shell nav entry appears via `manifest.ui.menu_item`.

**Files:**
- Create: `frontend/src/features/active_directory/index.ts`
- Modify: `frontend/src/router.tsx`

- [ ] **Step 10.1: Create feature index.ts**

```typescript
// frontend/src/features/active_directory/index.ts
export { ADAssessmentsPage } from './pages/ADAssessmentsPage';
export { ADAssessmentDetailPage } from './pages/ADAssessmentDetailPage';
export { ADGraphExplorerPage } from './pages/ADGraphExplorerPage';
export { ADTrustAnalyticsPage } from './pages/ADTrustAnalyticsPage';
export { ADExposureDashboardPage } from './pages/ADExposureDashboardPage';
```

- [ ] **Step 10.2: Add lazy route imports to router.tsx**

Add after the existing lazy imports (around line 47 in router.tsx):

```typescript
const ADAssessmentsPage = lazyRouteComponent(() =>
  import('./features/active_directory').then(m => ({ default: m.ADAssessmentsPage })));
const ADAssessmentDetailPage = lazyRouteComponent(() =>
  import('./features/active_directory').then(m => ({ default: m.ADAssessmentDetailPage })));
const ADGraphExplorerPage = lazyRouteComponent(() =>
  import('./features/active_directory').then(m => ({ default: m.ADGraphExplorerPage })));
const ADTrustAnalyticsPage = lazyRouteComponent(() =>
  import('./features/active_directory').then(m => ({ default: m.ADTrustAnalyticsPage })));
const ADExposureDashboardPage = lazyRouteComponent(() =>
  import('./features/active_directory').then(m => ({ default: m.ADExposureDashboardPage })));
```

- [ ] **Step 10.3: Add route definitions to router.tsx**

Add after `pluginsRoute`:

```typescript
const adAssessmentsRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: 'active-directory',
  component: ADAssessmentsPage,
});

const adAssessmentDetailRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: 'active-directory/assessment/$assessmentId',
  component: ADAssessmentDetailPage,
});

const adGraphExplorerRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: 'active-directory/assessment/$assessmentId/graph',
  component: ADGraphExplorerPage,
});

const adTrustAnalyticsRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: 'active-directory/assessment/$assessmentId/trusts',
  component: ADTrustAnalyticsPage,
});

const adExposureDashboardRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: 'active-directory/assessment/$assessmentId/exposures',
  component: ADExposureDashboardPage,
});
```

- [ ] **Step 10.4: Add routes to routeTree**

In the `routeTree` declaration, add inside `projectRoute.addChildren([...])`:

```typescript
    adAssessmentsRoute,
    adAssessmentDetailRoute,
    adGraphExplorerRoute,
    adTrustAnalyticsRoute,
    adExposureDashboardRoute,
```

- [ ] **Step 10.5: Build frontend and verify no TypeScript errors**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: Build completes. Zero TypeScript errors.

- [ ] **Step 10.6: Commit**

```bash
git add frontend/src/features/active_directory/index.ts \
        frontend/src/router.tsx
git commit -m "feat(ad-frontend): add 5 AD routes to router.tsx and feature index"
```

---

## Task 11: Verify nav item appears and routes resolve

**Context:** The Shell.tsx reads from `/api/plugins/registry/`. If the plugin is registered in the `Plugin` model with `manifest.ui.menu_item = "AD Intelligence"`, the nav item will appear as a child of "Plugins".

- [ ] **Step 11.1: Verify registry returns AD plugin**

```bash
cd web && python manage.py shell -c "
from plugins.models import Plugin
p = Plugin.objects.filter(slug='active_directory').first()
print('Plugin:', p)
print('manifest.ui:', p.manifest.get('ui') if p else 'NOT FOUND')
"
```

Expected:
```
Plugin: Active Directory Intelligence (1.0.0)
manifest.ui: {'menu_item': 'AD Intelligence', 'menu_path': '/active-directory', 'components': []}
```

- [ ] **Step 11.2: Verify /api/plugins/registry/ endpoint includes AD plugin**

```bash
curl -s http://localhost:8000/api/plugins/registry/ | python -m json.tool | grep -A5 active_directory
```

Expected: `"menu_item": "AD Intelligence"` in the response.

- [ ] **Step 11.3: Start frontend dev server and verify pages render**

```bash
cd frontend && npm run dev
```

Navigate to `http://localhost:5173/<projectSlug>/active-directory` and verify:
- Assessment list page renders (empty table or existing assessments)
- "Plugins" nav item expands showing "AD Intelligence" child

- [ ] **Step 11.4: Commit**

```bash
git add .
git commit -m "feat(ad-frontend): Phase 3 complete — all AD pages integrated and rendering"
```

---

## Phase 3 Complete

The plugin frontend now provides:
- **Assessment management** at `/active-directory` — create, list, start, cancel, import data
- **Assessment detail** at `/active-directory/assessment/{id}` — KPIs, findings summary, live WebSocket progress
- **Graph Explorer** at `/active-directory/assessment/{id}/graph` — Cytoscape.js with dagre/radial/grid layouts, node selection, entity side panel
- **Trust Analytics** at `/active-directory/assessment/{id}/trusts` — trust table with risk scores
- **Exposure Dashboard** at `/active-directory/assessment/{id}/exposures` — exposure table with type chips and risk scores
- **Nav integration** via `manifest.ui.menu_item` → Shell's dynamic plugin nav

**Next:** Phase 4 — Evidence, Reporting & Testing (`2026-05-24-ad-plugin-phase4-reporting.md`)
- Evidence snapshots (graph + timestamped findings)
- PDF executive + technical report generation
- JSON/PNG/SVG export
- Performance optimizations (graph virtualization, Web Workers for layout)
- Multi-tenancy / RBAC
- Full test suite (workflow, API, ingestion, WebSocket, UI)
