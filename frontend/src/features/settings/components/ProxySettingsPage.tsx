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
  Stack
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
    }
  }, [taskStatus]);

  const handleSave = () => {
    updateSettings.mutate({ use_proxy: useProxy, proxies: proxyList });
  };

  const handleFetch = () => {
    if (window.confirm('This will fetch new proxies and update the list. Existing list will be replaced if you save. Continue?')) {
      fetchProxies.mutate(undefined, {
        onSuccess: (data) => {
          setCurrentTaskId(data.task_id);
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

            {currentTaskId && taskStatus && (
              <Box sx={{ mt: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="caption" sx={{ color: '#00f3ff', fontWeight: 800 }}>
                    {taskStatus.message || 'Processing...'}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#fff' }}>
                    {taskStatus.progress || 0}%
                  </Typography>
                </Box>
                <LinearProgress 
                  variant="determinate" 
                  value={taskStatus.progress || 0} 
                  sx={{ 
                    height: 6, 
                    borderRadius: 3,
                    bgcolor: 'rgba(255,255,255,0.05)',
                    '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff' }
                  }} 
                />
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
    </Box>
  );
};
