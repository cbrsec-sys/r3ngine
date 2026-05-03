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
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  InputAdornment
} from '@mui/material';
import { 
  Settings, 
  Shield, 
  Save, 
  Lock,
  Zap,
  Activity,
  Wind,
  User,
  Clock,
  Globe,
  Monitor
} from 'lucide-react';
import { useParams } from '@tanstack/react-router';
import { useOpSecSettings, useUpdateOpSecSettings } from '../api';
import type { OpSecSettings } from '../api';
import { TacticalPanel } from '../../../components/TacticalPanel';

export const OpSecSettingsPage: React.FC = () => {
  const { projectSlug = 'default' } = useParams({ strict: false }) as any;
  const { data: settings, isLoading: isSettingsLoading } = useOpSecSettings(projectSlug);
  const updateSettings = useUpdateOpSecSettings(projectSlug);
  
  const [formData, setFormData] = useState<OpSecSettings | null>(null);
  const [activePreset, setActivePreset] = useState<string | null>(localStorage.getItem('rengine-opsec-preset'));

  useEffect(() => {
    if (settings) {
      setFormData(settings);
    }
  }, [settings]);

  const handleToggle = (field: keyof OpSecSettings) => {
    if (!formData) return;
    setFormData({ ...formData, [field]: !formData[field] });
    setActivePreset(null);
  };

  const handleChange = (field: keyof OpSecSettings, value: any) => {
    if (!formData) return;
    setFormData({ ...formData, [field]: value });
    setActivePreset(null);
  };

  const applyPreset = (preset: 'quiet' | 'balanced' | 'aggressive') => {
    if (!formData) return;
    let newSettings = { ...formData };
    
    if (preset === 'quiet') {
      newSettings = {
        ...newSettings,
        enable_random_ua: true,
        enable_waf_bypass: true,
        enable_ja3_randomization: true,
        enable_rate_limit: true,
        max_rps: 2,
        enable_delay: true,
        delay_ms: 5000,
        enable_jitter: true,
        jitter_percent: 50,
        http_protocol: 'http2'
      };
    } else if (preset === 'balanced') {
      newSettings = {
        ...newSettings,
        enable_random_ua: true,
        enable_waf_bypass: true,
        enable_ja3_randomization: false,
        enable_rate_limit: true,
        max_rps: 10,
        enable_delay: true,
        delay_ms: 100,
        enable_jitter: true,
        jitter_percent: 10,
        http_protocol: 'http2'
      };
    } else if (preset === 'aggressive') {
      newSettings = {
        ...newSettings,
        enable_random_ua: true,
        enable_waf_bypass: true,
        enable_ja3_randomization: false,
        enable_rate_limit: false,
        enable_delay: false,
        enable_jitter: false,
        http_protocol: 'http1.1'
      };
    }
    
    setFormData(newSettings);
    setActivePreset(preset);
    localStorage.setItem('rengine-opsec-preset', preset);
  };

  const handleSave = () => {
    if (formData) {
      updateSettings.mutate(formData);
    }
  };

  if (isSettingsLoading || !formData) return <LinearProgress sx={{ bgcolor: 'rgba(0, 243, 255, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff' } }} />;

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
            OPSEC SETTINGS
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', letterSpacing: 1 }}>
            STEALTH & OPERATIONAL SECURITY CONFIGURATION
          </Typography>
        </Box>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', fontFamily: 'Orbitron' }}>
          SETTINGS {'>'} <span style={{ color: '#00f3ff' }}>OPSEC</span>
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
          Configure stealth parameters to bypass WAFs, avoid rate limits, and minimize detection.
          These settings are applied globally when "OpSec Mode" is enabled in your scan engine.
        </Alert>

        <TacticalPanel title="GLOBAL CONTROL" icon={<Lock size={20} />}>
          <Box sx={{ p: 1 }}>
            <FormControlLabel
              control={
                <Switch 
                  checked={formData.enable_opsec} 
                  onChange={() => handleToggle('enable_opsec')}
                  sx={{
                    '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                    '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' }
                  }}
                />
              }
              label={
                <Typography sx={{ color: '#fff', fontFamily: 'Orbitron', fontSize: '0.9rem', fontWeight: 700 }}>
                  ENABLE GLOBAL OPSEC MODE
                </Typography>
              }
            />
            <Typography variant="caption" display="block" sx={{ color: 'rgba(255,255,255,0.4)', mt: 1 }}>
              Master switch to enable/disable stealth features for all compatible tools.
            </Typography>
          </Box>
        </TacticalPanel>

        <Box>
          <Typography variant="h6" sx={{ color: '#fff', fontFamily: 'Orbitron', mb: 2, fontSize: '0.8rem', letterSpacing: 1 }}>
            STEALTH PRESETS
          </Typography>
          <Grid container spacing={2}>
            {[
              { id: 'quiet', title: 'QUIET', icon: Wind, color: '#00f3ff', desc: 'Maximum stealth. Very slow. Random jitter (50%), long delays (5s), HTTP/2 only.' },
              { id: 'balanced', title: 'BALANCED', icon: Activity, color: '#4caf50', desc: 'Optimized for reliability. 100ms delay, 10% jitter, random UA, WAF bypass.' },
              { id: 'aggressive', title: 'AGGRESSIVE', icon: Zap, color: '#f44336', desc: 'Low stealth. Fast scans. Only random UA and basic WAF bypass enabled.' }
            ].map((preset) => (
              <Grid item xs={12} md={4} key={preset.id}>
                <Card 
                  onClick={() => applyPreset(preset.id as any)}
                  sx={{ 
                    cursor: 'pointer',
                    bgcolor: activePreset === preset.id ? `rgba(${preset.id === 'quiet' ? '0, 243, 255' : preset.id === 'balanced' ? '76, 175, 80' : '244, 67, 54'}, 0.1)` : 'rgba(255,255,255,0.02)',
                    border: `1px solid ${activePreset === preset.id ? preset.color : 'rgba(255,255,255,0.1)'}`,
                    transition: 'all 0.3s',
                    '&:hover': { transform: 'translateY(-4px)', borderColor: preset.color }
                  }}
                >
                  <CardContent sx={{ textAlign: 'center' }}>
                    <preset.icon size={32} color={preset.color} style={{ marginBottom: '12px' }} />
                    <Typography sx={{ color: preset.color, fontFamily: 'Orbitron', fontWeight: 800, mb: 1 }}>
                      {preset.title}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', lineHeight: 1.4, display: 'block' }}>
                      {preset.desc}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TacticalPanel title="IDENTITY & TRAFFIC" icon={<User size={20} />}>
              <Stack spacing={2} sx={{ p: 1 }}>
                <FormControlLabel
                  control={<Switch checked={formData.enable_random_ua} onChange={() => handleToggle('enable_random_ua')} size="small" />}
                  label={<Typography variant="body2" sx={{ color: '#fff' }}>Random User-Agents</Typography>}
                />
                <FormControlLabel
                  control={<Switch checked={formData.enable_waf_bypass} onChange={() => handleToggle('enable_waf_bypass')} size="small" />}
                  label={<Typography variant="body2" sx={{ color: '#fff' }}>Inject WAF Bypass Headers</Typography>}
                />
                <FormControlLabel
                  control={<Switch checked={formData.enable_ja3_randomization} onChange={() => handleToggle('enable_ja3_randomization')} size="small" />}
                  label={<Typography variant="body2" sx={{ color: '#fff' }}>JA3 Fingerprint Randomization</Typography>}
                />
              </Stack>
            </TacticalPanel>
          </Grid>

          <Grid item xs={12} md={6}>
            <TacticalPanel title="TIMING & RATE LIMITING" icon={<Clock size={20} />}>
              <Stack spacing={3} sx={{ p: 1 }}>
                <Box>
                  <FormControlLabel
                    control={<Switch checked={formData.enable_rate_limit} onChange={() => handleToggle('enable_rate_limit')} size="small" />}
                    label={<Typography variant="body2" sx={{ color: '#fff' }}>Enable Max RPS</Typography>}
                  />
                  <TextField 
                    fullWidth 
                    size="small" 
                    type="number"
                    value={formData.max_rps}
                    onChange={(e) => handleChange('max_rps', parseInt(e.target.value))}
                    disabled={!formData.enable_rate_limit}
                    placeholder="10"
                    sx={inputStyle}
                    InputProps={{ endAdornment: <InputAdornment position="end" sx={{ '& .MuiTypography-root': { color: 'rgba(255,255,255,0.3)' } }}>RPS</InputAdornment> }}
                  />
                </Box>
                <Box>
                  <FormControlLabel
                    control={<Switch checked={formData.enable_delay} onChange={() => handleToggle('enable_delay')} size="small" />}
                    label={<Typography variant="body2" sx={{ color: '#fff' }}>Enable Delay</Typography>}
                  />
                  <TextField 
                    fullWidth 
                    size="small" 
                    type="number"
                    value={formData.delay_ms}
                    onChange={(e) => handleChange('delay_ms', parseInt(e.target.value))}
                    disabled={!formData.enable_delay}
                    placeholder="0"
                    sx={inputStyle}
                    InputProps={{ endAdornment: <InputAdornment position="end" sx={{ '& .MuiTypography-root': { color: 'rgba(255,255,255,0.3)' } }}>ms</InputAdornment> }}
                  />
                </Box>
                <Box>
                  <FormControlLabel
                    control={<Switch checked={formData.enable_jitter} onChange={() => handleToggle('enable_jitter')} size="small" />}
                    label={<Typography variant="body2" sx={{ color: '#fff' }}>Enable Jitter</Typography>}
                  />
                  <TextField 
                    fullWidth 
                    size="small" 
                    type="number"
                    value={formData.jitter_percent}
                    onChange={(e) => handleChange('jitter_percent', parseInt(e.target.value))}
                    disabled={!formData.enable_jitter}
                    placeholder="0"
                    sx={inputStyle}
                    InputProps={{ endAdornment: <InputAdornment position="end" sx={{ '& .MuiTypography-root': { color: 'rgba(255,255,255,0.3)' } }}>%</InputAdornment> }}
                  />
                </Box>
              </Stack>
            </TacticalPanel>
          </Grid>

          <Grid item xs={12} md={6}>
            <TacticalPanel title="NETWORK" icon={<Globe size={20} />}>
              <Stack spacing={3} sx={{ p: 1 }}>
                <FormControl fullWidth size="small">
                  <InputLabel sx={{ color: 'rgba(255,255,255,0.5)' }}>Preferred HTTP Protocol</InputLabel>
                  <Select
                    value={formData.http_protocol}
                    onChange={(e) => handleChange('http_protocol', e.target.value)}
                    label="Preferred HTTP Protocol"
                    sx={{
                      color: '#fff',
                      bgcolor: 'rgba(255,255,255,0.02)',
                      '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1)' },
                      '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(0, 243, 255, 0.3)' },
                      '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#00f3ff' },
                      '& .MuiSvgIcon-root': { color: '#00f3ff' }
                    }}
                  >
                    <MenuItem value="http1.1">HTTP/1.1</MenuItem>
                    <MenuItem value="http2">HTTP/2</MenuItem>
                  </Select>
                </FormControl>
                <Box>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', mb: 1, display: 'block' }}>Custom DNS Servers (per line)</Typography>
                  <TextField 
                    multiline 
                    rows={4} 
                    fullWidth 
                    value={formData.custom_dns_servers}
                    onChange={(e) => handleChange('custom_dns_servers', e.target.value)}
                    placeholder="8.8.8.8\n1.1.1.1" 
                    sx={inputStyle} 
                  />
                </Box>
              </Stack>
            </TacticalPanel>
          </Grid>

          <Grid item xs={12} md={6}>
            <TacticalPanel title="POST-PROCESSING" icon={<Monitor size={20} />}>
              <Stack spacing={2} sx={{ p: 1 }}>
                <FormControlLabel
                  control={<Switch checked={formData.enable_metadata_stripping} onChange={() => handleToggle('enable_metadata_stripping')} size="small" />}
                  label={<Typography variant="body2" sx={{ color: '#fff' }}>Automatic Metadata Stripping</Typography>}
                />
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', lineHeight: 1.4 }}>
                  Cleans EXIF, GPS, and author metadata from discovered files (PDF, JPG, PNG, etc.) to prevent data leakage.
                </Typography>
              </Stack>
            </TacticalPanel>
          </Grid>
        </Grid>

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
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
              px: 4,
              py: 1.5,
              '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)', boxShadow: '0 0 20px rgba(0, 243, 255, 0.4)' }
            }}
          >
            {updateSettings.isPending ? 'SAVING...' : 'SAVE OPSEC CONFIGURATION'}
          </Button>
        </Box>
      </Stack>
    </Box>
  );
};

const inputStyle = {
  '& .MuiOutlinedInput-root': {
    color: '#fff',
    bgcolor: 'rgba(255,255,255,0.02)',
    '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
    '&:hover fieldset': { borderColor: 'rgba(0, 243, 255, 0.3)' },
    '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
  },
  '& .Mui-disabled': {
    opacity: 0.5,
    bgcolor: 'rgba(0,0,0,0.2)'
  }
};
