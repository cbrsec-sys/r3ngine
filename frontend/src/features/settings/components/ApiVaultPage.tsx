import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Card, 
  CardContent, 
  TextField, 
  Button, 
  LinearProgress,
  Alert,
  Stack,
  Grid,
  InputAdornment,
  IconButton,
  Divider
} from '@mui/material';
import { 
  Settings, 
  Shield, 
  Save, 
  Eye, 
  EyeOff,
  ExternalLink,
  Zap,
  Globe,
  Database,
  Search,
  Lock,
  ChevronRight
} from 'lucide-react';
import { useParams } from '@tanstack/react-router';
import { useApiVault, useUpdateApiVault } from '../api';
import { TacticalPanel } from '../../../components/TacticalPanel';

export const ApiVaultPage: React.FC = () => {
  const { projectSlug = 'default' } = useParams({ strict: false }) as any;
  const { data: settings, isLoading } = useApiVault(projectSlug);
  const updateSettings = useUpdateApiVault(projectSlug);

  const [form, setForm] = useState({
    netlas_key: '',
    chaos_key: '',
    shodan_key: '',
    censys_id: '',
    censys_secret: '',
    leaklookup_key: '',
    hackerone_username: '',
    hackerone_key: ''
  });

  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (settings) {
      setForm({
        netlas_key: settings.netlas_key || '',
        chaos_key: settings.chaos_key || '',
        shodan_key: settings.shodan_key || '',
        censys_id: settings.censys_id || '',
        censys_secret: settings.censys_secret || '',
        leaklookup_key: settings.leaklookup_key || '',
        hackerone_username: settings.hackerone_username || '',
        hackerone_key: settings.hackerone_key || ''
      });
    }
  }, [settings]);

  const toggleVisibility = (field: string) => {
    setShowKeys(prev => ({ ...prev, [field]: !prev[field] }));
  };

  const handleSave = () => {
    updateSettings.mutate(form);
  };

  if (isLoading) return <LinearProgress sx={{ bgcolor: 'rgba(0, 243, 255, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff' } }} />;

  const KeyField = ({ label, description, field, placeholder, icon: Icon, url }: any) => (
    <Box sx={{ mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Icon size={18} color="#00f3ff" />
          <Typography sx={{ color: '#fff', fontFamily: 'Orbitron', fontSize: '0.85rem', fontWeight: 700 }}>
            {label}
          </Typography>
        </Box>
        {url && (
          <Button 
            href={url} 
            target="_blank" 
            size="small" 
            endIcon={<ExternalLink size={12} />}
            sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px', '&:hover': { color: '#00f3ff' } }}
          >
            GET KEY
          </Button>
        )}
      </Box>
      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', mb: 2, display: 'block' }}>
        {description}
      </Typography>
      <TextField
        fullWidth
        variant="outlined"
        type={showKeys[field] ? 'text' : 'password'}
        value={(form as any)[field]}
        onChange={(e) => setForm({ ...form, [field]: e.target.value })}
        placeholder={placeholder}
        InputProps={{
          endAdornment: (
            <InputAdornment position="end">
              <IconButton onClick={() => toggleVisibility(field)} edge="end" sx={{ color: 'rgba(255,255,255,0.3)' }}>
                {showKeys[field] ? <EyeOff size={18} /> : <Eye size={18} />}
              </IconButton>
            </InputAdornment>
          ),
        }}
        sx={{
          '& .MuiOutlinedInput-root': {
            color: '#fff',
            bgcolor: 'rgba(255,255,255,0.02)',
            fontFamily: 'monospace',
            '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
            '&:hover fieldset': { borderColor: 'rgba(0, 243, 255, 0.3)' },
            '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
          }
        }}
      />
    </Box>
  );

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
            API VAULT
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', letterSpacing: 1 }}>
            CENTRALIZED CREDENTIAL MANAGEMENT
          </Typography>
        </Box>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', fontFamily: 'Orbitron' }}>
          SETTINGS {'>'} <span style={{ color: '#00f3ff' }}>API VAULT</span>
        </Typography>
      </Box>

      <Stack spacing={3}>
        <Alert 
          severity="info" 
          icon={<Lock size={20} />}
          sx={{ 
            bgcolor: 'rgba(0, 243, 255, 0.05)', 
            color: '#00f3ff',
            border: '1px solid rgba(0, 243, 255, 0.2)',
            '& .MuiAlert-icon': { color: '#00f3ff' }
          }}
        >
          API keys are stored securely and used across various discovery and OSINT modules. 
          Unleash the full power of reNgine by connecting external data sources.
        </Alert>

        <Grid container spacing={3}>
          <Grid size={{xs: 12, md: 6}} >
            <TacticalPanel title="OSINT & DISCOVERY" icon={<Globe size={20} />}>
              <Box sx={{ p: 1 }}>
                <KeyField 
                  label="NETLAS" 
                  description="Used for WHOIS information and historical OSINT data." 
                  field="netlas_key" 
                  placeholder="Enter Netlas Key"
                  icon={Search}
                  url="https://netlas.io"
                />
                <KeyField 
                  label="CHAOS" 
                  description="Used for subdomain enumeration and recon data from Project Discovery." 
                  field="chaos_key" 
                  placeholder="Enter Chaos Key"
                  icon={Zap}
                  url="https://cloud.projectdiscovery.io"
                />
                <KeyField 
                  label="SHODAN" 
                  description="Used for origin discovery and historical IP lookups." 
                  field="shodan_key" 
                  placeholder="Enter Shodan Key"
                  icon={Database}
                  url="https://shodan.io"
                />
                <KeyField 
                  label="LEAKLOOKUP" 
                  description="Used to search for leaked credentials and data breaches." 
                  field="leaklookup_key" 
                  placeholder="Enter LeakLookup Key"
                  icon={Shield}
                  url="https://leak-lookup.com"
                />
              </Box>
            </TacticalPanel>
          </Grid>

          <Grid size={{xs: 12, md: 6}} >
            <Stack spacing={3}>
              <TacticalPanel title="CENSYS CONFIGURATION" icon={<Search size={20} />}>
                <Box sx={{ p: 1 }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', mb: 3, display: 'block' }}>
                    Censys keys are used for origin discovery and SSL serial matching.
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid size={{xs: 12}} >
                      <Typography sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '11px', mb: 1, fontFamily: 'Orbitron' }}>API ID</Typography>
                      <TextField
                        fullWidth
                        size="small"
                        value={form.censys_id}
                        onChange={(e) => setForm({ ...form, censys_id: e.target.value })}
                        placeholder="Enter Censys API ID"
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            color: '#fff',
                            bgcolor: 'rgba(255,255,255,0.02)',
                            fontFamily: 'monospace',
                            '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                          }
                        }}
                      />
                    </Grid>
                    <Grid size={{xs: 12}} >
                      <Typography sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '11px', mb: 1, fontFamily: 'Orbitron' }}>API SECRET</Typography>
                      <TextField
                        fullWidth
                        size="small"
                        type={showKeys.censys_secret ? 'text' : 'password'}
                        value={form.censys_secret}
                        onChange={(e) => setForm({ ...form, censys_secret: e.target.value })}
                        placeholder="Enter Censys Secret"
                        InputProps={{
                          endAdornment: (
                            <InputAdornment position="end">
                              <IconButton onClick={() => toggleVisibility('censys_secret')} edge="end" sx={{ color: 'rgba(255,255,255,0.3)' }}>
                                {showKeys.censys_secret ? <EyeOff size={16} /> : <Eye size={16} />}
                              </IconButton>
                            </InputAdornment>
                          ),
                        }}
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            color: '#fff',
                            bgcolor: 'rgba(255,255,255,0.02)',
                            fontFamily: 'monospace',
                            '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                          }
                        }}
                      />
                    </Grid>
                  </Grid>
                  <Button 
                    href="https://search.censys.io/account/api" 
                    target="_blank" 
                    size="small" 
                    startIcon={<ExternalLink size={12} />}
                    sx={{ mt: 2, color: '#00f3ff', fontSize: '10px' }}
                  >
                    GET CENSYS KEYS
                  </Button>
                </Box>
              </TacticalPanel>

              <TacticalPanel title="HACKERONE (BUG BOUNTY)" icon={<Zap size={20} />}>
                <Box sx={{ p: 1 }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', mb: 3, display: 'block' }}>
                    Used to import targets, bookmarked programs, and submit automated reports.
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid size={{xs: 12}} >
                      <Typography sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '11px', mb: 1, fontFamily: 'Orbitron' }}>USERNAME (NOT EMAIL)</Typography>
                      <TextField
                        fullWidth
                        size="small"
                        value={form.hackerone_username}
                        onChange={(e) => setForm({ ...form, hackerone_username: e.target.value })}
                        placeholder="Enter Hackerone Username"
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            color: '#fff',
                            bgcolor: 'rgba(255,255,255,0.02)',
                            fontFamily: 'monospace',
                            '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                          }
                        }}
                      />
                    </Grid>
                    <Grid size={{xs: 12}} >
                      <Typography sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '11px', mb: 1, fontFamily: 'Orbitron' }}>API TOKEN</Typography>
                      <TextField
                        fullWidth
                        size="small"
                        type={showKeys.hackerone_key ? 'text' : 'password'}
                        value={form.hackerone_key}
                        onChange={(e) => setForm({ ...form, hackerone_key: e.target.value })}
                        placeholder="Enter Hackerone Token"
                        InputProps={{
                          endAdornment: (
                            <InputAdornment position="end">
                              <IconButton onClick={() => toggleVisibility('hackerone_key')} edge="end" sx={{ color: 'rgba(255,255,255,0.3)' }}>
                                {showKeys.hackerone_key ? <EyeOff size={16} /> : <Eye size={16} />}
                              </IconButton>
                            </InputAdornment>
                          ),
                        }}
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            color: '#fff',
                            bgcolor: 'rgba(255,255,255,0.02)',
                            fontFamily: 'monospace',
                            '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                          }
                        }}
                      />
                    </Grid>
                  </Grid>
                  <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                    <Button 
                      href="https://hackerone.com/settings/api_token/edit" 
                      target="_blank" 
                      size="small" 
                      startIcon={<ExternalLink size={12} />}
                      sx={{ color: '#00f3ff', fontSize: '10px' }}
                    >
                      GENERATE TOKEN
                    </Button>
                  </Box>
                </Box>
              </TacticalPanel>
            </Stack>
          </Grid>
        </Grid>

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 4 }}>
          <Button
            variant="contained"
            startIcon={<Save size={20} />}
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
            {updateSettings.isPending ? 'SYNCHRONIZING...' : 'UPDATE API VAULT'}
          </Button>
        </Box>
      </Stack>
    </Box>
  );
};
