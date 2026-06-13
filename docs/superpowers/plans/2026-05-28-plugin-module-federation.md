# Plugin UI Module Federation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `window.*` globals approach for plugin UI loading with Vite Module Federation so React and MUI are genuinely shared at runtime — no globals hacks, no jsx-runtime conflicts, no custom `externalGlobalsPlugin`.

**Architecture:** Host Vite app exposes shared modules (React, ReactDOM, MUI) via `@originjs/vite-plugin-federation`. Each plugin Vite build declares those same modules as `shared` and exposes its entry point as a remote. `PluginPageLoader` loads the remote entry file and imports the named component. Shared modules are deduplicated automatically by the federation runtime.

**Tech Stack:** `@originjs/vite-plugin-federation` (host + plugin), Vite 5, React 18, TanStack Router

**Current state (as of 2026-05-28):**
- Host: `frontend/vite.config.ts` — no federation config
- Host: `frontend/src/main.tsx` — manually sets `window.React`, `window.ReactDOM`, etc.
- Host: `frontend/src/features/plugins/components/PluginPageLoader.tsx` — dynamic `import(moduleUrl)` of plugin's `index.js`
- Plugin: `r3ngine-plugins/active_directory/ui/vite.config.ts` — custom `externalGlobalsPlugin` + `jsxRuntime: 'classic'` workaround
- Plugin served from: Django `PluginUIView` at `/plugins-ui/{slug}/{path}`
- Plugin files on disk: `web/plugins_data/{slug}/ui/index.js` (bind-mounted into container)

---

## Task 1: Add federation to host Vite config

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: Install the federation plugin in the host**

```bash
cd frontend && npm install @originjs/vite-plugin-federation --save-dev
```

- [ ] **Step 2: Run to verify it installs without conflicts**

```bash
npm list @originjs/vite-plugin-federation
```
Expected: shows version (1.3.x or later)

- [ ] **Step 3: Add federation config to host vite.config.ts**

Read `frontend/vite.config.ts` first to see the current plugin list, then add federation to the plugins array. The host declares no `remotes` (plugins are loaded dynamically by slug, not statically declared) and exposes the shared modules:

```ts
import federation from '@originjs/vite-plugin-federation';

// Inside defineConfig plugins array, add:
federation({
  name: 'r3ngine_host',
  remotes: {},
  shared: {
    react: { singleton: true, requiredVersion: '^18.0.0' },
    'react-dom': { singleton: true, requiredVersion: '^18.0.0' },
    '@mui/material': { singleton: true },
    '@mui/icons-material': { singleton: true },
    'lucide-react': { singleton: true },
  },
}),
```

- [ ] **Step 4: Build host to verify no errors**

```bash
cd frontend && npm run build 2>&1 | tail -20
```
Expected: build succeeds, output includes `__federation_shared_*` chunks.

- [ ] **Step 5: Remove window globals from main.tsx**

In `frontend/src/main.tsx`, remove the manual `window.React = React` etc. lines — they're no longer needed with federation.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/vite.config.ts frontend/src/main.tsx
git commit -m "feat(plugins): add Vite module federation to host, remove window globals"
```

---

## Task 2: Update PluginPageLoader to use federation remote loading

**Files:**
- Modify: `frontend/src/features/plugins/components/PluginPageLoader.tsx`

- [ ] **Step 1: Update the loader to import the remote entry then the component**

Federation remotes expose a `remoteEntry.js` file. The pattern for dynamic federation loading:

```tsx
const load = async () => {
  // 1. Load the remote entry (registers the remote's shared scope)
  const remoteUrl = `/plugins-ui/${pluginSlug}/remoteEntry.js`;
  await import(/* @vite-ignore */ remoteUrl);

  // 2. Import the exposed component from the federation container
  // The container name matches what the plugin declares as `name` in its federation config
  const containerName = pluginSlug; // e.g. 'active_directory'
  const container = (window as any)[containerName];
  await container.init(__webpack_share_scopes__.default);
  const factory = await container.get('./ADPluginApp');
  const mod = factory();
  const exported = mod[exportName];
  if (typeof exported !== 'function') {
    setError(`Plugin "${pluginSlug}" does not export "${exportName}".`);
    return;
  }
  setComponent(() => exported as React.ComponentType<Record<string, unknown>>);
};
```

Note: `@originjs/vite-plugin-federation` uses a Vite-compatible API, not Webpack's `__webpack_share_scopes__`. Use the federation runtime API instead:

```tsx
import { loadRemoteModule } from '@originjs/vite-plugin-federation/dist/client';

const mod = await loadRemoteModule({
  remoteEntry: `/plugins-ui/${pluginSlug}/remoteEntry.js`,
  remoteName: pluginSlug,
  exposedModule: './ADPluginApp',
});
```

Check the `@originjs/vite-plugin-federation` docs for the exact client-side API at the version installed.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep PluginPageLoader
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/plugins/components/PluginPageLoader.tsx
git commit -m "feat(plugins): update PluginPageLoader to use federation remote loading"
```

---

## Task 3: Update active_directory plugin Vite config for federation

**Files:**
- Modify: `r3ngine-plugins/active_directory/ui/package.json`
- Modify: `r3ngine-plugins/active_directory/ui/vite.config.ts`
- Modify: `r3ngine-plugins/active_directory/ui/src/index.ts` (verify exports)

- [ ] **Step 1: Install federation plugin in the AD plugin**

```bash
cd r3ngine-plugins/active_directory/ui && npm install @originjs/vite-plugin-federation --save-dev
```

- [ ] **Step 2: Replace externalGlobalsPlugin with federation config**

Replace the entire current `vite.config.ts` content:

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import federation from '@originjs/vite-plugin-federation';

export default defineConfig({
  plugins: [
    react(),
    federation({
      name: 'active_directory',
      filename: 'remoteEntry.js',
      exposes: {
        './ADPluginApp': './src/pages/ADPluginApp',
      },
      shared: {
        react: { singleton: true, requiredVersion: '^18.0.0' },
        'react-dom': { singleton: true, requiredVersion: '^18.0.0' },
        '@mui/material': { singleton: true },
        '@mui/icons-material': { singleton: true },
        'lucide-react': { singleton: true },
      },
    }),
  ],
  build: {
    target: 'esnext',
    outDir: 'dist',
    emptyOutDir: true,
  },
});
```

Note: federation handles externals automatically via `shared`. No `rollupOptions.external` needed. No `externalGlobalsPlugin`. No `jsxRuntime: 'classic'`. No `define: { 'process.env': ... }`.

- [ ] **Step 3: Build the plugin**

```bash
cd r3ngine-plugins/active_directory/ui && npm run build 2>&1 | tail -15
```
Expected: `dist/remoteEntry.js` and `dist/index.js` (or similar chunk files) are created.

- [ ] **Step 4: Verify remoteEntry.js exists**

```bash
ls -lh r3ngine-plugins/active_directory/ui/dist/
```
Expected: `remoteEntry.js` present.

- [ ] **Step 5: Copy dist to plugins_data for testing**

```bash
cp r3ngine-plugins/active_directory/ui/dist/* web/plugins_data/active_directory/ui/
```

- [ ] **Step 6: Commit to plugin repo**

```bash
cd r3ngine-plugins
git add active_directory/ui/package.json active_directory/ui/vite.config.ts
git commit -m "feat: replace externalGlobalsPlugin with Vite module federation"
```

---

## Task 4: Update Django PluginUIView and installer for federation output

**Files:**
- Modify: `web/plugins/views.py` — `PluginUIView` already serves any file from `ui/`, no changes needed if dist files land there
- Modify: `web/plugins/utils.py` — `AtomicInstaller` step 7: installer must copy all `ui/dist/` files, not just `index.js`

- [ ] **Step 1: Update AtomicInstaller to copy full dist directory**

In `web/plugins/utils.py`, step 7 of `AtomicInstaller.install()`, change the copy logic to copy the entire `ui/dist/` tree into `plugins_data/{slug}/ui/`:

```python
# Step 7: Place built UI assets in plugin data dir for serving
ui_dist_src = os.path.join(final_dir, 'ui', 'dist')
ui_target = os.path.join(final_dir, 'ui')
if os.path.exists(ui_dist_src):
    # Move dist contents up to ui/ so they're served at /plugins-ui/{slug}/
    for item in os.listdir(ui_dist_src):
        src = os.path.join(ui_dist_src, item)
        dst = os.path.join(ui_target, item)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
        else:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
```

- [ ] **Step 2: Verify PluginUIView serves any path under ui/**

`PluginUIView` already serves `GET /plugins-ui/{slug}/{path}` → `plugins_data/{slug}/ui/{path}`, so `remoteEntry.js` will be served at `/plugins-ui/active_directory/remoteEntry.js` automatically.

- [ ] **Step 3: Test by navigating to the AD plugin page**

In browser: navigate to Active Directory. Check network tab — `remoteEntry.js` should load with 302→200 (authed). No `window.React` references needed.

- [ ] **Step 4: Commit**

```bash
git add web/plugins/utils.py
git commit -m "fix(plugins): installer copies full ui/dist tree for federation remotes"
```

---

## Task 5: Write a plugin template / SDK note for future plugins

**Files:**
- Create: `r3ngine-plugins/PLUGIN_UI_GUIDE.md`

- [ ] **Step 1: Document the federation build pattern**

Write a guide covering:
- Required `vite.config.ts` structure (federation plugin, shared modules, `exposes` map)
- Required `src/index.ts` exports (named export of the main app component)
- Build command: `npm run build` → produces `dist/remoteEntry.js`
- How `PluginPageLoader` loads the component: `exportName` must match the key in `exposes`
- Do NOT use `externalGlobalsPlugin` — federation handles this
- Do NOT set `jsxRuntime: 'classic'` — federation handles React sharing

- [ ] **Step 2: Commit to plugin repo**

```bash
cd r3ngine-plugins
git add PLUGIN_UI_GUIDE.md
git commit -m "docs: add plugin UI development guide for module federation"
```

---

## Self-Review

**Spec coverage:**
- Host federation config ✓ (Task 1)
- PluginPageLoader updated ✓ (Task 2)  
- Plugin build config ✓ (Task 3)
- Installer handles multi-file dist ✓ (Task 4)
- Developer docs ✓ (Task 5)

**Key risk:** `@originjs/vite-plugin-federation`'s client-side dynamic loading API — verify exact import path and function signature from its docs before implementing Task 2. The API changed between v1.2 and v1.3.

**Cleanup after migration:** Remove `window.React` etc. globals from `frontend/src/main.tsx` only AFTER verifying all plugins load correctly with federation. Keep them during transition.
