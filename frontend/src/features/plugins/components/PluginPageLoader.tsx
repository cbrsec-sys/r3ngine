import React, { useEffect, useRef, useState } from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';

/**
 * Mounts a plugin into an isolated DOM container using the plugin's own React root.
 *
 * The plugin's remoteEntry.js (built with @originjs/vite-plugin-federation) exposes
 * a `./mount` module with `mount(el, props)` and `unmount(el)` functions.
 * The plugin manages its own React tree — no shared-React concerns.
 *
 * Example:
 *   <PluginPageLoader pluginSlug="active_directory" exportName="ADPluginApp" assessmentId={42} />
 */
interface Props {
  pluginSlug: string;
  exportName: string;
  [key: string]: unknown;
}

interface RemoteEntry {
  get: (module: string) => Promise<() => { mount: (el: HTMLElement, props: Record<string, unknown>) => void; unmount: (el: HTMLElement) => void }>;
  init: (scope: Record<string, unknown>) => Promise<void>;
}

const PluginPageLoader: React.FC<Props> = ({ pluginSlug, exportName: _exportName, ...rest }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const unmountRef = useRef<(() => void) | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const remoteUrl = `/plugins-ui/${pluginSlug}/assets/remoteEntry.js?v=${Date.now()}`;
        const remote = await import(/* @vite-ignore */ remoteUrl) as RemoteEntry;

        await remote.init({});

        const factory = await remote.get('./mount');
        const { mount, unmount } = factory();

        if (cancelled || !containerRef.current) return;

        mount(containerRef.current, rest);
        unmountRef.current = () => unmount(containerRef.current!);
        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          console.error(`[PluginPageLoader] Failed to load ${pluginSlug}:`, err);
          setError(`Could not load plugin "${pluginSlug}". Ensure it is installed and built.`);
          setLoading(false);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
      unmountRef.current?.();
      unmountRef.current = null;
    };
  }, [pluginSlug]);

  if (error) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="error" variant="body2">{error}</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ position: 'relative', minHeight: 100 }}>
      {loading && (
        <Box sx={{ p: 10, display: 'flex', justifyContent: 'center' }}>
          <CircularProgress size={24} />
        </Box>
      )}
      <div ref={containerRef} />
    </Box>
  );
};

export default PluginPageLoader;
