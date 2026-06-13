# AD Plugin Phase 7 & 8 — Enterprise Graph Visualization + Realtime Streaming

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the AD Intelligence plugin from a basic Cytoscape canvas into an enterprise-grade graph explorer with semantic styling for all 17 node types, multi-layout support, search, focus mode, node detail panels, live workflow progress, and batched WebSocket-driven graph refresh.

**Architecture:** Phase 7 builds entirely inside `r3ngine-plugins/active_directory/ui/src/` — new `graphs/` and updated `components/` files, with `ADGraphExplorerPage.tsx` refactored as the flagship interface. Phase 8 introduces a separate `realtimeStore.ts`, a batching WS event bus replacing the existing `useADWebSocket`, and a `WorkflowProgressPanel` that consumes live events. The backend `temporal_exports.py` gains six new event type emissions.

**Tech Stack:** cytoscape 3.33+, cytoscape-dagre, cytoscape-fcose, react-cytoscapejs, zustand 5, @tanstack/react-query 5, @mui/material 6, lucide-react, TypeScript strict

---

## File Map

### New files (plugin UI — `r3ngine-plugins/active_directory/ui/src/`)
| File | Responsibility |
|------|---------------|
| `graphs/cytoscapeExtensions.ts` | Register cytoscape-dagre + cytoscape-fcose once at import time |
| `graphs/cytoscapeStyles.ts` | All stylesheet rules + `NODE_COLORS` map for all 17 AD node types |
| `graphs/cytoscapeLayouts.ts` | Layout config objects for dagre, fcose, circle, concentric, grid |
| `graphs/useGraphSearch.ts` | Derive matching node IDs from search query over current elements |
| `graphs/useGraphFocus.ts` | Derive connected node IDs for focus/dim mode |
| `graphs/useGraphViewport.ts` | Save/restore cytoscape pan+zoom across data refreshes |
| `components/GraphNodePanel.tsx` | Side panel rendering all properties of the selected node |
| `components/GraphLegend.tsx` | Collapsible color/shape legend for node types |
| `components/GraphToolbar.tsx` | Full toolbar: layout selector, search, fit, focus toggle, PNG export |
| `store/realtimeStore.ts` | Separate Zustand store for WS streaming state per Phase 14 spec |
| `hooks/useWsEventBus.ts` | Batched WS hook (150ms flush) routing messages to realtimeStore |
| `components/WorkflowProgressPanel.tsx` | Sticky progress bar + event log shown while assessment RUNNING |

### Modified files
| File | What changes |
|------|-------------|
| `types/index.ts` | Add `LayoutName`, 6 new `WSEventType` values, typed payload interfaces |
| `store/adStore.ts` | Add `focusMode`, `searchQuery`, `selectedNodeData` fields |
| `pages/ADGraphExplorerPage.tsx` | Full rewrite using all new graph primitives |
| `pages/ADAssessmentDetailPage.tsx` | Replace `useADWebSocket` with `useWsEventBus`, add `WorkflowProgressPanel` |
| `package.json` | Add `cytoscape-dagre`, `cytoscape-fcose` to `dependencies` |
| `backend/temporal_exports.py` | Emit `workflow_progress`, `finding_detected`, `trust_discovered`, `identity_discovered`, `graph_updated`, `correlation_completed` |

### Files to delete
| File | Reason |
|------|--------|
| `components/GraphControlBar.tsx` | Replaced by `GraphToolbar.tsx` |
| `hooks/useADWebSocket.ts` | Replaced by `hooks/useWsEventBus.ts` |

---

## Phase 7: Enterprise Graph Visualization

---

### Task 1: Install layout extensions and register them

**Files:**
- Modify: `r3ngine-plugins/active_directory/ui/package.json`
- Create: `r3ngine-plugins/active_directory/ui/src/graphs/cytoscapeExtensions.ts`

- [ ] **Step 1: Add layout deps to package.json**

Open `r3ngine-plugins/active_directory/ui/package.json`. Add to `dependencies`:

```json
{
  "name": "active-directory-ui",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "build": "vite build",
    "dev": "vite"
  },
  "peerDependencies": {
    "@mui/material": "^6.0.0",
    "@mui/icons-material": "^6.0.0",
    "lucide-react": "^0.400.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "devDependencies": {
    "@types/cytoscape": "^3.19.0",
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.100.9",
    "cytoscape": "^3.33.3",
    "cytoscape-dagre": "^2.5.0",
    "cytoscape-fcose": "^2.2.0",
    "react-cytoscapejs": "^2.0.0",
    "zustand": "^5.0.0"
  }
}
```

- [ ] **Step 2: Run npm install**

```bash
cd r3ngine-plugins/active_directory/ui
npm install
```

Expected: `added N packages` with no errors. `node_modules/cytoscape-dagre/` and `node_modules/cytoscape-fcose/` appear.

- [ ] **Step 3: Create cytoscapeExtensions.ts**

Create `r3ngine-plugins/active_directory/ui/src/graphs/cytoscapeExtensions.ts`:

```typescript
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import fcose from 'cytoscape-fcose';

// Register layout extensions exactly once. Importing this module is idempotent.
cytoscape.use(dagre);
cytoscape.use(fcose);

export {};
```

- [ ] **Step 4: Add type declarations for untyped packages**

Create `r3ngine-plugins/active_directory/ui/src/graphs/cytoscapeExtensions.d.ts`:

```typescript
declare module 'cytoscape-dagre' {
  const ext: cytoscape.Ext;
  export default ext;
}
declare module 'cytoscape-fcose' {
  const ext: cytoscape.Ext;
  export default ext;
}
```

- [ ] **Step 5: Verify build still passes**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected: `✓ built in` with no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/package.json active_directory/ui/package-lock.json active_directory/ui/src/graphs/
git commit -m "feat(ad-ui): install cytoscape-dagre + cytoscape-fcose layout extensions"
```

---

### Task 2: Create cytoscapeStyles.ts with full semantic styling

**Files:**
- Create: `r3ngine-plugins/active_directory/ui/src/graphs/cytoscapeStyles.ts`

- [ ] **Step 1: Create the file**

Create `r3ngine-plugins/active_directory/ui/src/graphs/cytoscapeStyles.ts`:

```typescript
import type { Stylesheet } from 'cytoscape';

export const NODE_COLORS: Record<string, string> = {
  ADDomain: '#00f3ff',
  ADForest: '#00b4d8',
  ADOU: '#48cae4',
  ADUser: '#7c4dff',
  ADGroup: '#ff6d00',
  ADComputer: '#00c853',
  ADService: '#76ff03',
  ADCertificate: '#ffd600',
  ADTrust: '#f06292',
  ADSubnet: '#4fc3f7',
  ADSite: '#29b6f6',
  ADPolicy: '#ab47bc',
  ADExposure: '#ff1744',
  ADFinding: '#ff5252',
  ADIdentityProvider: '#ec407a',
  ADVPNGateway: '#ff7043',
  ADAuthService: '#ff8a65',
};

export const NODE_SHAPES: Record<string, string> = {
  ADDomain: '⬡', ADForest: '⬡', ADOU: '▬', ADUser: '●', ADGroup: '■',
  ADComputer: '▬', ADService: '⬠', ADCertificate: '◆', ADTrust: '●',
  ADSubnet: '▬', ADSite: '▬', ADPolicy: '■', ADExposure: '▲',
  ADFinding: '★', ADIdentityProvider: '●', ADVPNGateway: '⬠', ADAuthService: '▬',
};

export const CYTOSCAPE_STYLESHEET: Stylesheet[] = [
  // ── Base node ──────────────────────────────────────────────────────────────
  {
    selector: 'node',
    style: {
      label: 'data(label)',
      'background-color': '#1a237e',
      color: '#fff',
      'font-size': 10,
      'text-valign': 'center',
      'text-halign': 'center',
      'text-wrap': 'truncate',
      'text-max-width': '80px',
      width: 36,
      height: 36,
    },
  },
  // ── Typed node styles ──────────────────────────────────────────────────────
  { selector: 'node[type="ADDomain"]',           style: { 'background-color': '#00f3ff', color: '#000', shape: 'hexagon',          width: 56, height: 56, 'font-size': 11, 'font-weight': 'bold' } },
  { selector: 'node[type="ADForest"]',           style: { 'background-color': '#00b4d8', color: '#000', shape: 'hexagon',          width: 64, height: 64, 'font-size': 12, 'font-weight': 'bold' } },
  { selector: 'node[type="ADOU"]',               style: { 'background-color': '#48cae4', color: '#000', shape: 'round-rectangle'                                                                    } },
  { selector: 'node[type="ADUser"]',             style: { 'background-color': '#7c4dff',               shape: 'ellipse'                                                                             } },
  { selector: 'node[type="ADGroup"]',            style: { 'background-color': '#ff6d00',               shape: 'rectangle'                                                                           } },
  { selector: 'node[type="ADComputer"]',         style: { 'background-color': '#00c853',               shape: 'round-rectangle'                                                                     } },
  { selector: 'node[type="ADService"]',          style: { 'background-color': '#76ff03', color: '#000', shape: 'pentagon'                                                                           } },
  { selector: 'node[type="ADCertificate"]',      style: { 'background-color': '#ffd600', color: '#000', shape: 'diamond',          width: 44, height: 44                                           } },
  { selector: 'node[type="ADTrust"]',            style: { 'background-color': '#f06292',               shape: 'ellipse'                                                                             } },
  { selector: 'node[type="ADSubnet"]',           style: { 'background-color': '#4fc3f7', color: '#000', shape: 'round-rectangle'                                                                    } },
  { selector: 'node[type="ADSite"]',             style: { 'background-color': '#29b6f6', color: '#000', shape: 'round-rectangle'                                                                    } },
  { selector: 'node[type="ADPolicy"]',           style: { 'background-color': '#ab47bc',               shape: 'rectangle'                                                                           } },
  { selector: 'node[type="ADExposure"]',         style: { 'background-color': '#ff1744',               shape: 'triangle',          width: 48, height: 48                                           } },
  { selector: 'node[type="ADFinding"]',          style: { 'background-color': '#ff5252',               shape: 'star',              width: 48, height: 48                                           } },
  { selector: 'node[type="ADIdentityProvider"]', style: { 'background-color': '#ec407a',               shape: 'ellipse'                                                                             } },
  { selector: 'node[type="ADVPNGateway"]',       style: { 'background-color': '#ff7043',               shape: 'pentagon'                                                                            } },
  { selector: 'node[type="ADAuthService"]',      style: { 'background-color': '#ff8a65',               shape: 'round-rectangle'                                                                     } },
  // ── Compound / group parent nodes ─────────────────────────────────────────
  {
    selector: 'node:parent',
    style: {
      'background-opacity': 0.05,
      'border-width': 1,
      'border-style': 'dashed',
      'border-color': 'rgba(255,255,255,0.2)',
      'text-valign': 'top',
      'font-size': 9,
      color: 'rgba(255,255,255,0.4)',
      padding: '20px',
      label: 'data(label)',
    },
  },
  // ── Edges ──────────────────────────────────────────────────────────────────
  {
    selector: 'edge',
    style: {
      'line-color': 'rgba(255,255,255,0.15)',
      'target-arrow-color': 'rgba(255,255,255,0.3)',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'font-size': 8,
      label: 'data(label)',
      color: 'rgba(255,255,255,0.35)',
      'text-rotation': 'autorotate',
      width: 1,
    },
  },
  { selector: 'edge[type="AD_TRUSTS"]',      style: { 'line-color': '#f06292', 'line-style': 'dashed', width: 2 } },
  { selector: 'edge[type="AD_EXPOSES"]',     style: { 'line-color': '#ff1744',                         width: 2 } },
  { selector: 'edge[type="AD_MEMBER_OF"]',   style: { 'line-color': 'rgba(124,77,255,0.5)'                     } },
  { selector: 'edge[type="AD_AUTHENTICATES_TO"]', style: { 'line-color': '#ec407a', 'line-style': 'dotted'     } },
  { selector: 'edge[type="AD_ROUTES_THROUGH"]',   style: { 'line-color': '#ff7043', 'line-style': 'dotted'     } },
  // ── Interaction states ─────────────────────────────────────────────────────
  { selector: 'node.highlighted', style: { 'border-width': 3, 'border-color': '#fff', opacity: 1 } },
  { selector: 'node.dimmed',      style: { opacity: 0.12 } },
  { selector: 'edge.dimmed',      style: { opacity: 0.04 } },
  { selector: 'node.searched',    style: { 'border-width': 3, 'border-color': '#ffd600', 'border-style': 'solid', opacity: 1 } },
  { selector: 'node:selected',    style: { 'border-width': 3, 'border-color': '#ffffff', opacity: 1 } },
];
```

- [ ] **Step 2: Verify the build passes**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected: `✓ built in` — no errors.

- [ ] **Step 3: Commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/src/graphs/cytoscapeStyles.ts
git commit -m "feat(ad-ui): add semantic cytoscape stylesheet for all 17 AD node types"
```

---

### Task 3: Create cytoscapeLayouts.ts

**Files:**
- Create: `r3ngine-plugins/active_directory/ui/src/graphs/cytoscapeLayouts.ts`
- Modify: `r3ngine-plugins/active_directory/ui/src/types/index.ts`

- [ ] **Step 1: Add LayoutName to types/index.ts**

Add the following to the bottom of `r3ngine-plugins/active_directory/ui/src/types/index.ts`:

```typescript
export type LayoutName = 'dagre' | 'fcose' | 'circle' | 'concentric' | 'grid';
```

- [ ] **Step 2: Create cytoscapeLayouts.ts**

Create `r3ngine-plugins/active_directory/ui/src/graphs/cytoscapeLayouts.ts`:

```typescript
import './cytoscapeExtensions'; // registers dagre + fcose before first layout run
import type { LayoutName } from '../types';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const LAYOUT_CONFIGS: Record<LayoutName, any> = {
  dagre: {
    name: 'dagre',
    rankDir: 'TB',
    nodeSep: 60,
    rankSep: 90,
    padding: 40,
    animate: true,
    animationDuration: 450,
    fit: false,
  },
  fcose: {
    name: 'fcose',
    quality: 'default',
    randomize: false,
    animate: true,
    animationDuration: 450,
    nodeSeparation: 75,
    fit: false,
  },
  circle: {
    name: 'circle',
    padding: 40,
    animate: true,
    animationDuration: 450,
    fit: false,
  },
  concentric: {
    name: 'concentric',
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    concentric: (node: any) => {
      const t = node.data('type') as string;
      if (t === 'ADForest') return 5;
      if (t === 'ADDomain') return 4;
      if (t === 'ADIdentityProvider' || t === 'ADAuthService') return 3;
      if (t === 'ADUser' || t === 'ADGroup' || t === 'ADComputer') return 2;
      return 1;
    },
    levelWidth: () => 2,
    padding: 40,
    animate: true,
    animationDuration: 450,
    fit: false,
  },
  grid: {
    name: 'grid',
    padding: 40,
    animate: true,
    animationDuration: 450,
    fit: false,
  },
};
```

- [ ] **Step 3: Build and verify**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected: `✓ built in` — no errors.

- [ ] **Step 4: Commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/src/graphs/cytoscapeLayouts.ts active_directory/ui/src/types/index.ts
git commit -m "feat(ad-ui): add 5-layout config map and LayoutName type"
```

---

### Task 4: Update adStore.ts with new graph state fields

**Files:**
- Modify: `r3ngine-plugins/active_directory/ui/src/store/adStore.ts`

- [ ] **Step 1: Replace the entire file**

```typescript
import { create } from 'zustand';
import type { WSMessage, LayoutName } from '../types';

interface ADStoreState {
  // Graph
  graphLayout: LayoutName;
  selectedNodeId: string | null;
  selectedNodeData: Record<string, unknown> | null;
  focusMode: boolean;
  searchQuery: string;
  // WS messages (legacy — kept for backward compat; new consumers use realtimeStore)
  wsMessages: WSMessage[];
  // Assessment
  activeAssessmentId: number | null;
  // Actions
  setGraphLayout: (layout: LayoutName) => void;
  setSelectedNode: (id: string | null, data?: Record<string, unknown> | null) => void;
  setFocusMode: (enabled: boolean) => void;
  setSearchQuery: (q: string) => void;
  addWsMessage: (msg: WSMessage) => void;
  clearWsMessages: () => void;
  setActiveAssessment: (id: number | null) => void;
}

export const useADStore = create<ADStoreState>((set) => ({
  graphLayout: 'dagre',
  selectedNodeId: null,
  selectedNodeData: null,
  focusMode: false,
  searchQuery: '',
  wsMessages: [],
  activeAssessmentId: null,
  setGraphLayout: (layout) => set({ graphLayout: layout }),
  setSelectedNode: (id, data) => set({ selectedNodeId: id, selectedNodeData: data ?? null }),
  setFocusMode: (enabled) => set({ focusMode: enabled }),
  setSearchQuery: (q) => set({ searchQuery: q }),
  addWsMessage: (msg) =>
    set((state) => ({ wsMessages: [...state.wsMessages.slice(-99), msg] })),
  clearWsMessages: () => set({ wsMessages: [] }),
  setActiveAssessment: (id) => set({ activeAssessmentId: id }),
}));
```

- [ ] **Step 2: Build and verify**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected: `✓ built in` — no type errors.

- [ ] **Step 3: Commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/src/store/adStore.ts
git commit -m "feat(ad-ui): add focusMode, searchQuery, selectedNodeData to adStore"
```

---

### Task 5: Create graph utility hooks

**Files:**
- Create: `r3ngine-plugins/active_directory/ui/src/graphs/useGraphSearch.ts`
- Create: `r3ngine-plugins/active_directory/ui/src/graphs/useGraphFocus.ts`
- Create: `r3ngine-plugins/active_directory/ui/src/graphs/useGraphViewport.ts`

- [ ] **Step 1: Create useGraphSearch.ts**

```typescript
import { useMemo } from 'react';
import type { CytoscapeGraph } from '../types';

export function useGraphSearch(
  elements: CytoscapeGraph | undefined,
  searchQuery: string,
): Set<string> {
  return useMemo(() => {
    if (!searchQuery.trim() || !elements) return new Set<string>();
    const q = searchQuery.toLowerCase();
    return new Set(
      elements.nodes
        .filter((n) =>
          String(n.data['label'] ?? n.data['id'] ?? '').toLowerCase().includes(q)
        )
        .map((n) => String(n.data['id']))
    );
  }, [searchQuery, elements]);
}
```

- [ ] **Step 2: Create useGraphFocus.ts**

```typescript
import { useMemo } from 'react';
import type { CytoscapeGraph } from '../types';

export function useGraphFocus(
  selectedNodeId: string | null,
  elements: CytoscapeGraph | undefined,
  focusMode: boolean,
): Set<string> | null {
  return useMemo(() => {
    if (!focusMode || !selectedNodeId || !elements) return null;
    const connected = new Set<string>([selectedNodeId]);
    for (const edge of elements.edges) {
      const src = String(edge.data['source'] ?? '');
      const tgt = String(edge.data['target'] ?? '');
      if (src === selectedNodeId) connected.add(tgt);
      if (tgt === selectedNodeId) connected.add(src);
    }
    return connected;
  }, [selectedNodeId, elements, focusMode]);
}
```

- [ ] **Step 3: Create useGraphViewport.ts**

```typescript
import { useRef, useCallback } from 'react';
import type cytoscape from 'cytoscape';

interface Viewport {
  pan: { x: number; y: number };
  zoom: number;
}

export function useGraphViewport() {
  const saved = useRef<Viewport | null>(null);

  const saveViewport = useCallback((cy: cytoscape.Core) => {
    saved.current = { pan: cy.pan(), zoom: cy.zoom() };
  }, []);

  const restoreViewport = useCallback((cy: cytoscape.Core) => {
    if (!saved.current) return;
    cy.viewport({ pan: saved.current.pan, zoom: saved.current.zoom });
  }, []);

  const clearViewport = useCallback(() => {
    saved.current = null;
  }, []);

  return { saveViewport, restoreViewport, clearViewport };
}
```

- [ ] **Step 4: Build and verify**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected: `✓ built in` — no errors.

- [ ] **Step 5: Commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/src/graphs/useGraphSearch.ts active_directory/ui/src/graphs/useGraphFocus.ts active_directory/ui/src/graphs/useGraphViewport.ts
git commit -m "feat(ad-ui): add graph search, focus, and viewport utility hooks"
```

---

### Task 6: Create GraphNodePanel, GraphLegend, GraphToolbar components

**Files:**
- Create: `r3ngine-plugins/active_directory/ui/src/components/GraphNodePanel.tsx`
- Create: `r3ngine-plugins/active_directory/ui/src/components/GraphLegend.tsx`
- Create: `r3ngine-plugins/active_directory/ui/src/components/GraphToolbar.tsx`
- Delete: `r3ngine-plugins/active_directory/ui/src/components/GraphControlBar.tsx`

- [ ] **Step 1: Create GraphNodePanel.tsx**

```tsx
import React from 'react';
import { Box, Typography, Divider, Chip, IconButton } from '@mui/material';
import { X } from 'lucide-react';
import { NODE_COLORS } from '../graphs/cytoscapeStyles';

interface Props {
  nodeData: Record<string, unknown> | null;
  onClose: () => void;
}

const HIDDEN_KEYS = new Set(['id', 'label', 'color', 'origColor', 'parent']);

export function GraphNodePanel({ nodeData, onClose }: Props) {
  if (!nodeData) return null;

  const nodeType = String(nodeData['type'] ?? '');
  const color = NODE_COLORS[nodeType] ?? '#90caf9';
  const displayLabel = String(nodeData['label'] ?? nodeData['id'] ?? '');
  const entries = Object.entries(nodeData).filter(
    ([k, v]) => !HIDDEN_KEYS.has(k) && v !== null && v !== undefined && v !== ''
  );

  return (
    <Box
      sx={{
        width: 280,
        flexShrink: 0,
        height: '100%',
        bgcolor: 'rgba(8,8,18,0.97)',
        borderLeft: `3px solid ${color}`,
        borderTop: '1px solid rgba(255,255,255,0.08)',
        p: 2,
        overflow: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Chip
            label={nodeType.replace(/^AD/, '')}
            size="small"
            sx={{ bgcolor: color, color: '#000', mb: 0.5, fontFamily: 'Orbitron', fontSize: '0.6rem' }}
          />
          <Typography
            variant="subtitle2"
            sx={{ fontFamily: 'monospace', wordBreak: 'break-all', fontSize: '0.8rem' }}
          >
            {displayLabel}
          </Typography>
        </Box>
        <IconButton size="small" onClick={onClose} sx={{ color: 'text.secondary', flexShrink: 0 }}>
          <X size={14} />
        </IconButton>
      </Box>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)' }} />

      {entries.map(([key, value]) => (
        <Box key={key}>
          <Typography
            variant="caption"
            sx={{
              color: 'rgba(255,255,255,0.4)',
              textTransform: 'uppercase',
              fontSize: '0.58rem',
              fontFamily: 'Orbitron',
              letterSpacing: 0.8,
            }}
          >
            {key.replace(/_/g, ' ')}
          </Typography>
          <Typography
            variant="body2"
            sx={{ fontFamily: 'monospace', fontSize: '0.75rem', wordBreak: 'break-all', color: 'rgba(255,255,255,0.85)' }}
          >
            {typeof value === 'boolean' ? (value ? 'true' : 'false') : String(value)}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}
```

- [ ] **Step 2: Create GraphLegend.tsx**

```tsx
import React, { useState } from 'react';
import { Box, Typography, Collapse } from '@mui/material';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { NODE_COLORS, NODE_SHAPES } from '../graphs/cytoscapeStyles';

export function GraphLegend() {
  const [open, setOpen] = useState(false);

  return (
    <Box
      sx={{
        position: 'absolute',
        bottom: 12,
        left: 12,
        zIndex: 10,
        bgcolor: 'rgba(8,8,18,0.92)',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: 1,
        p: 1,
        cursor: 'pointer',
        minWidth: 80,
        userSelect: 'none',
      }}
      onClick={() => setOpen(!open)}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <Typography variant="caption" sx={{ fontFamily: 'Orbitron', fontSize: '0.58rem', color: 'rgba(255,255,255,0.5)', letterSpacing: 1 }}>
          LEGEND
        </Typography>
        {open ? <ChevronDown size={10} color="rgba(255,255,255,0.4)" /> : <ChevronRight size={10} color="rgba(255,255,255,0.4)" />}
      </Box>
      <Collapse in={open}>
        <Box sx={{ mt: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px 14px' }}>
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <Box key={type} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography sx={{ fontSize: '0.75rem', color, lineHeight: 1 }}>
                {NODE_SHAPES[type] ?? '●'}
              </Typography>
              <Typography variant="caption" sx={{ fontSize: '0.58rem', color: 'rgba(255,255,255,0.6)' }}>
                {type.replace(/^AD/, '')}
              </Typography>
            </Box>
          ))}
        </Box>
      </Collapse>
    </Box>
  );
}
```

- [ ] **Step 3: Create GraphToolbar.tsx**

```tsx
import React from 'react';
import {
  Box, ToggleButton, ToggleButtonGroup,
  TextField, IconButton, Tooltip, InputAdornment,
} from '@mui/material';
import { Maximize2, Target, Download, Search, X } from 'lucide-react';
import type { LayoutName } from '../types';

const LAYOUTS: LayoutName[] = ['dagre', 'fcose', 'circle', 'concentric', 'grid'];

interface Props {
  layout: LayoutName;
  onLayoutChange: (l: LayoutName) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  focusMode: boolean;
  onFocusModeToggle: () => void;
  onFitGraph: () => void;
  onExportPng: () => void;
}

export function GraphToolbar({
  layout, onLayoutChange,
  searchQuery, onSearchChange,
  focusMode, onFocusModeToggle,
  onFitGraph, onExportPng,
}: Props) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
      <ToggleButtonGroup
        size="small"
        exclusive
        value={layout}
        onChange={(_e, v) => { if (v) onLayoutChange(v as LayoutName); }}
      >
        {LAYOUTS.map((l) => (
          <ToggleButton
            key={l}
            value={l}
            sx={{ fontSize: '0.6rem', py: 0.5, px: 1, textTransform: 'uppercase', fontFamily: 'Orbitron', letterSpacing: 0.5 }}
          >
            {l}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>

      <TextField
        size="small"
        placeholder="Search nodes…"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        sx={{ width: 180, '& .MuiInputBase-input': { fontSize: '0.8rem' } }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Search size={14} color="rgba(255,255,255,0.4)" />
            </InputAdornment>
          ),
          endAdornment: searchQuery ? (
            <InputAdornment position="end">
              <IconButton size="small" onClick={() => onSearchChange('')} edge="end">
                <X size={12} />
              </IconButton>
            </InputAdornment>
          ) : null,
        }}
      />

      <Box sx={{ display: 'flex', gap: 0.5 }}>
        <Tooltip title="Fit graph to viewport">
          <IconButton size="small" onClick={onFitGraph}>
            <Maximize2 size={16} />
          </IconButton>
        </Tooltip>
        <Tooltip title={focusMode ? 'Disable focus mode' : 'Focus mode: highlight neighbors of selected node'}>
          <IconButton size="small" onClick={onFocusModeToggle} color={focusMode ? 'primary' : 'default'}>
            <Target size={16} />
          </IconButton>
        </Tooltip>
        <Tooltip title="Export graph as PNG">
          <IconButton size="small" onClick={onExportPng}>
            <Download size={16} />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );
}
```

- [ ] **Step 4: Delete the old GraphControlBar.tsx**

Delete `r3ngine-plugins/active_directory/ui/src/components/GraphControlBar.tsx` — it is replaced by `GraphToolbar.tsx`.

- [ ] **Step 5: Build and verify**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected: `✓ built in` — no errors. (ADGraphExplorerPage still imports GraphControlBar which is now gone — that import will break the build. Proceed to Task 7 immediately to fix the page.)

- [ ] **Step 6: Commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/src/components/GraphNodePanel.tsx active_directory/ui/src/components/GraphLegend.tsx active_directory/ui/src/components/GraphToolbar.tsx
git rm active_directory/ui/src/components/GraphControlBar.tsx
git commit -m "feat(ad-ui): add GraphNodePanel, GraphLegend, GraphToolbar; remove GraphControlBar"
```

---

### Task 7: Rewrite ADGraphExplorerPage.tsx

**Files:**
- Modify: `r3ngine-plugins/active_directory/ui/src/pages/ADGraphExplorerPage.tsx`

- [ ] **Step 1: Replace the entire file**

```tsx
import React, { useCallback, useEffect, useRef } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import type cytoscape from 'cytoscape';
import { Box, Typography, Alert, CircularProgress } from '@mui/material';
import { useDomainGraph } from '../api/adApi';
import { useADStore } from '../store/adStore';
import { CYTOSCAPE_STYLESHEET } from '../graphs/cytoscapeStyles';
import { LAYOUT_CONFIGS } from '../graphs/cytoscapeLayouts';
import { useGraphSearch } from '../graphs/useGraphSearch';
import { useGraphFocus } from '../graphs/useGraphFocus';
import { useGraphViewport } from '../graphs/useGraphViewport';
import { GraphToolbar } from '../components/GraphToolbar';
import { GraphNodePanel } from '../components/GraphNodePanel';
import { GraphLegend } from '../components/GraphLegend';

interface Props {
  assessmentId: number;
}

export function ADGraphExplorerPage({ assessmentId }: Props) {
  const { data, isLoading, error, dataUpdatedAt } = useDomainGraph(assessmentId);
  const {
    graphLayout, setGraphLayout,
    selectedNodeId, selectedNodeData, setSelectedNode,
    focusMode, setFocusMode,
    searchQuery, setSearchQuery,
  } = useADStore();

  const cyRef = useRef<cytoscape.Core | null>(null);
  const { saveViewport, restoreViewport, clearViewport } = useGraphViewport();
  const matchingNodeIds = useGraphSearch(data, searchQuery);
  const connectedNodeIds = useGraphFocus(selectedNodeId, data, focusMode);

  // ── Apply search highlight classes when matchingNodeIds changes ─────────
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().removeClass('searched');
    if (matchingNodeIds.size > 0) {
      matchingNodeIds.forEach((id) => cy.getElementById(id).addClass('searched'));
      const first = cy.getElementById([...matchingNodeIds][0]);
      if (first.length > 0) {
        cy.animate({ center: { eles: first }, duration: 300 } as Parameters<typeof cy.animate>[0]);
      }
    }
  }, [matchingNodeIds]);

  // ── Apply focus / dim classes when selection or focusMode changes ────────
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().removeClass('highlighted dimmed');
    cy.edges().removeClass('dimmed');
    if (!focusMode || !connectedNodeIds) return;
    cy.nodes().addClass('dimmed');
    cy.edges().addClass('dimmed');
    connectedNodeIds.forEach((id) => {
      cy.getElementById(id).addClass('highlighted').removeClass('dimmed');
    });
    // Re-highlight edges connecting the highlighted nodes
    cy.edges().filter((e) => {
      const src = e.source().id();
      const tgt = e.target().id();
      return (connectedNodeIds.has(src) && connectedNodeIds.has(tgt));
    }).removeClass('dimmed');
  }, [connectedNodeIds, focusMode]);

  // ── Restore viewport after data refresh (graph_updated WS event) ─────────
  useEffect(() => {
    // dataUpdatedAt changes when the query re-fetches
    const cy = cyRef.current;
    if (!cy || !dataUpdatedAt) return;
    // Wait for layout to settle then restore
    const tid = setTimeout(() => restoreViewport(cy), 600);
    return () => clearTimeout(tid);
  }, [dataUpdatedAt, restoreViewport]);

  // ── cy instance callback ─────────────────────────────────────────────────
  const handleCyReady = useCallback((cy: cytoscape.Core) => {
    cyRef.current = cy;

    // Save viewport on user interaction
    cy.on('viewport', () => saveViewport(cy));

    // Node tap → select
    cy.on('tap', 'node', (event) => {
      const nodeData = event.target.data() as Record<string, unknown>;
      setSelectedNode(String(nodeData['id'] ?? ''), nodeData);
    });
    // Background tap → deselect
    cy.on('tap', (event) => {
      if (event.target === cy) setSelectedNode(null, null);
    });
  }, [saveViewport, setSelectedNode]);

  // ── Toolbar actions ──────────────────────────────────────────────────────
  const handleFitGraph = useCallback(() => {
    clearViewport();
    cyRef.current?.fit(undefined, 40);
  }, [clearViewport]);

  const handleExportPng = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const png = cy.png({ full: true, scale: 2, bg: '#0a0a14' });
    const a = document.createElement('a');
    a.href = png;
    a.download = `ad-graph-${assessmentId}-${Date.now()}.png`;
    a.click();
  }, [assessmentId]);

  // ── Render guards ────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', pt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }
  if (error) return <Alert severity="error">Failed to load graph data</Alert>;

  const elements = [...(data?.nodes ?? []), ...(data?.edges ?? [])];
  if (elements.length === 0) {
    return (
      <Box>
        <Typography variant="h6" sx={{ fontFamily: 'Orbitron', mb: 2 }}>DOMAIN GRAPH</Typography>
        <Alert severity="info">
          No graph data yet. Run an assessment or ingest BloodHound / LDAP data to populate the graph.
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Typography variant="h6" sx={{ fontFamily: 'Orbitron', mb: 1, letterSpacing: 2 }}>
        DOMAIN GRAPH
      </Typography>

      <GraphToolbar
        layout={graphLayout}
        onLayoutChange={(l) => { saveViewport(cyRef.current!); setGraphLayout(l); }}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        focusMode={focusMode}
        onFocusModeToggle={() => setFocusMode(!focusMode)}
        onFitGraph={handleFitGraph}
        onExportPng={handleExportPng}
      />

      <Box sx={{ display: 'flex', flex: 1, minHeight: 0, gap: 0 }}>
        {/* Main canvas */}
        <Box
          sx={{
            flex: 1,
            position: 'relative',
            bgcolor: 'rgba(0,0,0,0.35)',
            borderRadius: selectedNodeData ? '4px 0 0 4px' : 1,
            border: '1px solid rgba(255,255,255,0.08)',
            minHeight: 560,
          }}
        >
          <CytoscapeComponent
            elements={elements}
            style={{ width: '100%', height: '100%' }}
            stylesheet={CYTOSCAPE_STYLESHEET}
            layout={LAYOUT_CONFIGS[graphLayout]}
            cy={handleCyReady}
            wheelSensitivity={0.2}
          />
          <GraphLegend />
        </Box>

        {/* Node detail panel */}
        {selectedNodeData && (
          <GraphNodePanel
            nodeData={selectedNodeData}
            onClose={() => setSelectedNode(null, null)}
          />
        )}
      </Box>
    </Box>
  );
}
```

- [ ] **Step 2: Build and verify**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected: `✓ built in` — no TypeScript errors.

- [ ] **Step 3: Rebuild and verify bundle size is reasonable**

Output should be similar to before: roughly 740–800 kB uncompressed. The two new layout extensions add ~150 kB combined.

- [ ] **Step 4: Commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/src/pages/ADGraphExplorerPage.tsx
git commit -m "feat(ad-ui): rewrite ADGraphExplorerPage with enterprise graph UX"
```

---

## Phase 8: Realtime Streaming

---

### Task 8: Expand WSMessage types with all Phase 8 event types

**Files:**
- Modify: `r3ngine-plugins/active_directory/ui/src/types/index.ts`

- [ ] **Step 1: Replace WSMessage and add payload interfaces**

Replace the existing `WSMessage` interface and its type union in `src/types/index.ts` with the following (add after the existing exports — keep everything else):

```typescript
// ── WebSocket event types ──────────────────────────────────────────────────

export type WSEventType =
  | 'assessment_started'
  | 'phase_started'
  | 'phase_completed'
  | 'activity_complete'
  | 'workflow_progress'
  | 'finding_detected'
  | 'trust_discovered'
  | 'identity_discovered'
  | 'graph_updated'
  | 'correlation_completed'
  | 'error';

export interface WorkflowProgressPayload {
  phase: string;
  progress_pct: number;
  message: string;
}

export interface FindingDetectedPayload {
  finding_id: string;
  title: string;
  severity: string;
  affected_object: string;
  finding_type: string;
}

export interface TrustDiscoveredPayload {
  source_domain: string;
  target_domain: string;
  trust_type: string;
  is_transitive: boolean;
}

export interface IdentityDiscoveredPayload {
  entity_type: string;
  name: string;
  count?: number;
}

export interface GraphUpdatedPayload {
  assessment_id: number;
  node_count: number;
  edge_count: number;
}

export interface CorrelationCompletedPayload {
  exposure_count: number;
  high_risk_count: number;
}

export interface WSMessage {
  type: WSEventType;
  payload: Record<string, unknown>;
}
```

The full `src/types/index.ts` after the edit (keep the previous interfaces, replace only `WSMessage` and its `type` field):

Final file content:

```typescript
export interface ADAssessment {
  id: number;
  name: string;
  target_domain: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'CANCELLED';
  created_at: string;
  completed_at: string | null;
  workflow_id: string | null;
  config: Record<string, unknown>;
  findings_count?: number;
}

export interface ADFinding {
  id: number;
  title: string;
  description: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  finding_type: string;
  affected_object: string;
  remediation: string;
  evidence: Record<string, unknown>;
  created_at: string;
}

export interface ADTrust {
  id: number;
  source_domain: string;
  target_domain: string;
  trust_type: string;
  trust_direction: string;
  is_transitive: boolean;
  sid_filtering_enabled: boolean;
}

export interface ADExposure {
  id: number;
  hostname: string;
  ip_address: string | null;
  exposure_type: string;
  risk_score: number;
  is_internet_facing: boolean;
  port: number | null;
  service_banner: string;
  correlated_domain: string | null;
  created_at: string;
}

export interface CytoscapeGraph {
  nodes: Array<{ data: Record<string, unknown> }>;
  edges: Array<{ data: Record<string, unknown> }>;
}

export type LayoutName = 'dagre' | 'fcose' | 'circle' | 'concentric' | 'grid';

export type WSEventType =
  | 'assessment_started'
  | 'phase_started'
  | 'phase_completed'
  | 'activity_complete'
  | 'workflow_progress'
  | 'finding_detected'
  | 'trust_discovered'
  | 'identity_discovered'
  | 'graph_updated'
  | 'correlation_completed'
  | 'error';

export interface WSMessage {
  type: WSEventType;
  payload: Record<string, unknown>;
}
```

- [ ] **Step 2: Build and verify**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected: `✓ built in` — no errors.

- [ ] **Step 3: Commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/src/types/index.ts
git commit -m "feat(ad-ui): expand WSMessage event types for Phase 8 realtime streaming"
```

---

### Task 9: Create realtimeStore.ts

**Files:**
- Create: `r3ngine-plugins/active_directory/ui/src/store/realtimeStore.ts`

- [ ] **Step 1: Create the file**

```typescript
import { create } from 'zustand';
import type { WSMessage, WSEventType } from '../types';

export interface RealtimeEvent {
  id: string;
  type: WSEventType;
  message: string;
  timestamp: number;
}

interface RealtimeStoreState {
  isConnected: boolean;
  currentPhase: string | null;
  progressPct: number;
  recentEvents: RealtimeEvent[];
  pendingGraphRefresh: boolean;
  liveFindings: Array<{
    id: string;
    title: string;
    severity: string;
    affected_object: string;
  }>;
  setConnected: (connected: boolean) => void;
  handleWsMessage: (msg: WSMessage) => void;
  clearPendingGraphRefresh: () => void;
  reset: () => void;
}

const MAX_EVENTS = 20;
const MAX_LIVE_FINDINGS = 50;

export const useRealtimeStore = create<RealtimeStoreState>((set) => ({
  isConnected: false,
  currentPhase: null,
  progressPct: 0,
  recentEvents: [],
  pendingGraphRefresh: false,
  liveFindings: [],

  setConnected: (connected) => set({ isConnected: connected }),

  handleWsMessage: (msg) =>
    set((state) => {
      const event: RealtimeEvent = {
        id: `${Date.now()}_${Math.random().toString(36).slice(2)}`,
        type: msg.type,
        message: String(msg.payload['message'] ?? msg.type),
        timestamp: Date.now(),
      };
      const recentEvents = [event, ...state.recentEvents].slice(0, MAX_EVENTS);

      switch (msg.type) {
        case 'workflow_progress':
          return {
            recentEvents,
            currentPhase: String(msg.payload['phase'] ?? state.currentPhase),
            progressPct: Number(msg.payload['progress_pct'] ?? state.progressPct),
          };

        case 'phase_started':
          return {
            recentEvents,
            currentPhase: String(msg.payload['phase'] ?? state.currentPhase),
          };

        case 'finding_detected':
          return {
            recentEvents,
            liveFindings: [
              {
                id: String(msg.payload['finding_id'] ?? Date.now()),
                title: String(msg.payload['title'] ?? ''),
                severity: String(msg.payload['severity'] ?? 'INFO'),
                affected_object: String(msg.payload['affected_object'] ?? ''),
              },
              ...state.liveFindings,
            ].slice(0, MAX_LIVE_FINDINGS),
          };

        case 'graph_updated':
          return { recentEvents, pendingGraphRefresh: true };

        default:
          return { recentEvents };
      }
    }),

  clearPendingGraphRefresh: () => set({ pendingGraphRefresh: false }),

  reset: () =>
    set({
      isConnected: false,
      currentPhase: null,
      progressPct: 0,
      recentEvents: [],
      pendingGraphRefresh: false,
      liveFindings: [],
    }),
}));
```

- [ ] **Step 2: Build and verify**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected: `✓ built in` — no errors.

- [ ] **Step 3: Commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/src/store/realtimeStore.ts
git commit -m "feat(ad-ui): add realtimeStore for batched WS event processing"
```

---

### Task 10: Create useWsEventBus.ts (batched WS hook)

**Files:**
- Create: `r3ngine-plugins/active_directory/ui/src/hooks/useWsEventBus.ts`
- Delete: `r3ngine-plugins/active_directory/ui/src/hooks/useADWebSocket.ts`

- [ ] **Step 1: Create useWsEventBus.ts**

```typescript
import { useEffect, useRef, useCallback } from 'react';
import type { WSMessage } from '../types';
import { useRealtimeStore } from '../store/realtimeStore';

const FLUSH_MS = 150;

export function useWsEventBus(assessmentId: number | null) {
  const buffer = useRef<WSMessage[]>([]);
  const flushTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const handleWsMessage = useRealtimeStore((s) => s.handleWsMessage);
  const setConnected = useRealtimeStore((s) => s.setConnected);

  const flush = useCallback(() => {
    flushTimer.current = null;
    const msgs = buffer.current.splice(0);
    for (const msg of msgs) handleWsMessage(msg);
  }, [handleWsMessage]);

  const scheduleFlush = useCallback(() => {
    if (!flushTimer.current) {
      flushTimer.current = setTimeout(flush, FLUSH_MS);
    }
  }, [flush]);

  useEffect(() => {
    if (!assessmentId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws/plugins/active_directory/${assessmentId}/`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string) as WSMessage;
        buffer.current.push(msg);
        scheduleFlush();
      } catch {
        // ignore malformed frames
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
      if (flushTimer.current) {
        clearTimeout(flushTimer.current);
        flushTimer.current = null;
      }
      buffer.current = [];
      setConnected(false);
    };
  }, [assessmentId, scheduleFlush, setConnected]);

  return wsRef;
}
```

- [ ] **Step 2: Delete the old useADWebSocket.ts**

Delete `r3ngine-plugins/active_directory/ui/src/hooks/useADWebSocket.ts`.

- [ ] **Step 3: Build and verify**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected: `✓ built in`. If `ADAssessmentDetailPage.tsx` still imports `useADWebSocket`, it will fail — fix that in Task 11.

- [ ] **Step 4: Commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/src/hooks/useWsEventBus.ts
git rm active_directory/ui/src/hooks/useADWebSocket.ts
git commit -m "feat(ad-ui): replace useADWebSocket with batched useWsEventBus routing to realtimeStore"
```

---

### Task 11: Create WorkflowProgressPanel and update ADAssessmentDetailPage

**Files:**
- Create: `r3ngine-plugins/active_directory/ui/src/components/WorkflowProgressPanel.tsx`
- Modify: `r3ngine-plugins/active_directory/ui/src/pages/ADAssessmentDetailPage.tsx`

- [ ] **Step 1: Create WorkflowProgressPanel.tsx**

```tsx
import React from 'react';
import { Box, Typography, LinearProgress, Collapse, Chip } from '@mui/material';
import { useRealtimeStore } from '../store/realtimeStore';

const PHASE_LABELS: Record<string, string> = {
  initialization: 'INITIALIZING',
  dns_discovery: 'DNS DISCOVERY',
  cert_discovery: 'CERT DISCOVERY',
  trust_analysis: 'TRUST ANALYSIS',
  exposure_correlation: 'EXPOSURE CORRELATION',
  graph_sync: 'GRAPH SYNC',
  completion: 'COMPLETE',
};

interface Props {
  isRunning: boolean;
}

export function WorkflowProgressPanel({ isRunning }: Props) {
  const { currentPhase, progressPct, recentEvents, isConnected } = useRealtimeStore();

  return (
    <Collapse in={isRunning}>
      <Box
        sx={{
          bgcolor: 'rgba(0,0,0,0.65)',
          border: '1px solid rgba(0,243,255,0.18)',
          borderRadius: 1,
          p: 1.5,
          mb: 2,
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                bgcolor: isConnected ? '#00f3ff' : '#ff1744',
                transition: 'background-color 0.3s',
              }}
            />
            <Typography
              variant="caption"
              sx={{ fontFamily: 'Orbitron', fontSize: '0.62rem', color: '#00f3ff', letterSpacing: 2 }}
            >
              {PHASE_LABELS[currentPhase ?? ''] ?? (currentPhase?.toUpperCase() ?? 'RUNNING')}
            </Typography>
          </Box>
          <Typography
            variant="caption"
            sx={{ fontFamily: 'monospace', color: 'rgba(0,243,255,0.7)', fontSize: '0.75rem' }}
          >
            {progressPct}%
          </Typography>
        </Box>

        <LinearProgress
          variant="determinate"
          value={progressPct}
          sx={{
            height: 3,
            borderRadius: 1,
            bgcolor: 'rgba(255,255,255,0.08)',
            mb: 1,
            '& .MuiLinearProgress-bar': {
              bgcolor: '#00f3ff',
              transition: 'transform 0.6s ease',
            },
          }}
        />

        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          {recentEvents.slice(0, 5).map((e) => (
            <Chip
              key={e.id}
              label={e.message.length > 45 ? `${e.message.slice(0, 45)}…` : e.message}
              size="small"
              sx={{
                fontSize: '0.58rem',
                height: 18,
                fontFamily: 'monospace',
                bgcolor: 'rgba(255,255,255,0.06)',
                color: 'rgba(255,255,255,0.6)',
              }}
            />
          ))}
        </Box>
      </Box>
    </Collapse>
  );
}
```

- [ ] **Step 2: Update ADAssessmentDetailPage.tsx**

Replace the `useADWebSocket` import and usage, and add `WorkflowProgressPanel`. The key changes are:
- Remove `import { useADWebSocket } from '../hooks/useADWebSocket'`
- Add `import { useWsEventBus } from '../hooks/useWsEventBus'`
- Add `import { WorkflowProgressPanel } from '../components/WorkflowProgressPanel'`
- Replace `useADWebSocket(...)` call with `useWsEventBus(...)`
- Add `<WorkflowProgressPanel isRunning={assessment.status === 'RUNNING'} />` before the Tabs

Full replacement for `ADAssessmentDetailPage.tsx`:

```tsx
import React, { useState } from 'react';
import {
  Box, Typography, Button, Tabs, Tab, Table, TableHead,
  TableBody, TableRow, TableCell, Chip, CircularProgress,
} from '@mui/material';
import { Upload, XCircle } from 'lucide-react';
import { useAssessment, useFindings, useCancelAssessment } from '../api/adApi';
import { AssessmentStatusBadge } from '../components/AssessmentStatusBadge';
import { IngestDataDialog } from '../components/IngestDataDialog';
import { WorkflowProgressPanel } from '../components/WorkflowProgressPanel';
import { useWsEventBus } from '../hooks/useWsEventBus';

interface Props {
  assessmentId: number;
  onNavigate?: (path: string) => void;
}

const SEVERITY_COLOR: Record<string, 'error' | 'warning' | 'info' | 'default' | 'success'> = {
  CRITICAL: 'error', HIGH: 'error', MEDIUM: 'warning', LOW: 'info', INFO: 'default',
};

export function ADAssessmentDetailPage({ assessmentId, onNavigate }: Props) {
  const [tab, setTab] = useState(0);
  const [ingestOpen, setIngestOpen] = useState(false);
  const { data: assessment, isLoading } = useAssessment(assessmentId);
  const { data: findings } = useFindings(assessmentId);
  const { mutate: cancel } = useCancelAssessment();

  // Connect WebSocket when assessment is running; batched events → realtimeStore
  useWsEventBus(assessment?.status === 'RUNNING' ? assessmentId : null);

  if (isLoading || !assessment) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', pt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
        <Box>
          <Typography variant="h6" sx={{ fontFamily: 'Orbitron' }}>{assessment.name}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
            {assessment.target_domain}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <AssessmentStatusBadge status={assessment.status} />
          <Button size="small" startIcon={<Upload size={14} />} onClick={() => setIngestOpen(true)}>
            Ingest Data
          </Button>
          {assessment.status === 'RUNNING' && (
            <Button size="small" color="error" startIcon={<XCircle size={14} />} onClick={() => cancel(assessmentId)}>
              Cancel
            </Button>
          )}
          <Button size="small" variant="outlined" onClick={() => onNavigate?.('graph')}>
            Graph Explorer
          </Button>
        </Box>
      </Box>

      <WorkflowProgressPanel isRunning={assessment.status === 'RUNNING'} />

      <Tabs value={tab} onChange={(_e, v) => setTab(v as number)} sx={{ mb: 2 }}>
        <Tab label="Findings" />
        <Tab label="Trusts" />
        <Tab label="Exposures" />
      </Tabs>

      {tab === 0 && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.68rem' }}>SEVERITY</TableCell>
              <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.68rem' }}>TITLE</TableCell>
              <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.68rem' }}>AFFECTED OBJECT</TableCell>
              <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.68rem' }}>TYPE</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(findings ?? []).map((f) => (
              <TableRow key={f.id} hover>
                <TableCell>
                  <Chip label={f.severity} color={SEVERITY_COLOR[f.severity] ?? 'default'} size="small" />
                </TableCell>
                <TableCell>{f.title}</TableCell>
                <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{f.affected_object}</TableCell>
                <TableCell sx={{ fontSize: '0.8rem' }}>{f.finding_type}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <IngestDataDialog
        open={ingestOpen}
        assessmentId={assessmentId}
        onClose={() => setIngestOpen(false)}
      />
    </Box>
  );
}
```

- [ ] **Step 3: Build and verify**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected: `✓ built in` — no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/src/components/WorkflowProgressPanel.tsx active_directory/ui/src/pages/ADAssessmentDetailPage.tsx
git commit -m "feat(ad-ui): add WorkflowProgressPanel; wire ADAssessmentDetailPage to useWsEventBus"
```

---

### Task 12: Wire graph_updated events into live graph refresh

**Files:**
- Modify: `r3ngine-plugins/active_directory/ui/src/pages/ADGraphExplorerPage.tsx`
- Modify: `r3ngine-plugins/active_directory/ui/src/api/adApi.ts`

The `realtimeStore.pendingGraphRefresh` flag is set to `true` whenever a `graph_updated` event arrives. `ADGraphExplorerPage` must watch this flag and refetch the graph query when it fires.

- [ ] **Step 1: Add a refetch trigger to useDomainGraph**

The existing `useDomainGraph` hook already uses TanStack Query. To trigger a refetch, we call `refetch()` from the returned query object. No changes needed to `adApi.ts` — the hook is fine as-is.

- [ ] **Step 2: Add the refresh effect to ADGraphExplorerPage.tsx**

In `ADGraphExplorerPage.tsx`, change the query destructure and add the refresh effect:

```tsx
// Change this line (near top of ADGraphExplorerPage component):
const { data, isLoading, error, dataUpdatedAt } = useDomainGraph(assessmentId);
// to:
const { data, isLoading, error, dataUpdatedAt, refetch } = useDomainGraph(assessmentId);
```

Then add these imports and effect after the existing imports:

```tsx
import { useRealtimeStore } from '../store/realtimeStore';
```

And add this effect inside the component body (after the existing `useEffect` hooks):

```tsx
// Trigger graph refetch when a graph_updated WS event is received
const pendingGraphRefresh = useRealtimeStore((s) => s.pendingGraphRefresh);
const clearPendingGraphRefresh = useRealtimeStore((s) => s.clearPendingGraphRefresh);

useEffect(() => {
  if (!pendingGraphRefresh) return;
  clearPendingGraphRefresh();
  void refetch();
}, [pendingGraphRefresh, clearPendingGraphRefresh, refetch]);
```

Full updated `ADGraphExplorerPage.tsx` (complete replacement, incorporating the new lines):

```tsx
import React, { useCallback, useEffect, useRef } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import type cytoscape from 'cytoscape';
import { Box, Typography, Alert, CircularProgress } from '@mui/material';
import { useDomainGraph } from '../api/adApi';
import { useADStore } from '../store/adStore';
import { useRealtimeStore } from '../store/realtimeStore';
import { CYTOSCAPE_STYLESHEET } from '../graphs/cytoscapeStyles';
import { LAYOUT_CONFIGS } from '../graphs/cytoscapeLayouts';
import { useGraphSearch } from '../graphs/useGraphSearch';
import { useGraphFocus } from '../graphs/useGraphFocus';
import { useGraphViewport } from '../graphs/useGraphViewport';
import { GraphToolbar } from '../components/GraphToolbar';
import { GraphNodePanel } from '../components/GraphNodePanel';
import { GraphLegend } from '../components/GraphLegend';

interface Props {
  assessmentId: number;
}

export function ADGraphExplorerPage({ assessmentId }: Props) {
  const { data, isLoading, error, dataUpdatedAt, refetch } = useDomainGraph(assessmentId);
  const {
    graphLayout, setGraphLayout,
    selectedNodeId, selectedNodeData, setSelectedNode,
    focusMode, setFocusMode,
    searchQuery, setSearchQuery,
  } = useADStore();

  const cyRef = useRef<cytoscape.Core | null>(null);
  const { saveViewport, restoreViewport, clearViewport } = useGraphViewport();
  const matchingNodeIds = useGraphSearch(data, searchQuery);
  const connectedNodeIds = useGraphFocus(selectedNodeId, data, focusMode);

  // Live graph refresh from WS graph_updated event
  const pendingGraphRefresh = useRealtimeStore((s) => s.pendingGraphRefresh);
  const clearPendingGraphRefresh = useRealtimeStore((s) => s.clearPendingGraphRefresh);
  useEffect(() => {
    if (!pendingGraphRefresh) return;
    clearPendingGraphRefresh();
    void refetch();
  }, [pendingGraphRefresh, clearPendingGraphRefresh, refetch]);

  // Apply search highlight classes
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().removeClass('searched');
    if (matchingNodeIds.size > 0) {
      matchingNodeIds.forEach((id) => cy.getElementById(id).addClass('searched'));
      const first = cy.getElementById([...matchingNodeIds][0]);
      if (first.length > 0) {
        cy.animate({ center: { eles: first }, duration: 300 } as Parameters<typeof cy.animate>[0]);
      }
    }
  }, [matchingNodeIds]);

  // Apply focus / dim classes
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().removeClass('highlighted dimmed');
    cy.edges().removeClass('dimmed');
    if (!focusMode || !connectedNodeIds) return;
    cy.nodes().addClass('dimmed');
    cy.edges().addClass('dimmed');
    connectedNodeIds.forEach((id) => {
      cy.getElementById(id).addClass('highlighted').removeClass('dimmed');
    });
    cy.edges().filter((e) => {
      const src = e.source().id();
      const tgt = e.target().id();
      return connectedNodeIds.has(src) && connectedNodeIds.has(tgt);
    }).removeClass('dimmed');
  }, [connectedNodeIds, focusMode]);

  // Restore viewport after data refresh
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !dataUpdatedAt) return;
    const tid = setTimeout(() => restoreViewport(cy), 600);
    return () => clearTimeout(tid);
  }, [dataUpdatedAt, restoreViewport]);

  const handleCyReady = useCallback((cy: cytoscape.Core) => {
    cyRef.current = cy;
    cy.on('viewport', () => saveViewport(cy));
    cy.on('tap', 'node', (event) => {
      const nodeData = event.target.data() as Record<string, unknown>;
      setSelectedNode(String(nodeData['id'] ?? ''), nodeData);
    });
    cy.on('tap', (event) => {
      if (event.target === cy) setSelectedNode(null, null);
    });
  }, [saveViewport, setSelectedNode]);

  const handleFitGraph = useCallback(() => {
    clearViewport();
    cyRef.current?.fit(undefined, 40);
  }, [clearViewport]);

  const handleExportPng = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const png = cy.png({ full: true, scale: 2, bg: '#0a0a14' });
    const a = document.createElement('a');
    a.href = png;
    a.download = `ad-graph-${assessmentId}-${Date.now()}.png`;
    a.click();
  }, [assessmentId]);

  if (isLoading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', pt: 8 }}><CircularProgress /></Box>;
  }
  if (error) return <Alert severity="error">Failed to load graph data</Alert>;

  const elements = [...(data?.nodes ?? []), ...(data?.edges ?? [])];
  if (elements.length === 0) {
    return (
      <Box>
        <Typography variant="h6" sx={{ fontFamily: 'Orbitron', mb: 2 }}>DOMAIN GRAPH</Typography>
        <Alert severity="info">
          No graph data yet. Run an assessment or ingest BloodHound / LDAP data to populate the graph.
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Typography variant="h6" sx={{ fontFamily: 'Orbitron', mb: 1, letterSpacing: 2 }}>
        DOMAIN GRAPH
      </Typography>
      <GraphToolbar
        layout={graphLayout}
        onLayoutChange={(l) => { saveViewport(cyRef.current!); setGraphLayout(l); }}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        focusMode={focusMode}
        onFocusModeToggle={() => setFocusMode(!focusMode)}
        onFitGraph={handleFitGraph}
        onExportPng={handleExportPng}
      />
      <Box sx={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <Box
          sx={{
            flex: 1,
            position: 'relative',
            bgcolor: 'rgba(0,0,0,0.35)',
            borderRadius: selectedNodeData ? '4px 0 0 4px' : 1,
            border: '1px solid rgba(255,255,255,0.08)',
            minHeight: 560,
          }}
        >
          <CytoscapeComponent
            elements={elements}
            style={{ width: '100%', height: '100%' }}
            stylesheet={CYTOSCAPE_STYLESHEET}
            layout={LAYOUT_CONFIGS[graphLayout]}
            cy={handleCyReady}
            wheelSensitivity={0.2}
          />
          <GraphLegend />
        </Box>
        {selectedNodeData && (
          <GraphNodePanel
            nodeData={selectedNodeData}
            onClose={() => setSelectedNode(null, null)}
          />
        )}
      </Box>
    </Box>
  );
}
```

- [ ] **Step 3: Build and verify**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected: `✓ built in` — no errors.

- [ ] **Step 4: Commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/src/pages/ADGraphExplorerPage.tsx
git commit -m "feat(ad-ui): wire graph_updated WS events to live graph refetch via pendingGraphRefresh"
```

---

### Task 13: Update backend temporal_exports.py to emit Phase 8 events

**Files:**
- Modify: `r3ngine-plugins/active_directory/backend/temporal_exports.py`

The backend currently emits only `phase_started` and `phase_completed`. We need six new event emissions spread across the existing activities.

- [ ] **Step 1: Add workflow_progress to each activity start**

After each `phase_started` call in every activity, add a `workflow_progress` emission with the cumulative progress percentage. The phase-to-percentage mapping:

```
initialization         →  5%
dns_discovery start    → 10%   / complete → 25%
cert_discovery start   → 26%   / complete → 40%
trust_analysis start   → 41%   / complete → 60%
exposure_correlation start → 61% / complete → 80%
graph_sync start       → 81%   / complete → 95%
completion             → 100%
```

- [ ] **Step 2: Add identity_discovered in run_dns_discovery_activity**

In `run_dns_discovery_activity`, after appending to `discovered`, add:

```python
_send_ws_update(assessment_id, 'identity_discovered', {
    'entity_type': 'domain_controller',
    'name': dc['hostname'],
    'message': f"Discovered DC: {dc['hostname']} ({dc['role']})",
})
```

Also add after `_send_ws_update(assessment_id, 'phase_completed', {...})`:

```python
_send_ws_update(assessment_id, 'graph_updated', {
    'assessment_id': assessment_id,
    'node_count': len(discovered),
    'edge_count': 0,
    'message': 'Domain graph updated with discovered controllers',
})
```

- [ ] **Step 3: Add trust_discovered and finding_detected in run_trust_analysis_activity**

In `run_trust_analysis_activity`, add inside the trust processing loop:

```python
_send_ws_update(assessment_id, 'trust_discovered', {
    'source_domain': trust.source_domain,
    'target_domain': trust.target_domain,
    'trust_type': trust.trust_type,
    'is_transitive': trust.is_transitive,
    'message': f"Trust discovered: {trust.source_domain} → {trust.target_domain}",
})
if not trust.sid_filtering_enabled:
    _send_ws_update(assessment_id, 'finding_detected', {
        'finding_id': f'trust_no_sid_filter_{trust.id}',
        'title': 'Trust without SID Filtering',
        'severity': 'HIGH',
        'affected_object': f'{trust.source_domain} → {trust.target_domain}',
        'finding_type': 'TRUST_MISCONFIGURATION',
        'message': f'SID filtering disabled on trust to {trust.target_domain}',
    })
```

- [ ] **Step 4: Add correlation_completed and finding_detected in run_exposure_correlation_activity**

After the correlation loop completes, add:

```python
high_risk = [e for e in exposures if e.risk_score >= 70]
for exp in high_risk:
    _send_ws_update(assessment_id, 'finding_detected', {
        'finding_id': f'exposure_high_risk_{exp.id}',
        'title': f'High-Risk Exposure: {exp.exposure_type}',
        'severity': 'HIGH' if exp.risk_score >= 85 else 'MEDIUM',
        'affected_object': exp.hostname,
        'finding_type': 'EXPOSURE',
        'message': f'High-risk exposure detected: {exp.hostname} (score {exp.risk_score})',
    })
_send_ws_update(assessment_id, 'correlation_completed', {
    'exposure_count': len(exposures),
    'high_risk_count': len(high_risk),
    'message': f'Correlation complete: {len(exposures)} exposures, {len(high_risk)} high-risk',
})
_send_ws_update(assessment_id, 'graph_updated', {
    'assessment_id': assessment_id,
    'node_count': len(exposures),
    'edge_count': len(high_risk),
    'message': 'Exposure graph updated',
})
```

The complete updated `temporal_exports.py` (showing only the changed sections — use these exact modifications against the existing file):

For `run_dns_discovery_activity`, add these calls immediately after the `phase_started` call:

```python
_send_ws_update(assessment_id, 'workflow_progress', {
    'phase': 'dns_discovery',
    'progress_pct': 10,
    'message': f'Starting DNS discovery for {target_domain}',
})
```

And after the discovery loop, before `phase_completed`:

```python
for dc in discovered:
    _send_ws_update(assessment_id, 'identity_discovered', {
        'entity_type': 'domain_controller',
        'name': dc['hostname'],
        'message': f"Discovered DC: {dc['hostname']} ({dc['role']})",
    })
_send_ws_update(assessment_id, 'workflow_progress', {
    'phase': 'dns_discovery',
    'progress_pct': 25,
    'message': f'DNS discovery complete: {len(discovered)} controllers found',
})
_send_ws_update(assessment_id, 'graph_updated', {
    'assessment_id': assessment_id,
    'node_count': len(discovered),
    'edge_count': 0,
    'message': 'Domain graph updated',
})
```

- [ ] **Step 5: Sync to container and verify no import errors**

```bash
docker cp d:/Repos/r3ngine/r3ngine-plugins/active_directory r3ngine-web-1:/usr/src/app/plugins_data/
docker exec r3ngine-web-1 python -c "from plugins_data.active_directory.backend.temporal_exports import initialize_assessment_activity; print('OK')"
```

Expected: `OK` with no import errors.

- [ ] **Step 6: Commit**

```bash
cd r3ngine-plugins
git add active_directory/backend/temporal_exports.py
git commit -m "feat(ad-backend): emit workflow_progress, finding_detected, trust_discovered, identity_discovered, graph_updated, correlation_completed events"
```

---

### Task 14: Final build, update src/index.ts exports, and rebuild

**Files:**
- Verify: `r3ngine-plugins/active_directory/ui/src/index.ts`

The barrel `src/index.ts` only needs to export page components. It does not need to export stores, hooks, or graph utilities — those are internal to the plugin bundle.

- [ ] **Step 1: Verify src/index.ts is correct**

Current content should be:

```typescript
export { ADAssessmentsPage } from './pages/ADAssessmentsPage';
export { ADAssessmentDetailPage } from './pages/ADAssessmentDetailPage';
export { ADGraphExplorerPage } from './pages/ADGraphExplorerPage';
export { ADTrustAnalyticsPage } from './pages/ADTrustAnalyticsPage';
export { ADExposureDashboardPage } from './pages/ADExposureDashboardPage';
```

No changes needed. The internal modules (stores, hooks, graph utilities) are all bundled into `dist/index.js` but not re-exported — they're internal implementation details.

- [ ] **Step 2: Final build**

```bash
cd r3ngine-plugins/active_directory/ui
npm run build
```

Expected output:
```
✓ 100+ modules transformed.
dist/index.js  ~900 kB │ gzip: ~230 kB
✓ built in ~2s
```

The bundle is larger than before due to `cytoscape-dagre` and `cytoscape-fcose` being bundled. This is expected.

- [ ] **Step 3: Sync to container**

```bash
docker cp "d:/Repos/r3ngine/r3ngine-plugins/active_directory" r3ngine-web-1:/usr/src/app/plugins_data/
docker exec r3ngine-web-1 python manage.py sync_plugin_ui
```

Expected: no errors. `dist/index.js` deployed to `MEDIA_ROOT/plugins/active_directory/ui/`.

- [ ] **Step 4: Final commit**

```bash
cd r3ngine-plugins
git add active_directory/ui/dist/ active_directory/ui/src/index.ts
git commit -m "build(ad-ui): final Phase 7+8 build — enterprise graph + realtime streaming complete"
```

---

## Self-Review Checklist

### Phase 7 Spec Coverage

| Requirement | Task |
|-------------|------|
| Hierarchical layouts | Task 3 — dagre layout config |
| Radial layout | Task 3 — concentric layout |
| Cluster layout | Task 3 — fcose layout |
| Infrastructure topology layout | Task 3 — grid layout |
| Compound nodes | Task 7 — Cytoscape natively supports compound parents in stylesheet |
| Progressive rendering | Task 7 — layout `fit: false`, viewport preserved on data refresh |
| Semantic grouping | Task 2 — 17 typed node styles; Task 6 — legend |
| Minimap | NOT in this plan — `cy.fit()` via toolbar covers core use case; add as follow-up |
| Smooth zoom | Task 7 — `wheelSensitivity: 0.2` |
| Focus mode | Tasks 5, 6, 7 — useGraphFocus + GraphToolbar focus toggle |
| Contextual side panels | Task 6 — GraphNodePanel |
| Search centering | Tasks 5, 7 — useGraphSearch + cy.animate center |
| Node highlighting | Tasks 5, 7 — `.searched`, `.highlighted`, `.dimmed` CSS classes |
| NOT raw force layout | Task 7 — default layout is `dagre` (hierarchical) |

### Phase 8 Spec Coverage

| Requirement | Task |
|-------------|------|
| `workflow_progress` event | Tasks 8, 13 |
| `graph_updated` event | Tasks 8, 12, 13 |
| `finding_detected` event | Tasks 8, 13 |
| `trust_discovered` event | Tasks 8, 13 |
| `identity_discovered` event | Tasks 8, 13 |
| `correlation_completed` event | Tasks 8, 13 |
| Avoid rerender explosions | Task 10 — 150ms batch flush |
| Preserve viewport state | Tasks 5, 7 — useGraphViewport |
| Stream progressively | Task 10 — useWsEventBus |
| Smooth animations | Task 11 — WorkflowProgressPanel progress bar transition |

### Known gaps (not in this plan, per scope)
- Full compound node grouping UI (expand/collapse parent nodes) — requires additional UX
- Minimap overlay — requires either `cytoscape-navigator` CSS integration or a custom SVG implementation
- Web Workers for layout computation — requires Cytoscape Web Worker API (experimental)
