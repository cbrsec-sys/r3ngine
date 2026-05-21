import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Card, 
  CardContent, 
  Switch, 
  FormControlLabel, 
  TextField, 
  Button, 
  LinearProgress,
  Alert,
  Stack,
  Snackbar,
  CircularProgress,
  Checkbox
} from '@mui/material';
import { 
  Settings, 
  Shield, 
  Save, 
  RefreshCw,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';
import { useParams } from '@tanstack/react-router';
import { ConfirmDialog } from '../../../components/ConfirmDialog';
import { useProxySettings, useUpdateProxySettings, useFetchProxies, useProxyTaskStatus } from '../api';
import { TacticalPanel } from '../../../components/TacticalPanel';

export const ProxySettingsPage: React.FC = () => {
  const { projectSlug = 'default' } = useParams({ strict: false }) as any;
  const { data: settings, isLoading: isSettingsLoading } = useProxySettings(projectSlug);
  const updateSettings = useUpdateProxySettings(projectSlug);
  const fetchProxies = useFetchProxies(projectSlug);
  
  const [useProxy, setUseProxy] = useState(false);
  const [useProxychains, setUseProxychains] = useState(false);
  const [proxyList, setProxyList] = useState('');
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [fetchLimit, setFetchLimit] = useState<number | 'custom'>(1000);
  const [customLimit, setCustomLimit] = useState<string>('2000');
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const { data: taskStatus } = useProxyTaskStatus(projectSlug, currentTaskId);

  useEffect(() => {
    if (settings) {
      setUseProxy(settings.use_proxy);
      setUseProxychains(settings.use_proxychains);
      setProxyList(settings.proxies);
    }
  }, [settings]);

  useEffect(() => {
    if (taskStatus?.status === 'SUCCESS' && taskStatus.result) {
      setProxyList(taskStatus.result);
      setUseProxy(true);
      setSnackbar({
        open: true,
        message: 'Proxy list updated from fetch task.',
        severity: 'success',
      });
      setCurrentTaskId(null);
    } else if (taskStatus?.status === 'FAILURE') {
      setSnackbar({
        open: true,
        message: 'Failed to fetch proxies automatically.',
        severity: 'error',
      });
      setCurrentTaskId(null);
    }
  }, [taskStatus]);

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const handleSave = () => {
    updateSettings.mutate({ use_proxy: useProxy, use_proxychains: useProxychains, proxies: proxyList }, {
      onSuccess: () => {
        setSnackbar({
          open: true,
          message: 'Proxy settings saved successfully.',
          severity: 'success',
        });
      },
      onError: (error: any) => {
        setSnackbar({
          open: true,
          message: `Failed to save proxy settings: ${error?.response?.data?.message || error.message || 'Unknown error'}`,
          severity: 'error',
        });
      },
    });
  };

  const handleLimitChange = (option: number | 'custom') => {
    setFetchLimit(option);
  };

  const handleFetchClick = () => {
    setIsConfirmOpen(true);
  };

  const handleConfirmFetch = () => {
    setIsConfirmOpen(false);
    setSnackbar({
      open: true,
      message: 'Initiating proxy fetch task...',
      severity: 'success'
    });
    
    const finalLimit = fetchLimit === 'custom' ? parseInt(customLimit, 10) || 1000 : fetchLimit;
    
    fetchProxies.mutate(finalLimit, {
      onSuccess: (data) => {
        setCurrentTaskId(data.task_id);
        setSnackbar({
          open: true,
          message: 'Proxy fetch task started. Monitoring progress...',
          severity: 'success'
        });
      },
      onError: (error: any) => {
        setSnackbar({
          open: true,
          message: `Failed to start proxy fetch: ${error?.response?.data?.error || error?.response?.data?.message || error.message || 'Unknown error'}`,
          severity: 'error'
        });
      }
    });
  };

  if (isSettingsLoading) return <LinearProgress sx={{ bgcolor: 'rgba(0, 243, 255, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff' } }} />;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ 
            fontFamily: 'Orbitron', 
            fontWeight: 900, 
            letterSpacing: 2, 
            color: '#fff',
            textShadow: '0 0 20px rgba(0, 243, 255, 0.5)',
            mb: 1
          }}>
            PROXY SETTINGS
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', letterSpacing: 1 }}>
            TRAFFIC ANONYMIZATION & RATE LIMIT BYPASS
          </Typography>
        </Box>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', fontFamily: 'Orbitron' }}>
          SETTINGS {'>'} <span style={{ color: '#00f3ff' }}>PROXY</span>
        </Typography>
      </Box>

      <Stack spacing={3}>
        <Alert 
          severity="info" 
          icon={<Shield size={20} />}
          sx={{ 
            bgcolor: 'rgba(0, 243, 255, 0.05)', 
            color: '#00f3ff',
            border: '1px solid rgba(0, 243, 255, 0.2)',
            '& .MuiAlert-icon': { color: '#00f3ff' }
          }}
        >
          Every website has a limit to requests. Exceeding it results in blocks. 
          Using proxies is highly recommended for reliable recon and OSINT.
        </Alert>

        <TacticalPanel title="CONFIGURATION" icon={<Settings size={20} />}>
          <Box sx={{ p: 1 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <FormControlLabel
                control={
                  <Switch 
                    checked={useProxy} 
                    onChange={(e) => setUseProxy(e.target.checked)}
                    sx={{
                      '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                      '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' }
                    }}
                  />
                }
                label={
                  <Typography sx={{ color: '#fff', fontFamily: 'Orbitron', fontSize: '0.9rem', fontWeight: 700 }}>
                    ENABLE PROXY ROTATION
                  </Typography>
                }
              />

              <FormControlLabel
                control={
                  <Switch 
                    checked={useProxychains} 
                    onChange={(e) => setUseProxychains(e.target.checked)}
                    disabled={!useProxy}
                    sx={{
                      '& .MuiSwitch-switchBase.Mui-checked': { color: '#ff00ff' },
                      '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#ff00ff' }
                    }}
                  />
                }
                label={
                  <Box>
                    <Typography sx={{ color: '#fff', fontFamily: 'Orbitron', fontSize: '0.9rem', fontWeight: 700 }}>
                      USE PROXYCHAINS WRAPPER
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', display: 'block' }}>
                      Force proxy usage for tools without native proxy support
                    </Typography>
                  </Box>
                }
              />
            </Box>
            
            <Box sx={{ mt: 3, p: 2, bgcolor: 'rgba(255, 255, 255, 0.02)', borderRadius: 1, border: '1px solid rgba(0, 243, 255, 0.1)' }}>
              <Typography variant="subtitle2" sx={{ color: '#fff', fontFamily: 'Orbitron', mb: 1, fontWeight: 700 }}>
                AUTOMATED PROXY FETCH LIMIT
              </Typography>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', display: 'block', mb: 2 }}>
                Select the maximum number of raw proxies to scrape and check for liveness.
              </Typography>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ alignItems: 'flex-start' }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={fetchLimit === 500}
                      onChange={() => handleLimitChange(500)}
                      sx={{ color: 'rgba(0, 243, 255, 0.3)', '&.Mui-checked': { color: '#00f3ff' } }}
                    />
                  }
                  label={<Typography sx={{ color: '#fff', fontFamily: 'Orbitron', fontSize: '0.85rem' }}>500 Proxies</Typography>}
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={fetchLimit === 1000}
                      onChange={() => handleLimitChange(1000)}
                      sx={{ color: 'rgba(0, 243, 255, 0.3)', '&.Mui-checked': { color: '#00f3ff' } }}
                    />
                  }
                  label={<Typography sx={{ color: '#fff', fontFamily: 'Orbitron', fontSize: '0.85rem' }}>1000 Proxies</Typography>}
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={fetchLimit === 5000}
                      onChange={() => handleLimitChange(5000)}
                      sx={{ color: 'rgba(0, 243, 255, 0.3)', '&.Mui-checked': { color: '#00f3ff' } }}
                    />
                  }
                  label={<Typography sx={{ color: '#fff', fontFamily: 'Orbitron', fontSize: '0.85rem' }}>5000 Proxies</Typography>}
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={fetchLimit === 'custom'}
                      onChange={() => handleLimitChange('custom')}
                      sx={{ color: 'rgba(0, 243, 255, 0.3)', '&.Mui-checked': { color: '#00f3ff' } }}
                    />
                  }
                  label={<Typography sx={{ color: '#fff', fontFamily: 'Orbitron', fontSize: '0.85rem' }}>Custom</Typography>}
                />
              </Stack>
              {fetchLimit === 'custom' && (
                <TextField
                  type="number"
                  label="Enter Proxy Count"
                  value={customLimit}
                  onChange={(e) => setCustomLimit(e.target.value)}
                  size="small"
                  sx={{
                    mt: 2,
                    width: 200,
                    '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.5)', fontFamily: 'Orbitron', fontSize: '0.8rem' },
                    '& .MuiOutlinedInput-root': {
                      color: '#fff',
                      bgcolor: 'rgba(255,255,255,0.02)',
                      '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                      '&:hover fieldset': { borderColor: 'rgba(0, 243, 255, 0.3)' },
                      '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
                    }
                  }}
                />
              )}
            </Box>

            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', mt: 3, mb: 1, fontWeight: 600 }}>
              PROXY LIST (ONE PER LINE)
            </Typography>
            <TextField
              multiline
              rows={12}
              fullWidth
              variant="outlined"
              value={proxyList}
              onChange={(e) => setProxyList(e.target.value)}
              disabled={!useProxy}
              placeholder="http://ip:port\nhttp://user:pass@ip:port"
              sx={{
                '& .MuiOutlinedInput-root': {
                  color: '#fff',
                  bgcolor: 'rgba(255,255,255,0.02)',
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                  '&:hover fieldset': { borderColor: 'rgba(0, 243, 255, 0.3)' },
                  '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
                },
                '& .Mui-disabled': {
                  opacity: 0.5,
                  bgcolor: 'rgba(0,0,0,0.2)'
                }
              }}
            />

            {currentTaskId && (
              <Box sx={{ mb: 4, p: 2, bgcolor: 'rgba(255, 255, 255, 0.02)', borderRadius: 1, border: '1px solid rgba(0, 243, 255, 0.1)' }}>
                <Stack direction="row" spacing={2} sx={{ alignItems: 'center', mb: 2 }}>
                  {(!taskStatus || taskStatus.status === 'PROGRESS' || taskStatus.status === 'PENDING') ? (
                    <CircularProgress size={20} sx={{ color: '#00f3ff' }} />
                  ) : taskStatus.status === 'SUCCESS' ? (
                    <CheckCircle2 size={20} color="#00ff00" />
                  ) : (
                    <AlertCircle size={20} color="#ff0055" />
                  )}
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="subtitle2" sx={{ color: '#fff', fontFamily: 'Orbitron', mb: 0.5 }}>
                      {taskStatus?.message || 'Initializing task...'}
                    </Typography>
                    <LinearProgress 
                      variant="determinate" 
                      value={taskStatus?.progress || 0} 
                      sx={{ 
                        height: 6, 
                        borderRadius: 3,
                        bgcolor: 'rgba(255, 255, 255, 0.05)',
                        '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff' }
                      }} 
                    />
                  </Box>
                  <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.5)', fontFamily: 'Orbitron' }}>
                    {taskStatus?.progress || 0}%
                  </Typography>
                </Stack>
                {taskStatus?.status === 'SUCCESS' && (
                  <Alert severity="success" sx={{ bgcolor: 'rgba(0, 255, 0, 0.05)', color: '#00ff00', border: '1px solid rgba(0, 255, 0, 0.2)' }}>
                    Proxies fetched and verified. Review the list below and click SAVE to apply changes.
                  </Alert>
                )}
                {taskStatus?.status === 'FAILURE' && (
                  <Alert severity="error" sx={{ bgcolor: 'rgba(255, 0, 0, 0.05)', color: '#ff0055', border: '1px solid rgba(255, 0, 0, 0.2)' }}>
                    Task failed: {taskStatus.result || 'Unknown error during verification'}
                  </Alert>
                )}
              </Box>
            )}

            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
              <Button
                variant="outlined"
                startIcon={<RefreshCw size={18} className={fetchProxies.isPending ? 'spin' : ''} />}
                onClick={handleFetchClick}
                disabled={fetchProxies.isPending || (taskStatus && taskStatus.status === 'PROGRESS')}
                sx={{
                  borderColor: '#00f3ff',
                  color: '#00f3ff',
                  fontFamily: 'Orbitron',
                  fontWeight: 800,
                  '&:hover': { borderColor: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.05)' }
                }}
              >
                FETCH & UPDATE
              </Button>

              <Button
                variant="contained"
                startIcon={<Save size={18} />}
                onClick={handleSave}
                disabled={updateSettings.isPending}
                sx={{
                  bgcolor: 'rgba(0, 243, 255, 0.1)',
                  color: '#00f3ff',
                  border: '1px solid rgba(0, 243, 255, 0.3)',
                  fontFamily: 'Orbitron',
                  fontWeight: 800,
                  '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)', boxShadow: '0 0 20px rgba(0, 243, 255, 0.4)' }
                }}
              >
                {updateSettings.isPending ? 'SAVING...' : 'SAVE PROXIES'}
              </Button>
            </Box>
          </Box>
        </TacticalPanel>
      </Stack>

      <ConfirmDialog
        open={isConfirmOpen}
        title="FETCH PROXIES"
        message={`This will initiate an automated task to fetch up to ${fetchLimit === 'custom' ? customLimit : fetchLimit} raw proxies and verify them. The existing list will be updated with the results. You will need to SAVE the settings once the task completes. Proceed?`}
        onConfirm={handleConfirmFetch}
        onClose={() => setIsConfirmOpen(false)}
        type="info"
        isDestructive={false}
        confirmText="INITIATE FETCH"
      />

      <Snackbar 
        open={snackbar.open} 
        autoHideDuration={6000} 
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={handleCloseSnackbar} 
          severity={snackbar.severity} 
          variant="filled"
          sx={{ 
            fontFamily: 'Orbitron', 
            fontSize: '0.8rem',
            fontWeight: 700,
            bgcolor: snackbar.severity === 'success' ? 'rgba(0, 243, 255, 0.9)' : 'rgba(255, 0, 85, 0.9)',
            color: '#000',
            '& .MuiAlert-icon': { color: '#000' }
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};
