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
  CircularProgress
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
import { useProxySettings, useUpdateProxySettings, useFetchProxies, useProxyTaskStatus } from '../api';
import { TacticalPanel } from '../../../components/TacticalPanel';

export const ProxySettingsPage: React.FC = () => {
  const { projectSlug = 'default' } = useParams({ strict: false }) as any;
  const { data: settings, isLoading: isSettingsLoading } = useProxySettings(projectSlug);
  const updateSettings = useUpdateProxySettings(projectSlug);
  const fetchProxies = useFetchProxies(projectSlug);
  
  const [useProxy, setUseProxy] = useState(false);
  const [proxyList, setProxyList] = useState('');
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
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
    updateSettings.mutate({ use_proxy: useProxy, proxies: proxyList }, {
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

  const handleFetch = () => {
    if (window.confirm('This will fetch new proxies and update the list. Existing list will be replaced if you save. Continue?')) {
      setSnackbar({
        open: true,
        message: 'Initiating proxy fetch task...',
        severity: 'success'
      });
      fetchProxies.mutate(undefined, {
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
    }
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
                onClick={handleFetch}
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
