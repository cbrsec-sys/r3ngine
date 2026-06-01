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
import { useProxySettings, useUpdateProxySettings, useFetchProxies, useProxyTaskStatus, useTorStatus } from '../api';
import { TacticalPanel } from '../../../components/TacticalPanel';
import { ProxyValidationModal } from './ProxyValidationModal';

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
  const [validateOnSave, setValidateOnSave] = useState(false);
  const [useTor, setUseTor] = useState(false);
  const [isValidationModalOpen, setIsValidationModalOpen] = useState(false);
  const { data: torStatus } = useTorStatus();
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
      setUseTor(settings.use_tor ?? false);
    }
  }, [settings]);

  useEffect(() => {
    if (taskStatus?.status === 'SUCCESS' && taskStatus.result) {
      const resultData = taskStatus.result as any;
      const proxyStr = typeof resultData === 'string' ? resultData : (resultData?.proxies || '');
      setProxyList(proxyStr);
      setUseProxy(true);
      setSnackbar({
        open: true,
        message: 'Proxies automatically fetched and saved to database.',
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

  const doSave = (proxies: string, skipValidation: boolean) => {
    updateSettings.mutate({
      use_proxy: useProxy,
      use_proxychains: useProxychains,
      proxies,
      skip_validation: skipValidation,
      use_tor: useTor,
    }, {
      onSuccess: () => {
        setSnackbar({ open: true, message: 'Proxy settings saved successfully.', severity: 'success' });
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

  const handleSave = () => {
    if (validateOnSave && useProxy && proxyList.trim()) {
      setIsValidationModalOpen(true);
    } else {
      doSave(proxyList, true);
    }
  };

  const handleValidationSave = (validProxies: string[]) => {
    setIsValidationModalOpen(false);
    const validList = validProxies.join('\n');
    setProxyList(validList);
    doSave(validList, true);
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

  const parsedProxies = proxyList.split('\n').map(p => p.trim()).filter(p => p.length > 0);

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
        <Box sx={{ textAlign: 'right' }}>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', fontFamily: 'Orbitron', display: 'block', mb: 1 }}>
            SETTINGS {'>'} <span style={{ color: '#00f3ff' }}>PROXY</span>
          </Typography>
          <Box sx={{
            display: 'inline-flex',
            alignItems: 'center',
            bgcolor: 'rgba(0, 243, 255, 0.1)',
            px: 1.5,
            py: 0.5,
            borderRadius: 1,
            border: '1px solid rgba(0, 243, 255, 0.3)'
          }}>
            <Typography variant="caption" sx={{ color: '#00f3ff', fontFamily: 'Orbitron', fontWeight: 700, letterSpacing: 1 }}>
              TOTAL PROXIES: {proxyList.split('\n').filter(p => p.trim() !== '').length}
            </Typography>
          </Box>
        </Box>
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

            <Box sx={{
              mt: 3, p: 2,
              bgcolor: 'rgba(255, 255, 255, 0.02)',
              borderRadius: 1,
              border: '1px solid rgba(0, 243, 255, 0.1)',
              display: 'flex',
              alignItems: 'center',
              gap: 2,
              flexWrap: { xs: 'wrap', md: 'nowrap' },
            }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="subtitle2" sx={{ color: '#fff', fontFamily: 'Orbitron', mb: 0.5, fontWeight: 700 }}>
                  AUTOMATED PROXY FETCH LIMIT
                </Typography>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', display: 'block' }}>
                  Select the maximum number of raw proxies to scrape and check for liveness.
                  (Note: It may take a while to complete [~75000/10m:00s]. Validation rate: ~1/3%)
                </Typography>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0, flexWrap: 'nowrap' }}>
                {([5000, 10000, 25000] as const).map((n) => (
                  <FormControlLabel
                    key={n}
                    control={
                      <Checkbox
                        checked={fetchLimit === n}
                        onChange={() => handleLimitChange(n)}
                        size="small"
                        sx={{ color: 'rgba(0, 243, 255, 0.3)', '&.Mui-checked': { color: '#00f3ff' } }}
                      />
                    }
                    label={<Typography sx={{ color: '#fff', fontFamily: 'Orbitron', fontSize: '0.78rem', whiteSpace: 'nowrap' }}>{n.toLocaleString()} Proxies</Typography>}
                    sx={{ mr: 0 }}
                  />
                ))}
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={fetchLimit === 'custom'}
                      onChange={() => handleLimitChange('custom')}
                      size="small"
                      sx={{ color: 'rgba(0, 243, 255, 0.3)', '&.Mui-checked': { color: '#00f3ff' } }}
                    />
                  }
                  label={<Typography sx={{ color: '#fff', fontFamily: 'Orbitron', fontSize: '0.78rem' }}>Custom</Typography>}
                  sx={{ mr: 0 }}
                />
                {fetchLimit === 'custom' && (
                  <TextField
                    type="number"
                    label="Enter Proxy Count"
                    value={customLimit}
                    onChange={(e) => setCustomLimit(e.target.value)}
                    size="small"
                    sx={{
                      ml: 1,
                      width: 160,
                      '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.5)', fontFamily: 'Orbitron', fontSize: '0.75rem' },
                      '& .MuiOutlinedInput-root': {
                        color: '#fff',
                        bgcolor: 'rgba(255,255,255,0.02)',
                        '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                        '&:hover fieldset': { borderColor: 'rgba(0, 243, 255, 0.3)' },
                        '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
                      },
                    }}
                  />
                )}
              </Box>
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
                    Proxies fetched, verified, and automatically saved to the database.
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

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={validateOnSave}
                      onChange={(e) => setValidateOnSave(e.target.checked)}
                      size="small"
                      sx={{
                        '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                        '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' }
                      }}
                    />
                  }
                  label={
                    <Typography sx={{ color: '#fff', fontFamily: 'Orbitron', fontSize: '0.8rem' }}>
                      VALIDATE ON SAVE
                    </Typography>
                  }
                />
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
          </Box>
        </TacticalPanel>

        {/* TOR Mode */}
        <Card variant="outlined" sx={{ mt: 2 }}>
          <CardContent>
            <Stack direction="row" sx={{ alignItems: 'center', mb: 1 }} spacing={1}>
              <Shield size={18} />
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                TOR Mode
              </Typography>
              <Box
                sx={{
                  ml: 1,
                  px: 1,
                  py: 0.25,
                  borderRadius: 1,
                  bgcolor: torStatus?.running ? 'success.main' : 'grey.600',
                  color: 'white',
                  fontSize: '0.7rem',
                  fontWeight: 'bold',
                }}
              >
                {torStatus?.running ? 'RUNNING' : 'STOPPED'}
              </Box>
            </Stack>

            <Alert severity="warning" sx={{ mb: 2 }}>
              TOR Mode routes all scanning traffic through the TOR network.
              Tools using raw sockets (naabu) will log a warning but run
              without TOR routing. Scanning will be significantly slower than normal.
            </Alert>

            <FormControlLabel
              control={
                <Switch
                  checked={useTor}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setUseTor(checked);
                    if (checked) {
                      setUseProxy(false);
                      setUseProxychains(false);
                    }
                  }}
                  color="warning"
                />
              }
              label="Enable TOR Mode"
            />
          </CardContent>
        </Card>
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

      <ProxyValidationModal
        open={isValidationModalOpen}
        onClose={() => setIsValidationModalOpen(false)}
        onSave={handleValidationSave}
        proxyList={parsedProxies}
        projectSlug={projectSlug}
      />
    </Box>
  );
};
