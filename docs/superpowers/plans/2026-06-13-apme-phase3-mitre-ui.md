# APME Phase 3 — MITRE ATT&CK UI Attribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface MITRE ATT&CK technique badges and tactic color-coded strips in the web UI (`AttackPathsTab.tsx`) and React Native mobile app (`AttackPathStep.tsx`, `AttackPathCard.tsx`). All data is already in the API response after Phase 1 — this phase is purely frontend.

**Prerequisite:** Phase 1 must be complete. The `serialize_path` output already includes `mitre_technique`, `mitre_tactic`, `mitre_tactic_color`, `mitre_technique_name`, `mitre_tactic_display` on each step, and `mitre_techniques`/`mitre_tactics` arrays on the path object.

**Architecture:** TypeScript interface additions are additive (no breaking changes). The `MitreBadge` component is created inline in each file — no shared component library change needed. Tactic color map is duplicated intentionally between web and mobile since they cannot share code.

**Tech Stack:** React 18, TypeScript, MUI v5 (`@mui/material`), React Native (Expo), `lucide-react`/`lucide-react-native`

---

## File Map

| Action | File | Repo |
|---|---|---|
| MODIFY | `frontend/src/features/scans/api/useAttackPaths.ts` | r3ngine |
| MODIFY | `frontend/src/features/scans/components/AttackPathsTab.tsx` | r3ngine |
| MODIFY | `r3ngine-mobile/src/components/Intelligence/AttackPathStep.tsx` | r3ngine-mobile |
| MODIFY | `r3ngine-mobile/src/components/Intelligence/AttackPathCard.tsx` | r3ngine-mobile |

Build verification commands:
```bash
# Web
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npm run build 2>&1 | tail -10"

# Mobile (type check only — no simulator available in CI)
cd r3ngine-mobile && npx tsc --noEmit 2>&1 | head -20
```

---

## Task 1: TypeScript Interface Additions

**Files:**
- Modify: `frontend/src/features/scans/api/useAttackPaths.ts`

- [ ] **Step 1.1 — Add MITRE fields to `EnrichedNode`, `AttackStep`, `AttackPath`, and `AttackPathsResponse`**

Replace the interface block (lines 33–70 in the current file) with:

```typescript
export interface EnrichedNode {
  id: string;
  type: string;
  subtype: string;
  name?: string;
  severity?: number;
  cvss_score?: number;
  vuln_id?: number | null;
  // Phase 3 additions
  cwe?: string;        // e.g. "CWE-89"
  technique?: string;  // e.g. "T1190"
}

export interface AttackStep {
  from: string;
  to: string;
  action: string;
  edge_type: string;
  confidence: number;
  validated: boolean;
  status: 'validated' | 'inferred';
  from_node?: EnrichedNode;
  to_node?: EnrichedNode;
  // Phase 3 additions
  mitre_technique?: string;        // e.g. "T1190"
  mitre_technique_name?: string;   // e.g. "Exploit Public-Facing Application"
  mitre_tactic?: string;           // e.g. "initial-access"
  mitre_tactic_display?: string;   // e.g. "Initial Access"
  mitre_tactic_color?: string;     // e.g. "#ff4444"
}

export interface AttackPath {
  path_id: string;
  risk: string;
  score: number;
  step_count: number;
  steps: AttackStep[];
  potential_impact: string;
  remediation_priority: number;
  vulnerability_id: number | null;
  explanation?: string;
  // Phase 3 additions
  mitre_techniques?: string[];  // unique technique IDs in this path
  mitre_tactics?: string[];     // unique tactic slugs in this path
}

export interface AttackPathsResponse {
  total_paths: number;
  paths: AttackPath[];
  speculative_paths?: AttackPath[];  // Phase 1 addition
}
```

- [ ] **Step 1.2 — Verify TypeScript compiles**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npx tsc --noEmit 2>&1 | head -20"
```

Expected: No errors (new optional fields are backward-compatible).

- [ ] **Step 1.3 — Commit to r3ngine repo**

```bash
git add frontend/src/features/scans/api/useAttackPaths.ts
git commit -m "feat(ui): add MITRE ATT&CK fields to AttackPath TypeScript interfaces"
```

---

## Task 2: Web UI — `MitreBadge` Component

**Files:**
- Modify: `frontend/src/features/scans/components/AttackPathsTab.tsx`

The `MitreBadge` component is added inline (near the top of the file after existing imports and the `RiskBadge` component). It is then placed in three locations:
1. `TimelineConnector` — shows technique per step edge
2. `RenderNode` — shows CWE + technique for Vulnerability nodes
3. `AttackPathCard` — shows tactic strip below the step-count bar

- [ ] **Step 2.1 — Add `TACTIC_COLORS` constant and `MitreBadge` component**

Insert this block immediately after the closing `};` of the existing `RiskBadge` component (around line 84):

```tsx
// ─── MITRE Tactic color palette ──────────────────────────────────────────────
const TACTIC_COLORS: Record<string, string> = {
  'initial-access':       '#ff4444',
  'execution':            '#ff8800',
  'persistence':          '#ffcc00',
  'privilege-escalation': '#aa00ff',
  'defense-evasion':      '#0088ff',
  'credential-access':    '#00aaff',
  'discovery':            '#00ff88',
  'lateral-movement':     '#ff00aa',
  'collection':           '#ff6600',
  'command-and-control':  '#9944ff',
  'exfiltration':         '#ff0066',
  'impact':               '#ff0000',
  'resource-development': '#888888',
  'reconnaissance':       '#44aaff',
};

// ─── MITRE ATT&CK badge ───────────────────────────────────────────────────────
interface MitreBadgeProps {
  technique?: string;
  techniqueName?: string;
  tactic?: string;
  tacticDisplay?: string;
  tacticColor?: string;
}

const MitreBadge: React.FC<MitreBadgeProps> = ({
  technique,
  techniqueName,
  tactic,
  tacticDisplay,
  tacticColor,
}) => {
  if (!technique) return null;
  const color = tacticColor ?? TACTIC_COLORS[tactic ?? ''] ?? '#888888';
  const tooltip = `${techniqueName ?? technique}${tacticDisplay ? ` · ${tacticDisplay}` : ''}`;
  return (
    <Tooltip title={tooltip} arrow placement="top">
      <Box
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          px: 0.75,
          py: 0.15,
          borderRadius: 0.5,
          borderLeft: `3px solid ${color}`,
          bgcolor: `${color}12`,
          color,
          fontSize: '0.48rem',
          fontWeight: 900,
          fontFamily: 'monospace',
          letterSpacing: 0.5,
          cursor: 'default',
          userSelect: 'none',
          whiteSpace: 'nowrap',
          flexShrink: 0,
        }}
      >
        ATT&amp;CK&nbsp;·&nbsp;{technique}
      </Box>
    </Tooltip>
  );
};
```

- [ ] **Step 2.2 — Add MITRE badge to `TimelineConnector`**

In `TimelineConnector`, find the `Stack direction="row"` that renders `[edge_type chip] [CONF: N%] [VALIDATED]` (around line 250–270). After the existing confidence `Typography`, add the badge:

```tsx
// After the existing confidence Typography, before the status Stack:
<MitreBadge
  technique={step.mitre_technique}
  techniqueName={step.mitre_technique_name}
  tactic={step.mitre_tactic}
  tacticDisplay={step.mitre_tactic_display}
  tacticColor={step.mitre_tactic_color}
/>
```

The full updated Stack inside `TimelineConnector` should read:

```tsx
<Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 0.8, flexWrap: 'wrap', gap: 0.5 }}>
  <Chip
    label={step.edge_type}
    size="small"
    sx={{
      height: 16,
      fontSize: '0.55rem',
      fontWeight: 900,
      bgcolor: 'rgba(112,0,255,0.1)',
      border: '1px solid rgba(112,0,255,0.2)',
      color: '#aa00ff',
      fontFamily: 'Orbitron',
    }}
  />
  <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', fontWeight: 700 }}>
    CONF: <Box component="span" sx={{ color: '#00f3ff' }}>{(step.confidence * 100).toFixed(0)}%</Box>
  </Typography>
  <MitreBadge
    technique={step.mitre_technique}
    techniqueName={step.mitre_technique_name}
    tactic={step.mitre_tactic}
    tacticDisplay={step.mitre_tactic_display}
    tacticColor={step.mitre_tactic_color}
  />
  <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center', ml: 'auto' }}>
    <Icon size={10} color={edgeColor} />
    <Typography sx={{ fontSize: '0.55rem', color: edgeColor, fontWeight: 900, fontFamily: 'Orbitron', letterSpacing: 0.5 }}>
      {step.status.toUpperCase()}
    </Typography>
  </Stack>
</Stack>
```

- [ ] **Step 2.3 — Add CWE + technique badges to `RenderNode` for Vulnerability nodes**

In `RenderNode`, find the existing CVSS `Chip` (around line 165–180). After it, add CWE and technique badges inside the same `Stack direction="row"`:

```tsx
{type === 'Vulnerability' && node?.cvss_score !== undefined && (
  <Chip
    label={`CVSS ${node.cvss_score}`}
    size="small"
    sx={{
      height: 14, fontSize: '0.5rem', fontFamily: 'monospace',
      bgcolor: 'rgba(255,255,255,0.05)', color: '#fff',
      border: '1px solid rgba(255,255,255,0.1)',
      '& .MuiChip-label': { px: 0.5 }
    }}
  />
)}
{type === 'Vulnerability' && node?.cwe && (
  <Chip
    label={node.cwe}
    size="small"
    sx={{
      height: 14, fontSize: '0.5rem', fontFamily: 'monospace',
      bgcolor: 'rgba(255,159,0,0.08)', color: '#ff9f00',
      border: '1px solid rgba(255,159,0,0.15)',
      '& .MuiChip-label': { px: 0.5 }
    }}
  />
)}
{type === 'Vulnerability' && node?.technique && (
  <MitreBadge technique={node.technique} />
)}
```

- [ ] **Step 2.4 — Add tactic strip to `AttackPathCard`**

In `AttackPathCard`, find the step-counts bar section (the `Box` containing the validated/inferred `Chip` elements, around line 422–453). Immediately after the closing `</Box>` of that section, add:

```tsx
{/* MITRE tactic strip */}
{path.mitre_tactics && path.mitre_tactics.length > 0 && (
  <Box sx={{ px: 2, pb: expanded ? 0 : 1.5, pt: 0.5 }}>
    <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', gap: 0.5 }}>
      {path.mitre_tactics.map((tactic) => {
        const color = TACTIC_COLORS[tactic] ?? '#888888';
        const label = tactic.replace(/-/g, ' ').toUpperCase();
        return (
          <Box
            key={tactic}
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              px: 0.75,
              py: 0.2,
              borderRadius: 4,
              bgcolor: `${color}10`,
              border: `1px solid ${color}30`,
              color,
              fontSize: '0.45rem',
              fontWeight: 900,
              fontFamily: 'Orbitron',
              letterSpacing: 0.5,
              whiteSpace: 'nowrap',
            }}
          >
            {label}
          </Box>
        );
      })}
    </Stack>
  </Box>
)}
```

- [ ] **Step 2.5 — Add MITRE legend entry**

In the legend `Stack` (around line 700–735), add a new entry after the existing three:

```tsx
<Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
  <Box sx={{
    display: 'inline-flex', px: 0.5, py: 0.1, borderRadius: 0.5,
    borderLeft: '3px solid #ff4444', bgcolor: 'rgba(255,68,68,0.08)',
    color: '#ff4444', fontSize: '0.5rem', fontWeight: 900, fontFamily: 'monospace',
  }}>
    ATT&amp;CK · T1190
  </Box>
  <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.6)', fontWeight: 600 }}>
    <Box component="span" sx={{ color: '#ff4444', fontWeight: 800 }}>MITRE ATT&amp;CK</Box>
    {' — technique badge, colored by tactic'}
  </Typography>
</Stack>
```

- [ ] **Step 2.6 — Build the frontend**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npm run build 2>&1 | tail -15"
```

Expected: `✓ built in X.Xs` with no TypeScript errors. If there are errors, check for missing imports (ensure `Tooltip` is imported from `@mui/material` — it already is in the existing file).

- [ ] **Step 2.7 — Commit to r3ngine repo**

```bash
git add frontend/src/features/scans/components/AttackPathsTab.tsx
git commit -m "feat(ui): add MitreBadge component with tactic colors; show ATT&CK technique on step edges, CWE on vuln nodes, tactic strip on path cards"
```

---

## Task 3: Mobile — Update `AttackPathStep.tsx`

**Files:**
- Modify: `r3ngine-mobile/src/components/Intelligence/AttackPathStep.tsx`

- [ ] **Step 3.1 — Update `EnrichedNode` and `PathStepData` interfaces**

Replace the existing `EnrichedNode` and `PathStepData` interfaces (lines 8–28):

```typescript
export interface EnrichedNode {
  id: string;
  type: string;
  subtype: string;
  name?: string;
  severity?: number;
  cvss_score?: number;
  vuln_id?: number | null;
  // Phase 3
  cwe?: string;
  technique?: string;
}

export interface PathStepData {
  from: string;
  to: string;
  action: string;
  confidence: number;
  edge_type: string;
  validated: boolean;
  status?: 'validated' | 'inferred';
  from_node?: EnrichedNode;
  to_node?: EnrichedNode;
  // Phase 3
  mitre_technique?: string;
  mitre_technique_name?: string;
  mitre_tactic?: string;
  mitre_tactic_display?: string;
  mitre_tactic_color?: string;
}
```

- [ ] **Step 3.2 — Add `TACTIC_COLORS` and `MitreBadge` RN component**

Add this block immediately after the imports (before `export interface EnrichedNode`):

```typescript
const TACTIC_COLORS: Record<string, string> = {
  'initial-access':       '#ff4444',
  'execution':            '#ff8800',
  'persistence':          '#ffcc00',
  'privilege-escalation': '#aa00ff',
  'defense-evasion':      '#0088ff',
  'credential-access':    '#00aaff',
  'discovery':            '#00ff88',
  'lateral-movement':     '#ff00aa',
  'collection':           '#ff6600',
  'command-and-control':  '#9944ff',
  'exfiltration':         '#ff0066',
  'impact':               '#ff0000',
  'resource-development': '#888888',
  'reconnaissance':       '#44aaff',
};

interface MitreBadgeProps {
  technique?: string;
  tactic?: string;
  tacticColor?: string;
}

const MitreBadge: React.FC<MitreBadgeProps> = ({ technique, tactic, tacticColor }) => {
  if (!technique) return null;
  const color = tacticColor ?? TACTIC_COLORS[tactic ?? ''] ?? '#888888';
  return (
    <View style={[mStyles.mitreBadge, {
      borderLeftColor: color,
      backgroundColor: color + '14',
    }]}>
      <Text style={[mStyles.mitreText, { color }]}>
        ATT&CK {technique}
      </Text>
    </View>
  );
};

const mStyles = StyleSheet.create({
  mitreBadge: {
    borderLeftWidth: 3,
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 3,
    marginRight: 4,
  },
  mitreText: {
    fontSize: 8,
    fontWeight: '900',
    fontFamily: 'monospace',
  },
});
```

- [ ] **Step 3.3 — Add MITRE badge and CWE to `RenderNode` Vulnerability header row**

In `RenderNode`, find the `nodeHeaderRow` View that contains `nodeTypeText` and `cvssBadge`. Update it to also include `MitreBadge`:

```tsx
<View style={styles.nodeHeaderRow}>
  <Text style={styles.nodeTypeText}>{type.toUpperCase()} ({subtype.toUpperCase()})</Text>
  {type === 'Vulnerability' && node?.cvss_score !== undefined && (
    <View style={styles.cvssBadge}>
      <Text style={styles.cvssText}>CVSS {node.cvss_score}</Text>
    </View>
  )}
  {type === 'Vulnerability' && node?.cwe && (
    <View style={[styles.cvssBadge, { borderColor: 'rgba(255,159,0,0.3)', backgroundColor: 'rgba(255,159,0,0.08)' }]}>
      <Text style={[styles.cvssText, { color: '#ff9f00' }]}>{node.cwe}</Text>
    </View>
  )}
  {type === 'Vulnerability' && node?.technique && (
    <MitreBadge technique={node.technique} />
  )}
</View>
```

- [ ] **Step 3.4 — Add MITRE badge to the edge `edgeHeaderRow` in `AttackPathStep`**

In `AttackPathStep`, find the `edgeHeaderRow` View inside `actionBox` (around line 130–140). Update it:

```tsx
<View style={styles.edgeHeaderRow}>
  <View style={[styles.actionBadge, { borderColor: edgeColor + '44', backgroundColor: 'rgba(255,255,255,0.01)' }]}>
    <Text style={[styles.actionText, { color: Theme.colors.text }]}>{step.edge_type.toUpperCase()}</Text>
  </View>
  <MitreBadge
    technique={step.mitre_technique}
    tactic={step.mitre_tactic}
    tacticColor={step.mitre_tactic_color}
  />
  <View style={styles.statusRow}>
    <EdgeIcon size={10} color={edgeColor} />
    <Text style={[styles.statusText, { color: edgeColor }]}>{(step.status || 'inferred').toUpperCase()}</Text>
  </View>
</View>
```

- [ ] **Step 3.5 — Type-check the mobile file**

```bash
cd d:/Repos/r3ngine/r3ngine-mobile && npx tsc --noEmit 2>&1 | head -20
```

Expected: No errors. If there are errors about `StyleSheet` being used before declaration, move `mStyles` after the `TACTIC_COLORS` constant or use a forward reference pattern — in RN this works fine as long as `mStyles` is defined before the component render call, which it is since it's a module-level const.

- [ ] **Step 3.6 — Commit to r3ngine-mobile repo**

```bash
cd d:/Repos/r3ngine/r3ngine-mobile
git add src/components/Intelligence/AttackPathStep.tsx
git commit -m "feat(mobile): add MitreBadge RN component; show ATT&CK technique on edges, CWE on vuln nodes"
```

---

## Task 4: Mobile — Update `AttackPathCard.tsx`

**Files:**
- Modify: `r3ngine-mobile/src/components/Intelligence/AttackPathCard.tsx`

- [ ] **Step 4.1 — Update the props interface to include MITRE tactics**

Replace the existing `AttackPathCardProps` interface:

```typescript
import { ScrollView } from 'react-native';

const TACTIC_COLORS: Record<string, string> = {
  'initial-access':       '#ff4444',
  'execution':            '#ff8800',
  'persistence':          '#ffcc00',
  'privilege-escalation': '#aa00ff',
  'defense-evasion':      '#0088ff',
  'credential-access':    '#00aaff',
  'discovery':            '#00ff88',
  'lateral-movement':     '#ff00aa',
  'collection':           '#ff6600',
  'command-and-control':  '#9944ff',
  'exfiltration':         '#ff0066',
  'impact':               '#ff0000',
  'resource-development': '#888888',
  'reconnaissance':       '#44aaff',
};

interface AttackPathCardProps {
  path: {
    path_id: string;
    risk: string;
    score: number;
    step_count: number;
    potential_impact: string;
    mitre_tactics?: string[];   // Phase 3 addition
  };
  onPress: () => void;
}
```

- [ ] **Step 4.2 — Add tactic pill strip to the card footer**

In the `TouchableOpacity` body, after the `impactText` and before the footer `View`, add the tactic strip:

```tsx
{/* MITRE tactic strip */}
{path.mitre_tactics && path.mitre_tactics.length > 0 && (
  <ScrollView
    horizontal
    showsHorizontalScrollIndicator={false}
    style={styles.tacticScroll}
    contentContainerStyle={styles.tacticScrollContent}
  >
    {path.mitre_tactics.map((tactic) => {
      const color = TACTIC_COLORS[tactic] ?? '#888888';
      return (
        <View
          key={tactic}
          style={[
            styles.tacticPill,
            { borderColor: color + '44', backgroundColor: color + '12' },
          ]}
        >
          <Text style={[styles.tacticText, { color }]}>
            {tactic.replace(/-/g, ' ').toUpperCase()}
          </Text>
        </View>
      );
    })}
  </ScrollView>
)}
```

- [ ] **Step 4.3 — Add StyleSheet entries for tactic strip**

Add to the existing `StyleSheet.create({...})` object:

```typescript
tacticScroll: {
  marginBottom: 12,
},
tacticScrollContent: {
  gap: 6,
  paddingRight: 4,
},
tacticPill: {
  paddingHorizontal: 8,
  paddingVertical: 3,
  borderRadius: 10,
  borderWidth: 1,
},
tacticText: {
  fontSize: 7,
  fontWeight: '900',
  fontFamily: 'Orbitron',
  letterSpacing: 0.5,
},
```

- [ ] **Step 4.4 — Type-check**

```bash
cd d:/Repos/r3ngine/r3ngine-mobile && npx tsc --noEmit 2>&1 | head -20
```

Expected: No errors.

- [ ] **Step 4.5 — Commit to r3ngine-mobile repo**

```bash
cd d:/Repos/r3ngine/r3ngine-mobile
git add src/components/Intelligence/AttackPathCard.tsx
git commit -m "feat(mobile): add MITRE tactic pill strip to AttackPathCard footer"
```

---

## Task 5: Final Build Verification

- [ ] **Step 5.1 — Full frontend build**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npm run build 2>&1 | tail -10"
```

Expected:
```
✓ built in X.Xs
```
No TypeScript errors, no missing module errors.

- [ ] **Step 5.2 — Mobile TypeScript check (both changed files)**

```bash
cd d:/Repos/r3ngine/r3ngine-mobile && npx tsc --noEmit 2>&1
```

Expected: Clean (0 errors).

- [ ] **Step 5.3 — Tag Phase 3 complete on r3ngine**

```bash
cd d:/Repos/r3ngine
git tag apme-phase3-complete
git push origin apme-enhancement --tags
```

- [ ] **Step 5.4 — Tag Phase 3 complete on r3ngine-mobile**

```bash
cd d:/Repos/r3ngine/r3ngine-mobile
git tag apme-phase3-complete
git push origin HEAD --tags
```

---

## Visual Reference

### Web — `TimelineConnector` (step edge area)
```
┌──────────────────────────────────────────────────────────────────┐
│  [LEADS_TO]  CONF: 85%  [ATT&CK · T1190]              VALIDATED │
│                                                                  │
│  Exploit sqli to gain db_access                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Web — `RenderNode` (vulnerability node)
```
┌──────────────────────────────────────────────────────────────────┐
│  🛡  VULNERABILITY (SQLI)  │ CVSS 9.8 │ CWE-89 │ ATT&CK·T1190  │
│     SQL Injection via login form                         [VIEW]  │
└──────────────────────────────────────────────────────────────────┘
```

### Web — `AttackPathCard` tactic strip (below step count bar)
```
[ ✓ 2 validated ] [ ? 3 inferred ]
[ INITIAL ACCESS ] [ EXECUTION ] [ CREDENTIAL ACCESS ]
```

### Mobile — `AttackPathCard` footer
```
👣 4 Steps    ⚡ Score: 7.8
[ INITIAL ACCESS ][ EXECUTION ][ LATERAL MOVEMENT ] →
```

### Mobile — `AttackPathStep` edge area
```
┌────────────────────────────────────────────────────────┐
│  [LEADS_TO]  [ATT&CK T1190]              ✓ VALIDATED   │
│  Exploit sqli to gain db_access                        │
│  Confidence: 85%                                       │
└────────────────────────────────────────────────────────┘
```

---

**Phase 3 complete.** All three phases of the APME enhancement are now implemented:
- Phase 1: Engine hardening (noise reduction, 8 new constraints, EPSS/KEV scoring, MITRE utils)
- Phase 2: 72-rule knowledge base across 13 kill-chain categories
- Phase 3: MITRE ATT&CK UI attribution on web and mobile
