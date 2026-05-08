import React from 'react';
import { Grid, Box, Typography } from '@mui/material';
import type { Plugin } from '../api/pluginsApi';
import PluginCard from './PluginCard';

interface Props {
  plugins: Plugin[];
}

const PluginInventory: React.FC<Props> = ({ plugins }) => {
  if (plugins.length === 0) {
    return (
      <Box sx={{ textAlign: "center", py: 10 }}>
        <Typography variant="h6" color="text.secondary">
          No plugins installed yet.
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Upload a plugin archive to get started.
        </Typography>
      </Box>
    );
  }

  return (
    <Grid container spacing={3} sx={{ justifyContent: "center" }}>
      {plugins?.length > 0 && plugins?.map((plugin) => (
        <Grid size={{ xs: 12, md: 6, lg: 4 }} key={plugin.slug} sx={{ justifyContent: "center" }}>
          <PluginCard plugin={plugin} />
        </Grid>
      )) || (
          <Box sx={{ textAlign: "center", py: 10 }}>
            <Typography variant="h6" color="text.secondary">
              No plugins installed yet.
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Upload a plugin archive to get started.
            </Typography>
          </Box>
        )}
    </Grid>
  );
};

export default PluginInventory;
