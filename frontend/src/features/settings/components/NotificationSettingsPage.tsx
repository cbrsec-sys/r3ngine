import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Stack,
  Button,
  Grid,
  Switch,
  TextField,
  Divider,
  CircularProgress,
  Alert,
  Snackbar,
  FormControlLabel,
  Tooltip,
} from '@mui/material';
import { 
  Bell, 
  Activity,
  Zap, 
  Settings, 
  ShieldAlert, 
  FileText, 
  Clock,
  AlertTriangle,
  Search,
  CheckSquare,
  Globe,
  Hash
} from 'lucide-react';
import { useParams } from '@tanstack/react-router';
import { TacticalPanel } from '../../../components/TacticalPanel';
import { useNotificationSettings, useUpdateNotificationSettings } from '../api';
import type { NotificationSettings } from '../api';

export const NotificationSettingsPage: React.FC = () => {
  const { projectSlug } = useParams({ from: '/$projectSlug' });
  const { data: settings, isLoading, error } = useNotificationSettings();
  const updateSettings = useUpdateNotificationSettings();

  const [formData, setFormData] = useState<Partial<NotificationSettings>>({});
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  useEffect(() => {
    if (settings) {
      setFormData(settings);
    }
  }, [settings]);

  const handleChange = (field: keyof NotificationSettings) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async (sendTest: boolean = false) => {
    try {
      await updateSettings.mutateAsync({ ...formData, send_test: sendTest });
      setSnackbar({
        open: true,
        message: sendTest 
          ? 'Settings updated and test notification triggered successfully.' 
          : 'Notification settings updated successfully.',
        severity: 'success',
      });
    } catch (err) {
      setSnackbar({
        open: true,
        message: 'Failed to update notification settings.',
        severity: 'error',
      });
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 10 }}>
        <CircularProgress sx={{ color: '#00f3ff' }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ bgcolor: 'rgba(255, 0, 60, 0.1)', color: '#ff003c', border: '1px solid #ff003c' }}>
          Failed to load notification settings.
        </Alert>
      </Box>
    );
  }

  const sectionHeader = (icon: React.ReactNode, title: string) => (
    <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
      <Box sx={{ 
        p: 1, 
        borderRadius: '8px', 
        bgcolor: 'rgba(0, 243, 255, 0.1)', 
        color: '#00f3ff',
        display: 'flex'
      }}>
        {icon}
      </Box>
      <Typography variant="h6" sx={{ fontFamily: 'Orbitron', fontWeight: 700, letterSpacing: 1 }}>
        {title}
      </Typography>
    </Stack>
  );

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 1100, margin: '0 auto' }}>
      <Grid container spacing={4}>
        {/* Header Section */}
        <Grid size={{ xs: 12, md: 7 }} sx={{ mb: 2 }}>
          <Box>
            <Typography variant="h4" sx={{ fontFamily: 'Orbitron', fontWeight: 900, color: '#fff', mb: 1, letterSpacing: 2 }}>
              NOTIFICATION_LINKS
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', fontFamily: 'Inter', maxWidth: 600 }}>
              Configure tactical relays for real-time operation updates across your infrastructure.
            </Typography>
          </Box>
        </Grid>
        <Grid size={{ xs: 12, md: 5 }} sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
          <Stack direction="row" spacing={2} sx={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button
              variant="outlined"
              size="small"
              onClick={() => handleSave(true)}
              disabled={updateSettings.isPending}
              sx={{
                borderColor: '#00f3ff',
                color: '#00f3ff',
                fontFamily: 'Orbitron',
                fontSize: '11px',
                px: 3,
                height: '36px',
                '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.1)', borderColor: '#00f3ff' }
              }}
            >
              TEST_SIGNAL
            </Button>
            <Button
              variant="contained"
              size="small"
              onClick={() => handleSave(false)}
              disabled={updateSettings.isPending}
              sx={{
                bgcolor: '#00f3ff',
                color: '#000',
                fontFamily: 'Orbitron',
                fontWeight: 900,
                fontSize: '11px',
                px: 3,
                height: '36px',
                '&:hover': { bgcolor: '#00c8d4' }
              }}
            >
              {updateSettings.isPending ? <CircularProgress size={16} color="inherit" /> : 'SAVE_CONFIG'}
            </Button>
          </Stack>
        </Grid>

        {/* Notification Channels */}
        <Grid size={{ xs: 12, md: 7 }}>
          <TacticalPanel title="CHANNEL_CONFIG">
            <Stack spacing={4} sx={{ p: 2 }}>
              {/* Slack */}
              <Box>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Hash size={20} color="#E01E5A" />
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Slack Integration</Typography>
                  </Stack>
                  <Switch 
                    checked={formData.send_to_slack || false} 
                    onChange={handleChange('send_to_slack')}
                    sx={{
                      '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                      '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' }
                    }}
                  />
                </Stack>
                <TextField
                  fullWidth
                  label="Webhook URL"
                  variant="outlined"
                  value={formData.slack_hook_url || ''}
                  onChange={handleChange('slack_hook_url')}
                  disabled={!formData.send_to_slack}
                  placeholder="https://hooks.slack.com/services/..."
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                      '&:hover fieldset': { borderColor: 'rgba(0,243,255,0.5)' },
                    },
                    '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.5)' },
                    '& .MuiInputBase-input': { color: '#fff' }
                  }}
                />
              </Box>

              <Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />

              {/* Discord */}
              <Box>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <ShieldAlert size={20} color="#5865F2" />
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Discord Integration</Typography>
                  </Stack>
                  <Switch 
                    checked={formData.send_to_discord || false} 
                    onChange={handleChange('send_to_discord')}
                    sx={{
                      '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                      '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' }
                    }}
                  />
                </Stack>
                <TextField
                  fullWidth
                  label="Webhook URL"
                  variant="outlined"
                  value={formData.discord_hook_url || ''}
                  onChange={handleChange('discord_hook_url')}
                  disabled={!formData.send_to_discord}
                  placeholder="https://discord.com/api/webhooks/..."
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                      '&:hover fieldset': { borderColor: 'rgba(0,243,255,0.5)' },
                    },
                    '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.5)' },
                    '& .MuiInputBase-input': { color: '#fff' }
                  }}
                />
              </Box>

              <Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />

              {/* Telegram */}
              <Box>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Zap size={20} color="#0088cc" />
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Telegram Integration</Typography>
                  </Stack>
                  <Switch 
                    checked={formData.send_to_telegram || false} 
                    onChange={handleChange('send_to_telegram')}
                    sx={{
                      '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                      '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' }
                    }}
                  />
                </Stack>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12 }} sm={6}>
                    <TextField
                      fullWidth
                      label="Bot Token"
                      variant="outlined"
                      value={formData.telegram_bot_token || ''}
                      onChange={handleChange('telegram_bot_token')}
                      disabled={!formData.send_to_telegram}
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                          '&:hover fieldset': { borderColor: 'rgba(0,243,255,0.5)' },
                        },
                        '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.5)' },
                        '& .MuiInputBase-input': { color: '#fff' }
                      }}
                    />
                  </Grid>
                  <Grid size={{ xs: 12 }} sm={6}>
                    <TextField
                      fullWidth
                      label="Chat ID"
                      variant="outlined"
                      value={formData.telegram_bot_chat_id || ''}
                      onChange={handleChange('telegram_bot_chat_id')}
                      disabled={!formData.send_to_telegram}
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                          '&:hover fieldset': { borderColor: 'rgba(0,243,255,0.5)' },
                        },
                        '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.5)' },
                        Mini: { color: '#fff' }
                      }}
                    />
                  </Grid>
                </Grid>
              </Box>

              <Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />

              {/* Lark */}
              <Box>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Typography sx={{ fontSize: '20px' }}>🐦</Typography>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Lark Integration</Typography>
                  </Stack>
                  <Switch 
                    checked={formData.send_to_lark || false} 
                    onChange={handleChange('send_to_lark')}
                    sx={{
                      '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                      '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' }
                    }}
                  />
                </Stack>
                <TextField
                  fullWidth
                  label="Webhook URL"
                  variant="outlined"
                  value={formData.lark_hook_url || ''}
                  onChange={handleChange('lark_hook_url')}
                  disabled={!formData.send_to_lark}
                  placeholder="https://open.larksuite.com/open-apis/bot/v2/hook/..."
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                      '&:hover fieldset': { borderColor: 'rgba(0,243,255,0.5)' },
                    },
                    '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.5)' },
                    '& .MuiInputBase-input': { color: '#fff' }
                  }}
                />
              </Box>
            </Stack>
          </TacticalPanel>
        </Grid>

        {/* Triggers and Advanced */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Stack spacing={4}>
            <TacticalPanel title="TRIGGER_EVENTS">
              <Stack spacing={2} sx={{ p: 2 }}>
                {[
                  { id: 'send_scan_status_notif', label: 'Scan Status Updates', icon: <Activity size={18} /> },
                  { id: 'send_interesting_notif', label: 'Interesting Subdomains Found', icon: <Bell size={18} /> },
                  { id: 'send_vuln_notif', label: 'Vulnerabilities Discovered', icon: <ShieldAlert size={18} /> },
                  { id: 'send_subdomain_changes_notif', label: 'Subdomain Changes', icon: <Clock size={18} /> },
                ].map((trigger) => (
                  <FormControlLabel
                    key={trigger.id}
                    control={
                      <Switch 
                        checked={formData[trigger.id as keyof NotificationSettings] as boolean || false} 
                        onChange={handleChange(trigger.id as keyof NotificationSettings)}
                        sx={{
                          '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                          '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' }
                        }}
                      />
                    }
                    label={
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Box sx={{ color: 'rgba(255,255,255,0.5)', display: 'flex' }}>{trigger.icon}</Box>
                        <Typography variant="body2">{trigger.label}</Typography>
                      </Stack>
                    }
                    sx={{ 
                      m: 0, 
                      p: 1.5, 
                      borderRadius: '8px', 
                      bgcolor: 'rgba(255,255,255,0.03)',
                      width: '100%',
                      justifyContent: 'space-between',
                      flexDirection: 'row-reverse'
                    }}
                  />
                ))}
              </Stack>
            </TacticalPanel>

            <TacticalPanel title="ADVANCED_OPTIONS">
              <Stack spacing={2} sx={{ p: 2 }}>
                <FormControlLabel
                  control={
                    <Switch 
                      checked={formData.send_scan_output_file || false} 
                      onChange={handleChange('send_scan_output_file')}
                      sx={{
                        '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                        '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' }
                      }}
                    />
                  }
                  label={
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Box sx={{ color: 'rgba(255,255,255,0.5)', display: 'flex' }}><FileText size={18} /></Box>
                      <Box>
                        <Typography variant="body2">Upload Scan Output Files</Typography>
                        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', display: 'block' }}>
                          Available for Discord
                        </Typography>
                      </Box>
                    </Stack>
                  }
                  sx={{ 
                    m: 0, 
                    p: 1.5, 
                    borderRadius: '8px', 
                    bgcolor: 'rgba(255,255,255,0.03)',
                    width: '100%',
                    justifyContent: 'space-between',
                    flexDirection: 'row-reverse'
                  }}
                />

                <FormControlLabel
                  control={
                    <Switch 
                      checked={formData.send_scan_tracebacks || false} 
                      onChange={handleChange('send_scan_tracebacks')}
                      sx={{
                        '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                        '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' }
                      }}
                    />
                  }
                  label={
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Box sx={{ color: 'rgba(255,255,255,0.5)', display: 'flex' }}><AlertTriangle size={18} /></Box>
                      <Box>
                        <Typography variant="body2">Send Task Tracebacks</Typography>
                        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', display: 'block' }}>
                          Include debug info on failures
                        </Typography>
                      </Box>
                    </Stack>
                  }
                  sx={{ 
                    m: 0, 
                    p: 1.5, 
                    borderRadius: '8px', 
                    bgcolor: 'rgba(255,255,255,0.03)',
                    width: '100%',
                    justifyContent: 'space-between',
                    flexDirection: 'row-reverse'
                  }}
                />
              </Stack>
            </TacticalPanel>
          </Stack>
        </Grid>
      </Grid>


      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity}
          sx={{ 
            width: '100%', 
            bgcolor: snackbar.severity === 'success' ? 'rgba(0, 243, 255, 0.1)' : 'rgba(255, 0, 60, 0.1)',
            color: snackbar.severity === 'success' ? '#00f3ff' : '#ff003c',
            border: `1px solid ${snackbar.severity === 'success' ? '#00f3ff' : '#ff003c'}`,
            '& .MuiAlert-icon': { color: snackbar.severity === 'success' ? '#00f3ff' : '#ff003c' }
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};
