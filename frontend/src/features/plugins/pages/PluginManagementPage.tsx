import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Tabs,
  Tab,
  CircularProgress,
  Backdrop,
  Snackbar,
  Alert,
  Stack
} from '@mui/material';
import { 
  Upload as UploadIcon, 
  Extension as ExtensionIcon, 
  AccountTree as PipelineIcon
} from '@mui/icons-material';
import { 
  Shield
} from 'lucide-react';
import { 
  usePlugins, 
  useUploadPlugin, 
  useMarketplacePlugins, 
  useRefreshMarketplace 
} from '../api/pluginsApi';
import PluginInventory from '../components/PluginInventory';
import PipelineBuilder from '../components/PipelineBuilder';

const PluginManagementPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const { data: plugins, isLoading: isPluginsLoading, error: pluginsError } = usePlugins();
  const { data: marketplaceData, isLoading: isMarketplaceLoading } = useMarketplacePlugins();
  const uploadMutation = useUploadPlugin();
  const refreshMarketplaceMutation = useRefreshMarketplace();

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      uploadMutation.mutate(file, {
        onSuccess: () => {
          setSnackbar({ open: true, message: 'Plugin uploaded successfully!', severity: 'success' });
        },
        onError: (err: any) => {
          setSnackbar({ 
            open: true, 
            message: `Upload failed: ${err.response?.data?.error || err.message}`, 
            severity: 'error' 
          });
        }
      });
    }
  };

  const handleRefreshMarketplace = () => {
    refreshMarketplaceMutation.mutate(undefined, {
      onSuccess: () => {
        setSnackbar({ open: true, message: 'Marketplace index refreshed.', severity: 'success' });
      },
      onError: (err: any) => {
        setSnackbar({ 
          open: true, 
          message: `Refresh failed: ${err.message}`, 
          severity: 'error' 
        });
      }
    });
  };

  const isLoading = isPluginsLoading || (isMarketplaceLoading && !marketplaceData);

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", flexDirection: 'column', alignItems: "center", justifyContent: 'center', height: '60vh', gap: 2 }}>
        <CircularProgress sx={{ color: '#00f3ff' }} />
        <Typography sx={{ fontFamily: 'Orbitron', color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', letterSpacing: 2 }}>
          BROWSING THE MARKETPLACE...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4 }}>
      <Backdrop
        sx={{ color: '#00f3ff', zIndex: (theme) => theme.zIndex.drawer + 1, flexDirection: 'column', gap: 2, backdropFilter: 'blur(4px)' }}
        open={uploadMutation.isPending}
      >
        <CircularProgress color="inherit" size={60} thickness={2} />
        <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 900, letterSpacing: 2 }}>
          INSTALLING PLUGIN...
        </Typography>
      </Backdrop>

      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", mb: 6 }}>
        <Box>
          <Stack direction="row" spacing={2} sx={{ alignItems: 'center', mb: 1 }}>
            <Shield size={32} color="#00f3ff" />
            <Typography variant="h3" sx={{ fontFamily: 'Orbitron', fontWeight: 900, letterSpacing: -1, color: '#fff' }}>
              PLUGIN ORCHESTRATION
            </Typography>
          </Stack>
          <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.5)', maxWidth: 600 }}>
            Extend system capabilities with modular reconnaissance engines and intelligence layers. 
            Maintain total control over the execution pipeline.
          </Typography>
        </Box>
        <Button
          variant="contained"
          component="label"
          startIcon={<UploadIcon />}
          sx={{
            bgcolor: '#00f3ff',
            color: '#000',
            fontFamily: 'Orbitron',
            fontWeight: 900,
            borderRadius: 0,
            px: 4,
            py: 1.5,
            clipPath: 'polygon(10% 0, 100% 0, 90% 100%, 0% 100%)',
            '&:hover': { bgcolor: '#00d8e4' }
          }}
        >
          UPLOAD PLUGIN
          <input type="file" hidden accept=".zip" onChange={handleFileUpload} />
        </Button>
      </Box>

      {pluginsError && (
        <Alert 
          severity="error" 
          variant="outlined"
          sx={{ mb: 4, borderColor: 'rgba(255, 0, 60, 0.3)', color: '#ff003c', bgcolor: 'rgba(255, 0, 60, 0.05)' }}
        >
          CRITICAL ERROR: Failed to synchronize with orchestration backend.
        </Alert>
      )}

      <Paper sx={{ 
        borderRadius: 0, 
        overflow: 'hidden', 
        bgcolor: 'transparent',
        border: '1px solid rgba(255,255,255,0.05)'
      }}>
        <Tabs
          value={activeTab}
          onChange={(_, val) => setActiveTab(val)}
          sx={{ 
            borderBottom: '1px solid rgba(255,255,255,0.1)',
            bgcolor: 'rgba(255,255,255,0.02)',
            '& .MuiTab-root': {
              minHeight: 70,
              fontFamily: 'Orbitron',
              fontWeight: 800,
              fontSize: '0.8rem',
              letterSpacing: 1,
              color: 'rgba(255,255,255,0.4)',
              '&.Mui-selected': { color: '#00f3ff' }
            },
            '& .MuiTabs-indicator': { bgcolor: '#00f3ff', height: 3 }
          }}
        >
          <Tab icon={<ExtensionIcon sx={{ fontSize: 20 }} />} iconPosition="start" label="INVENTORY" />
          <Tab icon={<PipelineIcon sx={{ fontSize: 20 }} />} iconPosition="start" label="PIPELINE BUILDER" />
        </Tabs>

        <Box sx={{ p: 4, minHeight: '400px' }}>
          {activeTab === 0 ? (
            <PluginInventory 
              plugins={plugins || []} 
              marketplacePlugins={marketplaceData}
              onRefreshMarketplace={handleRefreshMarketplace}
              isRefreshingMarketplace={refreshMarketplaceMutation.isPending}
            />
          ) : (
            <PipelineBuilder plugins={plugins || []} />
          )}
        </Box>
      </Paper>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity} 
          variant="filled"
          sx={{ 
            fontFamily: 'Orbitron', 
            fontWeight: 800,
            bgcolor: snackbar.severity === 'success' ? '#00ffaa' : '#ff003c',
            color: '#000',
            borderRadius: 0
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default PluginManagementPage;
