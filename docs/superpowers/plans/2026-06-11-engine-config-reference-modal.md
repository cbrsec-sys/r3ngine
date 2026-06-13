# Engine Config Reference Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reference button to both AddEngineModal and EditEngineModal that opens a floating, searchable, syntax-highlighted modal showing all available YAML configuration keys from `full_yaml_config.yaml`.

**Architecture:** A new read-only Django view serves `full_yaml_config.yaml` (copied into `web/scanEngine/reference/` so it lands in the Docker image). A new `useYamlConfigReference` TanStack Query hook fetches the content. A new `EngineConfigReferenceModal` React component renders it with line-numbered, color-coded syntax highlighting and incremental search. A small `BookOpen` icon button wired into `AddEngineModal` and `EditEngineModal` triggers the modal.

**Tech Stack:** React 18, MUI Dialog, lucide-react icons, TypeScript, TanStack Query v5, Python 3 / Django 5.2, Django `@login_required`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| **Copy** | `web/scanEngine/reference/full_yaml_config.yaml` | Repo-root YAML placed inside `web/` so Docker `COPY web/` picks it up |
| **Create** | `frontend/src/features/engines/components/EngineConfigReferenceModal.tsx` | Floating reference modal — fetch, syntax-highlight, search, copy |
| **Create** | `frontend/src/features/engines/components/__tests__/EngineConfigReferenceModal.test.tsx` | Component unit tests |
| **Create** | `web/tests/test_yaml_config_reference.py` | Backend endpoint tests |
| **Modify** | `web/scanEngine/views.py` | Add `yaml_config_reference` view |
| **Modify** | `web/scanEngine/urls.py` | Register URL pattern |
| **Modify** | `frontend/src/features/engines/api/index.ts` | Add `useYamlConfigReference` hook |
| **Modify** | `frontend/src/features/engines/components/AddEngineModal.tsx` | Add icon button + wire modal |
| **Modify** | `frontend/src/features/engines/components/EditEngineModal.tsx` | Add icon button + wire modal |

---

## Task 1: Copy reference file + backend view + URL (TDD)

**Files:**
- Copy: `full_yaml_config.yaml` → `web/scanEngine/reference/full_yaml_config.yaml`
- Modify: `web/scanEngine/views.py`
- Modify: `web/scanEngine/urls.py`
- Create: `web/tests/test_yaml_config_reference.py`

- [ ] **Step 1: Copy `full_yaml_config.yaml` into the web directory**

  From the repo root, copy the file so it is within the Docker build context:

  ```bash
  # Run from repo root d:\Repos\r3ngine
  mkdir -p web/scanEngine/reference
  cp full_yaml_config.yaml web/scanEngine/reference/full_yaml_config.yaml
  ```

  The `docker/web/Dockerfile` does `COPY web/ /usr/src/app/` — the file will be available at
  `/usr/src/app/scanEngine/reference/full_yaml_config.yaml` inside the container.

- [ ] **Step 2: Write failing backend test**

  Create `web/tests/test_yaml_config_reference.py`:

  ```python
  from django.test import TestCase
  from django.contrib.auth.models import User
  from unittest.mock import patch, mock_open

  MOCK_YAML = "subdomain_discovery:\n  uses_tools:\n    - subfinder\n# A comment\n"


  class TestYamlConfigReference(TestCase):
      def setUp(self):
          self.user = User.objects.create_user(username='testref', password='pass123')
          self.client.force_login(self.user)

      @patch('builtins.open', mock_open(read_data=MOCK_YAML))
      def test_returns_yaml_content(self):
          response = self.client.get('/scanEngine/default/yaml_config_reference/')
          self.assertEqual(response.status_code, 200)
          data = response.json()
          self.assertEqual(data['status'], 'success')
          self.assertIn('subdomain_discovery', data['content'])

      @patch('builtins.open', mock_open(read_data=MOCK_YAML))
      def test_content_is_string(self):
          response = self.client.get('/scanEngine/default/yaml_config_reference/')
          data = response.json()
          self.assertIsInstance(data['content'], str)

      def test_requires_auth(self):
          self.client.logout()
          response = self.client.get('/scanEngine/default/yaml_config_reference/')
          # login_required redirects unauthenticated requests
          self.assertIn(response.status_code, [302, 403])
  ```

- [ ] **Step 3: Run test — confirm it fails**

  ```bash
  docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_yaml_config_reference --verbosity=2"
  ```

  Expected: `FAIL` — URL resolves to 404 because the view does not exist yet.

- [ ] **Step 4: Add `yaml_config_reference` view to `web/scanEngine/views.py`**

  Add the following function. Place it immediately after the existing `get_full_yaml_config` function (around line 1290). It needs no project-specific data so it uses only `@login_required`:

  ```python
  @login_required
  def yaml_config_reference(request, slug):
      """Return the full YAML configuration reference (static file, all config keys documented)."""
      import os
      from django.conf import settings
      ref_path = os.path.join(settings.BASE_DIR, 'scanEngine', 'reference', 'full_yaml_config.yaml')
      try:
          with open(ref_path, 'r') as f:
              content = f.read()
          return http.JsonResponse({'status': 'success', 'content': content})
      except FileNotFoundError:
          return http.JsonResponse(
              {'status': 'error', 'content': '', 'message': 'Reference config not found'},
              status=404,
          )
  ```

  Ensure `login_required` is imported — check the top of `views.py` for existing imports:
  ```python
  from django.contrib.auth.decorators import login_required
  ```
  Add it if not already present.

- [ ] **Step 5: Register URL in `web/scanEngine/urls.py`**

  Add the following line with the other `<slug:slug>/...` patterns (after the `get_full_yaml_config` entry):

  ```python
  path('<slug:slug>/yaml_config_reference/', views.yaml_config_reference, name='yaml_config_reference'),
  ```

- [ ] **Step 6: Run tests — confirm they pass**

  ```bash
  docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_yaml_config_reference --verbosity=2"
  ```

  Expected: `3 tests passed`.

- [ ] **Step 7: Commit**

  ```bash
  git add web/scanEngine/reference/full_yaml_config.yaml \
          web/scanEngine/views.py \
          web/scanEngine/urls.py \
          web/tests/test_yaml_config_reference.py
  git commit -m "feat(engines): add yaml_config_reference endpoint serving full reference YAML"
  ```

---

## Task 2: Frontend API hook

**Files:**
- Modify: `frontend/src/features/engines/api/index.ts`

- [ ] **Step 1: Add `useYamlConfigReference` hook**

  Open `frontend/src/features/engines/api/index.ts` and append the following export at the end of the file. The hook follows the same `fetch` + `credentials: 'include'` pattern used by `useEngines` and `useWordlists` already in the file. The `staleTime: Infinity` avoids redundant refetches for this static resource.

  ```typescript
  export function useYamlConfigReference() {
    return useQuery<string>({
      queryKey: ['yaml_config_reference'],
      queryFn: async () => {
        const response = await fetch('/scanEngine/default/yaml_config_reference/', {
          credentials: 'include',
        });
        if (!response.ok) throw new Error('Failed to fetch YAML config reference');
        const json = await response.json();
        return json.content as string;
      },
      staleTime: Infinity,
    });
  }
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add frontend/src/features/engines/api/index.ts
  git commit -m "feat(engines): add useYamlConfigReference query hook"
  ```

---

## Task 3: Create `EngineConfigReferenceModal` component (TDD)

**Files:**
- Create: `frontend/src/features/engines/components/EngineConfigReferenceModal.tsx`
- Create: `frontend/src/features/engines/components/__tests__/EngineConfigReferenceModal.test.tsx`

- [ ] **Step 1: Write failing component tests**

  Create `frontend/src/features/engines/components/__tests__/EngineConfigReferenceModal.test.tsx`:

  ```tsx
  import React from 'react';
  import { render, screen, fireEvent } from '@testing-library/react';
  import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
  import { EngineConfigReferenceModal } from '../EngineConfigReferenceModal';
  import * as api from '../../api';

  jest.mock('../../api');

  const MOCK_YAML = [
    'subdomain_discovery:',
    '  uses_tools:',
    '    - subfinder',
    '# A comment line',
    'port_scan:',
    '  timeout: 5',
  ].join('\n');

  function makeWrapper() {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );
  }

  beforeEach(() => {
    (api.useYamlConfigReference as jest.Mock).mockReturnValue({
      data: MOCK_YAML,
      isLoading: false,
    });
  });

  describe('EngineConfigReferenceModal', () => {
    it('renders modal title when open', () => {
      render(
        <EngineConfigReferenceModal open={true} onClose={jest.fn()} />,
        { wrapper: makeWrapper() }
      );
      expect(screen.getByText('CONFIGURATION REFERENCE')).toBeInTheDocument();
    });

    it('does not render content when closed', () => {
      render(
        <EngineConfigReferenceModal open={false} onClose={jest.fn()} />,
        { wrapper: makeWrapper() }
      );
      expect(screen.queryByText('CONFIGURATION REFERENCE')).not.toBeInTheDocument();
    });

    it('displays YAML lines from fetched content', () => {
      render(
        <EngineConfigReferenceModal open={true} onClose={jest.fn()} />,
        { wrapper: makeWrapper() }
      );
      expect(screen.getByText(/subdomain_discovery/)).toBeInTheDocument();
    });

    it('shows match indicator when search term found', () => {
      render(
        <EngineConfigReferenceModal open={true} onClose={jest.fn()} />,
        { wrapper: makeWrapper() }
      );
      fireEvent.change(screen.getByPlaceholderText('Search configuration keys...'), {
        target: { value: 'subfinder' },
      });
      expect(screen.getByText(/MATCH AT LINE/)).toBeInTheDocument();
    });

    it('shows NO MATCH when search term not present', () => {
      render(
        <EngineConfigReferenceModal open={true} onClose={jest.fn()} />,
        { wrapper: makeWrapper() }
      );
      fireEvent.change(screen.getByPlaceholderText('Search configuration keys...'), {
        target: { value: 'xyz_nonexistent_key' },
      });
      expect(screen.getByText('NO MATCH FOUND')).toBeInTheDocument();
    });

    it('shows line count when no search term', () => {
      render(
        <EngineConfigReferenceModal open={true} onClose={jest.fn()} />,
        { wrapper: makeWrapper() }
      );
      expect(screen.getByText(/6 LINES/)).toBeInTheDocument();
    });

    it('calls onClose when CLOSE button clicked', () => {
      const onClose = jest.fn();
      render(
        <EngineConfigReferenceModal open={true} onClose={onClose} />,
        { wrapper: makeWrapper() }
      );
      fireEvent.click(screen.getByText('CLOSE'));
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('shows loading spinner when isLoading is true', () => {
      (api.useYamlConfigReference as jest.Mock).mockReturnValue({
        data: undefined,
        isLoading: true,
      });
      render(
        <EngineConfigReferenceModal open={true} onClose={jest.fn()} />,
        { wrapper: makeWrapper() }
      );
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });
  ```

- [ ] **Step 2: Run tests — confirm they fail**

  ```bash
  docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npx jest EngineConfigReferenceModal --no-coverage 2>&1 | tail -20"
  ```

  Expected: `Cannot find module '../EngineConfigReferenceModal'`.

- [ ] **Step 3: Create `EngineConfigReferenceModal.tsx`**

  Create `frontend/src/features/engines/components/EngineConfigReferenceModal.tsx`:

  ```tsx
  import React, { useState, useRef, useEffect } from 'react';
  import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    TextField,
    Box,
    Typography,
    CircularProgress,
    InputAdornment,
    IconButton,
    Tooltip,
  } from '@mui/material';
  import { BookOpen, X, Search, Copy, Check } from 'lucide-react';
  import { useYamlConfigReference } from '../api';

  interface EngineConfigReferenceModalProps {
    open: boolean;
    onClose: () => void;
  }

  function colorForLine(line: string): string {
    const trimmed = line.trimStart();
    if (trimmed.startsWith('#')) return 'rgba(255,255,255,0.4)';
    if (/^[a-zA-Z_]/.test(line)) return '#ff3333';         // top-level key
    if (/^ {2}[a-zA-Z_]/.test(line)) return '#e5c07b';    // second-level key
    return '#ffffff';
  }

  export const EngineConfigReferenceModal: React.FC<EngineConfigReferenceModalProps> = ({
    open,
    onClose,
  }) => {
    const [search, setSearch] = useState('');
    const [copied, setCopied] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);
    const { data: content, isLoading } = useYamlConfigReference();

    const lines = content ? content.split('\n') : [];
    const lowerSearch = search.toLowerCase();

    const matchIndex =
      search.length > 0
        ? lines.findIndex(l => l.toLowerCase().includes(lowerSearch))
        : -1;

    useEffect(() => {
      if (matchIndex >= 0 && containerRef.current) {
        const el = containerRef.current.querySelector<HTMLElement>(
          `#ref-line-${matchIndex}`
        );
        el?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
    }, [matchIndex, search]);

    // Reset search when modal closes
    useEffect(() => {
      if (!open) setSearch('');
    }, [open]);

    const handleCopy = async () => {
      if (!content) return;
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    };

    return (
      <Dialog
        open={open}
        onClose={onClose}
        maxWidth="lg"
        fullWidth
        slotProps={{
          paper: {
            sx: {
              bgcolor: '#0a0a0c',
              border: '1px solid rgba(0,243,255,0.2)',
              boxShadow: '0 0 30px rgba(0,243,255,0.1)',
              backgroundImage:
                'linear-gradient(rgba(0,243,255,0.05) 1px, transparent 1px), ' +
                'linear-gradient(90deg, rgba(0,243,255,0.05) 1px, transparent 1px)',
              backgroundSize: '20px 20px',
              maxHeight: '88vh',
            },
          },
        }}
      >
        <DialogTitle
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(0,243,255,0.1)',
            pb: 2,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <BookOpen size={20} style={{ color: '#00f3ff' }} />
            <Typography
              sx={{ fontFamily: 'Orbitron', fontWeight: 800, color: '#fff', letterSpacing: 1 }}
            >
              CONFIGURATION REFERENCE
            </Typography>
          </Box>
          <IconButton onClick={onClose} size="small" sx={{ color: 'rgba(255,255,255,0.5)' }}>
            <X size={20} />
          </IconButton>
        </DialogTitle>

        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2, pb: 1 }}>
          <TextField
            size="small"
            placeholder="Search configuration keys..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            fullWidth
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <Search size={14} style={{ color: 'rgba(0,243,255,0.5)' }} />
                  </InputAdornment>
                ),
              },
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                fontFamily: 'monospace',
                fontSize: '0.75rem',
                color: '#fff',
                '& fieldset': { borderColor: 'rgba(0,243,255,0.3)' },
                '&:hover fieldset': { borderColor: 'rgba(0,243,255,0.5)' },
                '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
              },
              '& input::placeholder': { color: 'rgba(255,255,255,0.3)', opacity: 1 },
            }}
          />

          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
              <CircularProgress size={28} sx={{ color: '#00f3ff' }} />
            </Box>
          ) : (
            <Box
              ref={containerRef}
              sx={{
                fontFamily: 'monospace',
                fontSize: '12px',
                lineHeight: 1.65,
                overflowY: 'auto',
                maxHeight: '62vh',
                bgcolor: 'rgba(0,0,0,0.35)',
                border: '1px solid rgba(0,243,255,0.1)',
                borderRadius: 1,
                p: 1.5,
              }}
            >
              {lines.map((line, i) => {
                const isMatch =
                  search.length > 0 && line.toLowerCase().includes(lowerSearch);
                const color = colorForLine(line);
                const matchStart = isMatch ? line.toLowerCase().indexOf(lowerSearch) : -1;

                return (
                  <Box
                    key={i}
                    id={`ref-line-${i}`}
                    component="div"
                    sx={{
                      display: 'flex',
                      bgcolor: isMatch ? 'rgba(0,243,255,0.07)' : 'transparent',
                      borderRadius: 0.25,
                      px: 0.5,
                    }}
                  >
                    <Box
                      component="span"
                      sx={{
                        color: 'rgba(0,243,255,0.2)',
                        userSelect: 'none',
                        minWidth: '3ch',
                        mr: 1.5,
                        flexShrink: 0,
                        textAlign: 'right',
                        fontSize: '10px',
                        lineHeight: 1.65,
                      }}
                    >
                      {i + 1}
                    </Box>
                    <Box component="span" sx={{ color, whiteSpace: 'pre', flexGrow: 1 }}>
                      {isMatch && matchStart >= 0 ? (
                        <>
                          {line.slice(0, matchStart)}
                          <mark
                            style={{
                              background: 'rgba(0,243,255,0.3)',
                              color: '#fff',
                              borderRadius: '2px',
                            }}
                          >
                            {line.slice(matchStart, matchStart + search.length)}
                          </mark>
                          {line.slice(matchStart + search.length)}
                        </>
                      ) : (
                        line || ' '
                      )}
                    </Box>
                  </Box>
                );
              })}
            </Box>
          )}
        </DialogContent>

        <DialogActions
          sx={{ borderTop: '1px solid rgba(0,243,255,0.1)', px: 2, py: 1.5, gap: 1 }}
        >
          <Typography
            sx={{
              color: 'rgba(255,255,255,0.3)',
              fontSize: '0.65rem',
              fontFamily: 'Orbitron',
              flexGrow: 1,
            }}
          >
            {matchIndex >= 0
              ? `MATCH AT LINE ${matchIndex + 1}`
              : search.length > 0
              ? 'NO MATCH FOUND'
              : `${lines.length} LINES`}
          </Typography>
          <Tooltip title={copied ? 'Copied!' : 'Copy full config to clipboard'}>
            <Button
              size="small"
              onClick={handleCopy}
              disabled={!content}
              startIcon={copied ? <Check size={14} /> : <Copy size={14} />}
              sx={{
                fontFamily: 'Orbitron',
                fontSize: '0.65rem',
                letterSpacing: 1,
                color: copied ? '#00ff88' : '#00f3ff',
                border: `1px solid ${copied ? 'rgba(0,255,136,0.3)' : 'rgba(0,243,255,0.3)'}`,
                '&:hover': {
                  borderColor: copied ? 'rgba(0,255,136,0.6)' : 'rgba(0,243,255,0.6)',
                },
              }}
            >
              {copied ? 'COPIED' : 'COPY ALL'}
            </Button>
          </Tooltip>
          <Button
            size="small"
            onClick={onClose}
            sx={{
              fontFamily: 'Orbitron',
              fontSize: '0.65rem',
              letterSpacing: 1,
              color: 'rgba(255,255,255,0.5)',
              border: '1px solid rgba(255,255,255,0.1)',
              '&:hover': { borderColor: 'rgba(255,255,255,0.3)' },
            }}
          >
            CLOSE
          </Button>
        </DialogActions>
      </Dialog>
    );
  };
  ```

- [ ] **Step 4: Run tests — confirm they pass**

  ```bash
  docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npx jest EngineConfigReferenceModal --no-coverage 2>&1 | tail -20"
  ```

  Expected: `8 tests passed`.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/features/engines/components/EngineConfigReferenceModal.tsx \
          frontend/src/features/engines/components/__tests__/EngineConfigReferenceModal.test.tsx
  git commit -m "feat(engines): add EngineConfigReferenceModal component with search and copy"
  ```

---

## Task 4: Wire reference button into `AddEngineModal`

**File:** `frontend/src/features/engines/components/AddEngineModal.tsx`

The file currently has a `TextField` with `label="YAML CONFIGURATION BLUEPRINT"` at around line 102. We replace that single TextField with a wrapper Box that separates the label (adding the icon button) from the input field itself.

- [ ] **Step 1: Update imports at the top of `AddEngineModal.tsx`**

  Change the lucide-react import line from:
  ```tsx
  import { X, Cpu } from 'lucide-react';
  ```
  To:
  ```tsx
  import { X, Cpu, BookOpen } from 'lucide-react';
  ```

  Add `Tooltip` to the MUI imports:
  ```tsx
  import {
    Dialog, DialogTitle, DialogContent, DialogActions,
    Button, TextField, Box, Typography, IconButton, Tooltip,
  } from '@mui/material';
  ```

  Add the modal import after the existing import block:
  ```tsx
  import { EngineConfigReferenceModal } from './EngineConfigReferenceModal';
  ```

- [ ] **Step 2: Add `refOpen` state inside the component**

  After the existing `const createEngine = useCreateEngine();` line, add:
  ```tsx
  const [refOpen, setRefOpen] = useState(false);
  ```

- [ ] **Step 3: Replace the YAML `TextField` with the labeled wrapper**

  Find and replace the YAML `TextField` block (the one with `label="YAML CONFIGURATION BLUEPRINT"`):

  **Before:**
  ```tsx
  <TextField
    label="YAML CONFIGURATION BLUEPRINT"
    placeholder="# Enter your engine configuration here"
    fullWidth
    multiline
    rows={15}
    value={yaml}
    onChange={(e) => setYaml(e.target.value)}
    variant="filled"
    sx={{
      '& .MuiFilledInput-root': {
        bgcolor: 'rgba(255,255,255,0.03)',
        '&:before, &:after': { display: 'none' },
        border: '1px solid rgba(255,255,255,0.1)',
        color: '#00f3ff',
        fontFamily: 'monospace',
        fontSize: '0.85rem'
      },
      '& .MuiInputLabel-root': { color: 'rgba(0, 243, 255, 0.5)', fontFamily: 'Orbitron', fontSize: '0.7rem' }
    }}
  />
  ```

  **After:**
  ```tsx
  <Box>
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
      <Typography sx={{ color: 'rgba(0,243,255,0.5)', fontFamily: 'Orbitron', fontSize: '0.7rem' }}>
        YAML CONFIGURATION BLUEPRINT
      </Typography>
      <Tooltip title="View configuration reference">
        <IconButton
          size="small"
          onClick={() => setRefOpen(true)}
          sx={{
            color: 'rgba(0,243,255,0.6)',
            p: 0.5,
            '&:hover': { color: '#00f3ff', bgcolor: 'rgba(0,243,255,0.08)' },
          }}
        >
          <BookOpen size={14} />
        </IconButton>
      </Tooltip>
    </Box>
    <TextField
      placeholder="# Enter your engine configuration here"
      fullWidth
      multiline
      rows={15}
      value={yaml}
      onChange={(e) => setYaml(e.target.value)}
      variant="filled"
      sx={{
        '& .MuiFilledInput-root': {
          bgcolor: 'rgba(255,255,255,0.03)',
          '&:before, &:after': { display: 'none' },
          border: '1px solid rgba(255,255,255,0.1)',
          color: '#00f3ff',
          fontFamily: 'monospace',
          fontSize: '0.85rem',
        },
      }}
    />
  </Box>
  ```

- [ ] **Step 4: Add `EngineConfigReferenceModal` render before closing `</Dialog>`**

  Find the closing `</Dialog>` tag at the bottom of the `return` block and insert the modal just before it:

  **Before:**
  ```tsx
      </DialogActions>
    </Dialog>
  );
  ```

  **After:**
  ```tsx
      </DialogActions>
      <EngineConfigReferenceModal open={refOpen} onClose={() => setRefOpen(false)} />
    </Dialog>
  );
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/features/engines/components/AddEngineModal.tsx
  git commit -m "feat(engines): add config reference button to AddEngineModal"
  ```

---

## Task 5: Wire reference button into `EditEngineModal`

**File:** `frontend/src/features/engines/components/EditEngineModal.tsx`

The YAML editor in `EditEngineModal` is a raw `Box` with a `<pre>` overlay and `<textarea>` — no label. We add a label row with the icon button above it.

- [ ] **Step 1: Update imports at the top of `EditEngineModal.tsx`**

  Change the lucide-react import line from:
  ```tsx
  import { X, Cpu, Save } from 'lucide-react';
  ```
  To:
  ```tsx
  import { X, Cpu, Save, BookOpen } from 'lucide-react';
  ```

  Add `Tooltip` to the MUI imports:
  ```tsx
  import {
    Dialog, DialogTitle, DialogContent, DialogActions,
    Button, TextField, Box, Typography, IconButton,
    CircularProgress, Tooltip,
  } from '@mui/material';
  ```

  Add the modal import after the existing import block:
  ```tsx
  import { EngineConfigReferenceModal } from './EngineConfigReferenceModal';
  ```

- [ ] **Step 2: Add `refOpen` state inside the component**

  After the existing `const updateEngine = useUpdateEngine();` line, add:
  ```tsx
  const [refOpen, setRefOpen] = useState(false);
  ```

- [ ] **Step 3: Add label row with reference button before the YAML editor Box**

  Find the YAML editor `Box` (the one with `position: 'relative', width: '100%', height: 500`). Insert the following label row immediately before it:

  **Before:**
  ```tsx
  <Box sx={{
    position: 'relative',
    width: '100%',
    height: 500,
    bgcolor: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 1,
    overflow: 'hidden'
  }}>
  ```

  **After:**
  ```tsx
  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
    <Typography sx={{ color: 'rgba(0,243,255,0.5)', fontFamily: 'Orbitron', fontSize: '0.7rem' }}>
      YAML CONFIGURATION BLUEPRINT
    </Typography>
    <Tooltip title="View configuration reference">
      <IconButton
        size="small"
        onClick={() => setRefOpen(true)}
        sx={{
          color: 'rgba(0,243,255,0.6)',
          p: 0.5,
          '&:hover': { color: '#00f3ff', bgcolor: 'rgba(0,243,255,0.08)' },
        }}
      >
        <BookOpen size={14} />
      </IconButton>
    </Tooltip>
  </Box>
  <Box sx={{
    position: 'relative',
    width: '100%',
    height: 500,
    bgcolor: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 1,
    overflow: 'hidden'
  }}>
  ```

- [ ] **Step 4: Add `EngineConfigReferenceModal` render before closing `</Dialog>`**

  Find the closing `</Dialog>` tag at the bottom of the `return` block and insert the modal just before it:

  **Before:**
  ```tsx
      </DialogActions>
    </Dialog>
  );
  ```

  **After:**
  ```tsx
      </DialogActions>
      <EngineConfigReferenceModal open={refOpen} onClose={() => setRefOpen(false)} />
    </Dialog>
  );
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/features/engines/components/EditEngineModal.tsx
  git commit -m "feat(engines): add config reference button to EditEngineModal"
  ```

---

## Task 6: Build verification

- [ ] **Step 1: Run the full backend test suite**

  ```bash
  docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test --verbosity=1 2>&1 | tail -10"
  ```

  Expected: all existing tests still pass + 3 new tests from `test_yaml_config_reference`.

- [ ] **Step 2: Run the frontend build**

  ```bash
  docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npm run build 2>&1 | tail -20"
  ```

  Expected: `✓ built in Xs` with no TypeScript errors.

- [ ] **Step 3: Final commit (if build produced any auto-fixes)**

  If all tests and build pass with no further changes, no additional commit is needed. If TypeScript reports type errors, fix them and commit with:

  ```bash
  git add -p
  git commit -m "fix(engines): resolve TypeScript errors from config reference modal wiring"
  ```

---

## Self-Review Checklist

- **Spec coverage**
  - [x] Button in AddEngineModal — Task 4
  - [x] Button in EditEngineModal — Task 5
  - [x] Floating modal — Task 3 (MUI Dialog, maxWidth="lg", maxHeight="88vh")
  - [x] full_yaml_config.yaml as source of truth — Task 1 copies the file; backend view reads it directly
  - [x] All available/valid configs shown — full file content rendered line-by-line
  - [x] Search — Task 3, `search` state, `matchIndex`, scroll-to-match, highlight
  - [x] Copy — Task 3, `handleCopy` with `navigator.clipboard.writeText`
  - [x] Auth guard on endpoint — Task 1, `@login_required`
  - [x] Docker accessibility — Task 1, file copied into `web/scanEngine/reference/`
  - [x] Consistent UI theme — cyan #00f3ff, Orbitron font, dark background, grid pattern

- **Type consistency**
  - `useYamlConfigReference()` returns `UseQueryResult<string>` — modal destructures `{ data: content, isLoading }`
  - `EngineConfigReferenceModal` props: `{ open: boolean; onClose: () => void }` — identical across Tasks 3, 4, 5

- **No placeholders** — every step has exact code blocks
