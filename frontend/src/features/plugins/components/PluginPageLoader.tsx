import React, { useEffect, useState } from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';

/**
 * Dynamically loads a named page component from a plugin's built ES module.
 *
 * Plugin UI is served at /media/plugins/{slug}/ui/index.js (built by build_plugins.py).
 * The module must export page components by name. Pass exportName to select which one.
 *
 * Example:
 *   <PluginPageLoader pluginSlug="active_directory" exportName="ADAssessmentsPage" assessmentId={42} />
 */
interface Props {
  pluginSlug: string;
  exportName: string;
  [key: string]: unknown;
}

const PluginPageLoader: React.FC<Props> = ({ pluginSlug, exportName, ...rest }) => {
  const [Component, setComponent] = useState<React.ComponentType<Record<string, unknown>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const moduleUrl = `/media/plugins/${pluginSlug}/ui/index.js?v=${Date.now()}`;
        const mod = await import(/* @vite-ignore */ moduleUrl) as Record<string, unknown>;

        if (cancelled) return;

        const exported = mod[exportName];
        if (typeof exported !== 'function') {
          setError(`Plugin "${pluginSlug}" does not export "${exportName}".`);
          return;
        }
        setComponent(() => exported as React.ComponentType<Record<string, unknown>>);
      } catch (err) {
        if (!cancelled) {
          console.error(`[PluginPageLoader] Failed to load ${pluginSlug}:`, err);
          setError(`Could not load plugin "${pluginSlug}". Ensure it is installed and synced.`);
        }
      }
    };

    void load();
    return () => { cancelled = true; };
  }, [pluginSlug, exportName]);

  if (error) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="error" variant="body2">{error}</Typography>
      </Box>
    );
  }

  if (!Component) {
    return (
      <Box sx={{ p: 10, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  return <Component {...rest} />;
};

export default PluginPageLoader;
