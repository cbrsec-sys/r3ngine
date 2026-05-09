import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  IconButton,
  MenuItem,
  CircularProgress,
  Alert,
  Switch,
  FormControlLabel,
  Collapse,
  Divider,
} from '@mui/material';
import { X, Target, Globe, Building2, Terminal, Activity, Clock, Settings2, Search, Zap, ListX, Map } from 'lucide-react';
import { useAddTarget, useOrganizations, useEngines, useResolveIP } from '../api';
import { Checkbox, List, ListItem, ListItemButton, ListItemIcon, ListItemText } from '@mui/material';

interface AddTargetModalProps {
  open: boolean;
  onClose: () => void;
  projectSlug: string;
}

export const AddTargetModal: React.FC<AddTargetModalProps> = ({ open, onClose, projectSlug }) => {
  const [formData, setFormData] = useState({
    domain_name: '',
    description: '',
    organization: '',
    h1_team_handle: '',
    is_monitored: false,
    monitor_frequency: 'daily',
    monitor_engine_id: '',
    monitor_scan_scope: 'none',
    starting_point_path: '',
    excluded_paths: '',
  });

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [resolverInput, setResolverInput] = useState('');
  const [resolvedDomains, setResolvedDomains] = useState<string[]>([]);
  const [selectedDomains, setSelectedDomains] = useState<string[]>([]);
  const [isResolverOpen, setIsResolverOpen] = useState(false);

  const { data: organizations, isLoading: loadingOrgs } = useOrganizations();
  const { data: engines, isLoading: loadingEngines } = useEngines();
  const { mutate: addTarget, isPending, error, reset } = useAddTarget(projectSlug);
  const { mutate: resolveIP, isPending: isResolving } = useResolveIP();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    addTarget({ 
      domain_name: formData.domain_name, 
      project_slug: projectSlug,
      organization: formData.organization,
      h1_team_handle: formData.h1_team_handle,
      description: formData.description,
      is_monitored: formData.is_monitored,
      monitor_frequency: formData.monitor_frequency,
      monitor_engine_id: formData.monitor_engine_id ? Number(formData.monitor_engine_id) : undefined,
      monitor_scan_scope: formData.monitor_scan_scope,
      starting_point_path: formData.starting_point_path || undefined,
      excluded_paths: formData.excluded_paths ? formData.excluded_paths.split('\n').filter(p => p.trim()) : [],
    }, {
      onSuccess: () => {
        onClose();
        setFormData({
          domain_name: '',
          description: '',
          organization: '',
          h1_team_handle: '',
          is_monitored: false,
          monitor_frequency: 'daily',
          monitor_engine_id: '',
          monitor_scan_scope: 'none',
          starting_point_path: '',
          excluded_paths: '',
        });
        reset();
      },
    });
  };

  const handleResolve = () => {
    if (!resolverInput) return;
    resolveIP(resolverInput, {
      onSuccess: (data) => {
        setResolvedDomains(data.domains || []);
        setSelectedDomains(data.domains || []);
      }
    });
  };

  const toggleDomain = (domain: string) => {
    setSelectedDomains(prev => 
      prev.includes(domain) ? prev.filter(d => d !== domain) : [...prev, domain]
    );
  };

  const addSelectedToTargets = () => {
    const currentTargets = formData.domain_name.split('\n').filter(t => t.trim());
    const newTargets = [...new Set([...currentTargets, ...selectedDomains])];
    setFormData({ ...formData, domain_name: newTargets.join('\n') });
    setIsResolverOpen(false);
    setResolverInput('');
    setResolvedDomains([]);
    setSelectedDomains([]);
  };

  const handleClose = () => {
    onClose();
    reset();
  };

  return (
    <Dialog 
      open={open} 
      onClose={handleClose}
      slotProps={{
        paper: {
          sx: {
            bgcolor: 'rgba(10, 10, 20, 0.95)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(0, 243, 255, 0.2)',
            borderRadius: 4,
            backgroundImage: 'radial-gradient(circle at top right, rgba(0, 243, 255, 0.05), transparent)',
            maxWidth: 600,
            width: '100%'
          }
        }
      }}
    >
      <DialogTitle sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        pb: 2
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box sx={{ 
            p: 1, 
            borderRadius: 2, 
            bgcolor: 'rgba(0, 243, 255, 0.1)', 
            color: '#00f3ff',
            display: 'flex'
          }}>
            <Target size={20} />
          </Box>
          <Typography variant="h6" sx={{ 
            fontFamily: 'Orbitron', 
            fontWeight: 800, 
            letterSpacing: 1,
            color: '#fff'
          }}>
            INITIATE NEW TARGETS
          </Typography>
        </Box>
        <IconButton onClick={handleClose} sx={{ color: 'rgba(255,255,255,0.3)', '&:hover': { color: '#ff003c' } }}>
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <form onSubmit={handleSubmit}>
        <DialogContent sx={{ mt: 2 }}>
          {error && (
            <Alert severity="error" sx={{ 
              mb: 3, 
              bgcolor: 'rgba(255, 0, 60, 0.1)', 
              color: '#ff003c',
              border: '1px solid rgba(255, 0, 60, 0.2)',
              '& .MuiAlert-icon': { color: '#ff003c' }
            }}>
              {error.message}
            </Alert>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <TextField
              label="Domains / IPs / URLs"
              fullWidth
              required
              multiline
              rows={4}
              value={formData.domain_name}
              onChange={(e) => setFormData({ ...formData, domain_name: e.target.value })}
              placeholder="example.com&#10;192.168.1.1&#10;https://api.example.com"
              sx={fieldStyles}
              helperText="Enter multiple targets separated by newlines"
              slotProps={{
                formHelperText: { sx: { color: 'rgba(255,255,255,0.3)' } },
                input: {
                  startAdornment: <Globe size={18} style={{ marginRight: 12, marginTop: -60, color: '#00f3ff' }} />,
                  endAdornment: (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, position: 'absolute', right: 8, top: 8 }}>
                      <Button
                        size="small"
                        onClick={() => setIsResolverOpen(!isResolverOpen)}
                        startIcon={<Zap size={14} />}
                        sx={{
                          fontSize: '0.65rem',
                          bgcolor: isResolverOpen ? 'rgba(0, 243, 255, 0.2)' : 'rgba(255,255,255,0.05)',
                          color: '#00f3ff',
                          borderColor: 'rgba(0, 243, 255, 0.3)',
                          '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.3)' }
                        }}
                        variant="outlined"
                      >
                        IP RESOLVER
                      </Button>
                    </Box>
                  )
                }
              }}
            />

            <Collapse in={isResolverOpen}>
              <Box sx={{ 
                p: 2, 
                borderRadius: 2, 
                bgcolor: 'rgba(0, 243, 255, 0.05)',
                border: '1px solid rgba(0, 243, 255, 0.1)',
                mb: 2
              }}>
                <Typography variant="caption" sx={{ color: '#00f3ff', mb: 1, display: 'block', fontWeight: 600 }}>
                  IP / CIDR RESOLVER TOOL
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                  <TextField
                    size="small"
                    placeholder="Enter IP or CIDR (e.g. 1.1.1.1/24)"
                    fullWidth
                    value={resolverInput}
                    onChange={(e) => setResolverInput(e.target.value)}
                    sx={fieldStyles}
                  />
                  <Button 
                    variant="contained" 
                    size="small"
                    disabled={isResolving}
                    onClick={handleResolve}
                    sx={{ bgcolor: '#00f3ff', color: '#000', fontWeight: 900 }}
                  >
                    {isResolving ? <CircularProgress size={16} sx={{ color: '#000' }} /> : 'RESOLVE'}
                  </Button>
                </Box>
                
                {resolvedDomains.length > 0 && (
                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                        Resolved {resolvedDomains.length} domains
                      </Typography>
                      <Box>
                        <Button size="small" sx={{ fontSize: '0.6rem', color: '#00f3ff' }} onClick={() => setSelectedDomains(resolvedDomains)}>All</Button>
                        <Button size="small" sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }} onClick={() => setSelectedDomains([])}>None</Button>
                      </Box>
                    </Box>
                    <Box sx={{ maxHeight: 200, overflowY: 'auto', bgcolor: 'rgba(0,0,0,0.2)', borderRadius: 1 }}>
                      <List dense>
                        {resolvedDomains.map((domain) => (
                          <ListItem key={domain} disablePadding>
                            <ListItemButton onClick={() => toggleDomain(domain)} dense>
                              <ListItemIcon sx={{ minWidth: 32 }}>
                                <Checkbox
                                  edge="start"
                                  checked={selectedDomains.includes(domain)}
                                  tabIndex={-1}
                                  disableRipple
                                  size="small"
                                  sx={{ color: 'rgba(0, 243, 255, 0.3)', '&.Mui-checked': { color: '#00f3ff' } }}
                                />
                              </ListItemIcon>
                              <ListItemText 
                                primary={
                                  <Typography sx={{ fontSize: '0.75rem', color: '#fff' }}>
                                    {domain}
                                  </Typography>
                                } 
                              />
                            </ListItemButton>
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                    <Button 
                      fullWidth 
                      variant="outlined" 
                      size="small" 
                      onClick={addSelectedToTargets}
                      sx={{ mt: 2, color: '#00f3ff', borderColor: 'rgba(0, 243, 255, 0.4)' }}
                    >
                      ADD {selectedDomains.length} SELECTED TO TARGETS
                    </Button>
                  </Box>
                )}
              </Box>
            </Collapse>

            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              <TextField
                label="Organization (Optional)"
                select
                fullWidth
                value={formData.organization}
                onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                sx={fieldStyles}
                slotProps={{
                  input: {
                    startAdornment: <Building2 size={18} style={{ marginRight: 12, color: 'rgba(255,255,255,0.4)' }} />
                  }
                }}
              >
                <MenuItem value="">
                  <em>None</em>
                </MenuItem>
                {organizations?.map((org: any) => (
                  <MenuItem key={org.id} value={org.name}>
                    {org.name}
                  </MenuItem>
                ))}
              </TextField>

              <TextField
                label="HackerOne Team Handle"
                fullWidth
                value={formData.h1_team_handle}
                onChange={(e) => setFormData({ ...formData, h1_team_handle: e.target.value })}
                placeholder="Optional team handle"
                sx={fieldStyles}
                slotProps={{
                  input: {
                    startAdornment: <Terminal size={18} style={{ marginRight: 12, color: 'rgba(255,255,255,0.4)' }} />
                  }
                }}
              />
            </Box>

            <TextField
              label="Description"
              fullWidth
              multiline
              rows={2}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Target reconnaissance notes..."
              sx={fieldStyles}
            />

            <Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />

            <Box>
              <Button
                fullWidth
                variant="text"
                onClick={() => setShowAdvanced(!showAdvanced)}
                startIcon={<Settings2 size={16} />}
                sx={{ 
                  justifyContent: 'flex-start',
                  color: 'rgba(255,255,255,0.4)',
                  fontSize: '0.75rem',
                  fontFamily: 'Orbitron',
                  '&:hover': { color: '#00f3ff', bgcolor: 'transparent' }
                }}
              >
                {showAdvanced ? 'HIDE' : 'SHOW'} ADVANCED SCAN CONFIGURATION
              </Button>
              
              <Collapse in={showAdvanced}>
                <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField
                    label="Starting Point Path"
                    fullWidth
                    size="small"
                    value={formData.starting_point_path}
                    onChange={(e) => setFormData({ ...formData, starting_point_path: e.target.value })}
                    placeholder="/api/v1 (Optional)"
                    sx={fieldStyles}
                    slotProps={{
                      input: {
                        startAdornment: <Map size={16} style={{ marginRight: 12, color: 'rgba(255,255,255,0.4)' }} />
                      }
                    }}
                    helperText="Initial path to start scanning from"
                  />
                  <TextField
                    label="Excluded Paths"
                    fullWidth
                    multiline
                    rows={2}
                    size="small"
                    value={formData.excluded_paths}
                    onChange={(e) => setFormData({ ...formData, excluded_paths: e.target.value })}
                    placeholder="/logout&#10;/admin/delete"
                    sx={fieldStyles}
                    slotProps={{
                      input: {
                        startAdornment: <ListX size={16} style={{ marginRight: 12, marginTop: -20, color: 'rgba(255,255,255,0.4)' }} />
                      }
                    }}
                    helperText="Paths to ignore during scanning (newline separated)"
                  />
                </Box>
              </Collapse>
            </Box>

            <Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />

            <Box>
              <FormControlLabel
                control={
                  <Switch 
                    checked={formData.is_monitored}
                    onChange={(e) => setFormData({ ...formData, is_monitored: e.target.checked })}
                    sx={{
                      '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                      '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' },
                    }}
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Activity size={16} color={formData.is_monitored ? '#00f3ff' : 'rgba(255,255,255,0.4)'} />
                    <Typography sx={{ 
                      fontFamily: 'Orbitron', 
                      fontSize: '0.75rem', 
                      fontWeight: 600,
                      color: formData.is_monitored ? '#fff' : 'rgba(255,255,255,0.4)'
                    }}>
                      CONTINUOUS MONITORING
                    </Typography>
                  </Box>
                }
              />

              <Collapse in={formData.is_monitored}>
                <Box sx={{ 
                  mt: 2, 
                  p: 2, 
                  borderRadius: 2, 
                  bgcolor: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 2
                }}>
                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                    <TextField
                      label="Frequency"
                      select
                      fullWidth
                      size="small"
                      value={formData.monitor_frequency}
                      onChange={(e) => setFormData({ ...formData, monitor_frequency: e.target.value })}
                      sx={fieldStyles}
                      slotProps={{
                        input: {
                          startAdornment: <Clock size={16} style={{ marginRight: 8, color: 'rgba(255,255,255,0.4)' }} />
                        }
                      }}
                    >
                      <MenuItem value="hourly">Hourly</MenuItem>
                      <MenuItem value="daily">Daily</MenuItem>
                      <MenuItem value="weekly">Weekly</MenuItem>
                      <MenuItem value="monthly">Monthly</MenuItem>
                    </TextField>

                    <TextField
                      label="Auto Scan Scope"
                      select
                      fullWidth
                      size="small"
                      value={formData.monitor_scan_scope}
                      onChange={(e) => setFormData({ ...formData, monitor_scan_scope: e.target.value })}
                      sx={fieldStyles}
                      slotProps={{
                        input: {
                          startAdornment: <Search size={16} style={{ marginRight: 8, color: 'rgba(255,255,255,0.4)' }} />
                        }
                      }}
                    >
                      <MenuItem value="none">None (Discovery Only)</MenuItem>
                      <MenuItem value="targeted">Targeted Scan</MenuItem>
                      <MenuItem value="full">Full Scan</MenuItem>
                    </TextField>
                  </Box>

                  <TextField
                    label="Monitoring Engine"
                    select
                    fullWidth
                    size="small"
                    required={formData.is_monitored}
                    value={formData.monitor_engine_id}
                    onChange={(e) => setFormData({ ...formData, monitor_engine_id: e.target.value })}
                    sx={fieldStyles}
                    slotProps={{
                      input: {
                        startAdornment: <Settings2 size={16} style={{ marginRight: 8, color: 'rgba(255,255,255,0.4)' }} />
                      }
                    }}
                  >
                    {engines?.map((engine: any) => (
                      <MenuItem key={engine.id} value={engine.id}>
                        {engine.engine_name}
                      </MenuItem>
                    ))}
                  </TextField>
                </Box>
              </Collapse>
            </Box>
          </Box>
        </DialogContent>

        <DialogActions sx={{ p: 3, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <Button 
            onClick={handleClose} 
            sx={{ 
              color: 'rgba(255,255,255,0.5)',
              fontFamily: 'Orbitron',
              fontSize: '0.7rem',
              fontWeight: 800
            }}
          >
            ABORT
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={isPending || (formData.is_monitored && !formData.monitor_engine_id)}
            sx={{
              bgcolor: '#00f3ff',
              color: '#000',
              fontWeight: 900,
              fontFamily: 'Orbitron',
              letterSpacing: 1,
              px: 4,
              '&:hover': {
                bgcolor: '#00d1db',
                boxShadow: '0 0 20px rgba(0, 243, 255, 0.4)'
              },
              '&.Mui-disabled': {
                bgcolor: 'rgba(0, 243, 255, 0.2)',
                color: 'rgba(0, 0, 0, 0.5)'
              }
            }}
          >
            {isPending ? <CircularProgress size={20} sx={{ color: '#000' }} /> : 'DEPLOY TARGETS'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

const fieldStyles = {
  '& .MuiOutlinedInput-root': {
    color: '#fff',
    '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
    '&:hover fieldset': { borderColor: 'rgba(0, 243, 255, 0.3)' },
    '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
    bgcolor: 'rgba(255,255,255,0.03)',
  },
  '& .MuiInputLabel-root': { 
    color: 'rgba(255,255,255,0.4)',
    '&.Mui-focused': { color: '#00f3ff' }
  },
  '& .MuiSelect-icon': { color: 'rgba(255,255,255,0.4)' },
};
