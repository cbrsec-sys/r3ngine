import React from 'react';
import { Grid, Box, Typography } from '@mui/material';
import type { Plugin } from '../api/pluginsApi';
import PluginCard from './PluginCard';

interface Props {
  plugins: Plugin[];
}

const PluginInventory: React.FC<Props> = ({ plugins }) => {
  if (!Array.isArray(plugins) || plugins.length === 0) {
    return (
      <Box sx={{ textAlign: "center", py: 10 }}>
        <Typography variant="h6" color="text.secondary" sx={{ fontFamily: 'Orbitron', fontWeight: 800 }}>
          NO PLUGINS INSTALLED
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Upload a plugin archive to extend system capabilities.
        </Typography>
      </Box>
    );
  }

  return (
    <Grid container spacing={3}>
      {plugins.map((plugin) => (
        <Grid size={{ xs: 12, md: 6, lg: 4 }} key={plugin.slug}>
          <PluginCard plugin={plugin} />
        </Grid>
      ))}
    </Grid>
  );
};

export default PluginInventory;
