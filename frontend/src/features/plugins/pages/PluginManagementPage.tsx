import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Grid,
  Paper,
  Tabs,
  Tab,
  CircularProgress,
  Alert
} from '@mui/material';
import { Upload as UploadIcon, Extension as ExtensionIcon, AccountTree as PipelineIcon } from '@mui/icons-material';
import { usePlugins, useUploadPlugin } from '../api/pluginsApi';
import PluginInventory from '../components/PluginInventory';
import PipelineBuilder from '../components/PipelineBuilder';

const PluginManagementPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const { data: plugins, isLoading, error } = usePlugins();
  const uploadMutation = useUploadPlugin();

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      uploadMutation.mutate(file);
    }
  };

  if (isLoading) return <Box sx={{ display: "flex", justifyContent: "center", p: 5 }}><CircularProgress /></Box>;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: "bold" }} gutterBottom>
            Plugin Orchestration
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Extend reNgine with custom engines, tasks, and UI modules.
          </Typography>
        </Box>
        <Button
          variant="contained"
          component="label"
          startIcon={<UploadIcon />}
          sx={{
            borderRadius: '12px',
            textTransform: 'none',
            px: 3,
            py: 1.5,
            boxShadow: '0 4px 14px 0 rgba(0,118,255,0.39)'
          }}
        >
          Upload Plugin
          <input type="file" hidden accept=".zip" onChange={handleFileUpload} />
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>Error loading plugins: {(error as any).message}</Alert>}

      <Paper sx={{ borderRadius: '16px', overflow: 'hidden', mb: 4, background: 'rgba(255, 255, 255, 0.05)', backdropFilter: 'blur(10px)' }}>
        <Tabs
          value={activeTab}
          onChange={(_, val) => setActiveTab(val)}
          sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}
        >
          <Tab icon={<ExtensionIcon />} iconPosition="start" label="Inventory" sx={{ minHeight: 64 }} />
          <Tab icon={<PipelineIcon />} iconPosition="start" label="Pipeline Builder" sx={{ minHeight: 64 }} />
        </Tabs>

        <Box sx={{ p: 3 }}>
          {activeTab === 0 ? (
            <PluginInventory plugins={plugins || []} />
          ) : (
            <PipelineBuilder plugins={plugins || []} />
          )}
        </Box>
      </Paper>
    </Box>
  );
};

export default PluginManagementPage;
