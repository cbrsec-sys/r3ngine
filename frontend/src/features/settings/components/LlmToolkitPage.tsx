import React, { useState, useEffect, useRef } from 'react';
import { 
  Box, 
  Typography, 
  Grid, 
  Button, 
  Stack, 
  TextField, 
  Switch, 
  FormControlLabel, 
  MenuItem, 
  CircularProgress,
  Alert,
  IconButton,
  InputAdornment,
  Divider,
  Paper,
  Tooltip
} from '@mui/material';
import { 
  Cpu, 
  Settings, 
  Save, 
  Download, 
  Eye, 
  EyeOff, 
  Info, 
  Terminal as TerminalIcon,
  CheckCircle2,
  AlertCircle,
  Brain,
  Zap,
  Globe,
  Ghost,
  Shield,
  ChevronRight,
  Database
} from 'lucide-react';
import { useParams } from '@tanstack/react-router';
import { 
  useLlmToolkit, 
  useLlmModels, 
  useUpdateLlmSettings, 
  useOllamaPullStatus,
} from '../api';
import type { LLMConfig, LLMModel } from '../api';

import { TacticalPanel } from '../../../components/TacticalPanel';

export const LlmToolkitPage: React.FC = () => {
  const { projectSlug = 'default' } = useParams({ strict: false }) as any;
  const { data: toolkit, isLoading: isToolkitLoading } = useLlmToolkit(projectSlug);
  const updateSettings = useUpdateLlmSettings(projectSlug);
  
  const [selectedProvider, setSelectedProvider] = useState<string>('ollama');
  const [showKey, setShowKey] = useState(false);
  const [form, setForm] = useState({
    api_key: '',
    selected_model: '',
    is_active: false
  });
  const [pullingModel, setPullingModel] = useState<string | null>(null);
  
  const { data: models, isLoading: isModelsLoading } = useLlmModels(
    projectSlug, 
    selectedProvider, 
    form.api_key
  );
  
  const { data: pullStatus } = useOllamaPullStatus(projectSlug, pullingModel);
  const terminalRef = useRef<HTMLDivElement>(null);

  // Initialize form when toolkit data is loaded or provider changes
  useEffect(() => {
    if (toolkit?.llm_configs) {
      const config = toolkit.llm_configs.find(c => c.provider === selectedProvider);
      if (config) {
        setForm({
          api_key: config.api_key || '',
          selected_model: config.selected_model || '',
          is_active: config.is_active
        });
      } else {
        setForm({
          api_key: selectedProvider === 'ollama' ? 'http://ollama:11434' : '',
          selected_model: '',
          is_active: false
        });
      }
    }
  }, [toolkit, selectedProvider]);

  // Set default provider on first load
  useEffect(() => {
    if (toolkit?.active_provider) {
      setSelectedProvider(toolkit.active_provider);
    }
  }, [toolkit?.active_provider]);

  // Scroll terminal to bottom
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [pullStatus?.log]);

  // Handle pull completion
  useEffect(() => {
    if (pullStatus?.status === 'success' || pullStatus?.status === 'failed') {
      setTimeout(() => setPullingModel(null), 5000);
    }
  }, [pullStatus?.status]);

  const handleProviderChange = (provider: string) => {
    setSelectedProvider(provider);
    setShowKey(false);
  };

  const handleSave = (action: 'save' | 'pull') => {
    updateSettings.mutate({
      provider: selectedProvider,
      api_key: form.api_key,
      selected_model: form.selected_model,
      is_active: form.is_active,
      action
    }, {
      onSuccess: (data) => {
        if (data.status === 'pulling') {
          setPullingModel(form.selected_model);
        }
      }
    });
  };

  const currentModel = models?.find(m => m.name === form.selected_model);
  const providers = [
    { id: 'ollama', name: 'Ollama (Local)', icon: <Database size={18} /> },
    { id: 'openai', name: 'OpenAI', icon: <Zap size={18} /> },
    { id: 'anthropic', name: 'Anthropic', icon: <Shield size={18} /> },
    { id: 'gemini', name: 'Google Gemini', icon: <Globe size={18} /> },
  ];

  if (isToolkitLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 10 }}>
        <CircularProgress sx={{ color: '#00f3ff' }} />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ 
          fontFamily: 'Orbitron', 
          fontWeight: 900, 
          color: '#fff', 
          textShadow: '0 0 20px rgba(0, 243, 255, 0.5)',
          mb: 1 
        }}>
          AI_HUB
        </Typography>
        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', letterSpacing: 1 }}>
          CENTRALIZED LLM ORCHESTRATION & CONFIGURATION
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Provider Sidebar */}
        <Grid size={{xs: 12, lg: 3}} >
          <TacticalPanel title="LLM_PROVIDERS" icon={<Brain size={18} />}>
            <Stack spacing={1}>
              {providers.map((p) => (
                <Button
                  key={p.id}
                  variant={selectedProvider === p.id ? 'contained' : 'text'}
                  startIcon={p.icon}
                  onClick={() => handleProviderChange(p.id)}
                  sx={{
                    justifyContent: 'flex-start',
                    fontFamily: 'Orbitron',
                    fontSize: '0.75rem',
                    py: 1.5,
                    px: 2,
                    borderRadius: '12px',
                    bgcolor: selectedProvider === p.id ? 'rgba(0, 243, 255, 0.15)' : 'transparent',
                    color: selectedProvider === p.id ? '#00f3ff' : 'rgba(255,255,255,0.6)',
                    border: selectedProvider === p.id ? '1px solid rgba(0, 243, 255, 0.3)' : '1px solid transparent',
                    '&:hover': {
                      bgcolor: 'rgba(0, 243, 255, 0.05)',
                      color: '#00f3ff'
                    }
                  }}
                >
                  {p.name}
                  {toolkit?.llm_configs.find(c => c.provider === p.id)?.is_active && (
                    <Box sx={{ ml: 'auto', display: 'flex' }}>
                      <CheckCircle2 size={14} color="#00f3ff" />
                    </Box>
                  )}
                </Button>
              ))}
            </Stack>
            <Box sx={{ mt: 4, pt: 3, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', lineHeight: 1.6, display: 'block' }}>
                reNgine uses LLMs for intelligent reporting, vulnerability analysis, and attack path suggestions.
              </Typography>
            </Box>
          </TacticalPanel>
        </Grid>

        {/* Main Config Area */}
        <Grid size={{xs: 12, lg: selectedProvider === 'ollama' ? 6 : 9}} >
          <TacticalPanel 
            title={`${selectedProvider.toUpperCase()}_CONFIGURATION`}
            icon={<Settings size={18} />}
            headerAction={
              <Box sx={{ 
                px: 1.5, 
                py: 0.5, 
                borderRadius: '20px', 
                bgcolor: form.is_active ? 'rgba(0, 243, 255, 0.1)' : 'rgba(255,255,255,0.05)',
                border: `1px solid ${form.is_active ? 'rgba(0, 243, 255, 0.3)' : 'rgba(255,255,255,0.1)'}`
              }}>
                <Typography sx={{ 
                  fontSize: '10px', 
                  fontFamily: 'Orbitron', 
                  color: form.is_active ? '#00f3ff' : 'rgba(255,255,255,0.4)',
                  fontWeight: 700
                }}>
                  {form.is_active ? 'ACTIVE_DEFAULT' : 'INACTIVE'}
                </Typography>
              </Box>
            }
          >
            <Stack spacing={4}>
              {/* API Key / Host URL */}
              <Box>
                <Typography sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.75rem', mb: 1, fontFamily: 'Orbitron' }}>
                  {selectedProvider === 'ollama' ? 'HOST_URL' : 'API_KEY'}
                </Typography>
                <TextField
                  fullWidth
                  type={showKey ? 'text' : 'password'}
                  value={form.api_key}
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                  placeholder={selectedProvider === 'ollama' ? 'http://ollama:11434' : 'sk-...'}
                  slotProps={{
                    input: {
                      startAdornment: (
                        <InputAdornment position="start">
                          <Box sx={{ color: 'rgba(0, 243, 255, 0.5)' }}>
                            {selectedProvider === 'ollama' ? <Globe size={18} /> : <Eye size={18} />}
                          </Box>
                        </InputAdornment>
                      ),
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton onClick={() => setShowKey(!showKey)} edge="end" sx={{ color: 'rgba(255,255,255,0.3)' }}>
                            {showKey ? <EyeOff size={18} /> : <Eye size={18} />}
                          </IconButton>
                        </InputAdornment>
                      )
                    }
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
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', mt: 1, display: 'block' }}>
                  {selectedProvider === 'ollama' 
                    ? 'Internal URL for Ollama service. Default is http://ollama:11434' 
                    : `Enter your ${selectedProvider} API key to fetch available models.`}
                </Typography>
              </Box>

              {/* Model Selection */}
              <Box>
                <Typography sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.75rem', mb: 1, fontFamily: 'Orbitron' }}>
                  SELECT_MODEL
                </Typography>
                <TextField
                  select
                  fullWidth
                  value={form.selected_model}
                  onChange={(e) => setForm({ ...form, selected_model: e.target.value })}
                  disabled={isModelsLoading}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      color: '#fff',
                      bgcolor: 'rgba(255,255,255,0.02)',
                      '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                      '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
                    },
                    '& .MuiSelect-icon': { color: 'rgba(255,255,255,0.4)' }
                  }}
                >
                  {isModelsLoading ? (
                    <MenuItem disabled value="">
                      <CircularProgress size={20} sx={{ mr: 2 }} /> Loading models...
                    </MenuItem>
                  ) : models && models.length > 0 ? (
                    models.map((m) => (
                      <MenuItem key={m.name} value={m.name} sx={{ 
                        fontFamily: 'monospace',
                        color: '#fff',
                        bgcolor: '#0a0a0f',
                        '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.1)' },
                        '&.Mui-selected': { bgcolor: 'rgba(0, 243, 255, 0.2)' }
                      }}>
                        {m.name} {m.is_local && '(Local)'}
                      </MenuItem>
                    ))
                  ) : (
                    <MenuItem disabled value="">
                      No models found. Check your {selectedProvider === 'ollama' ? 'host' : 'API key'}.
                    </MenuItem>
                  )}
                </TextField>
              </Box>

              {/* Default Toggle */}
              <FormControlLabel
                control={
                  <Switch 
                    checked={form.is_active} 
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                    sx={{
                      '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                      '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' }
                    }}
                  />
                }
                label={
                  <Typography sx={{ color: '#fff', fontSize: '0.85rem', fontFamily: 'Orbitron' }}>
                    SET_AS_DEFAULT_LLM
                  </Typography>
                }
              />

              {/* Actions */}
              <Box sx={{ display: 'flex', gap: 2, pt: 2 }}>
                <Button
                  variant="contained"
                  startIcon={<Save size={20} />}
                  onClick={() => handleSave('save')}
                  disabled={updateSettings.isPending}
                  sx={{
                    bgcolor: 'rgba(0, 243, 255, 0.1)',
                    color: '#00f3ff',
                    border: '1px solid rgba(0, 243, 255, 0.3)',
                    fontFamily: 'Orbitron',
                    fontWeight: 800,
                    px: 4,
                    '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)' }
                  }}
                >
                  {updateSettings.isPending ? 'SAVING...' : 'SAVE CONFIG'}
                </Button>

                {selectedProvider === 'ollama' && currentModel && !currentModel.is_local && (
                  <Button
                    variant="outlined"
                    startIcon={<Download size={20} />}
                    onClick={() => handleSave('pull')}
                    disabled={updateSettings.isPending || !!pullingModel}
                    sx={{
                      borderColor: 'rgba(255, 214, 0, 0.3)',
                      color: '#ffd600',
                      fontFamily: 'Orbitron',
                      fontWeight: 800,
                      px: 4,
                      '&:hover': { borderColor: '#ffd600', bgcolor: 'rgba(255, 214, 0, 0.05)' }
                    }}
                  >
                    DOWNLOAD MODEL
                  </Button>
                )}
              </Box>

              {/* Terminal */}
              {(pullingModel || pullStatus) && (
                <Box sx={{ mt: 4 }}>
                  <Paper sx={{ 
                    bgcolor: '#0a0a0a', 
                    borderRadius: '12px', 
                    border: '1px solid rgba(255,255,255,0.1)',
                    overflow: 'hidden'
                  }}>
                    <Box sx={{ 
                      px: 2, 
                      py: 1, 
                      bgcolor: '#1a1a1a', 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center' 
                    }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <TerminalIcon size={14} color="#00f3ff" />
                        <Typography sx={{ color: '#fff', fontSize: '10px', fontFamily: 'monospace' }}>
                          OLLAMA_PULL: {pullingModel}
                        </Typography>
                      </Box>
                      <Typography sx={{ 
                        fontSize: '10px', 
                        fontFamily: 'Orbitron', 
                        color: pullStatus?.status === 'success' ? '#00f3ff' : pullStatus?.status === 'failed' ? '#ff3131' : '#ffd600'
                      }}>
                        {pullStatus?.status.toUpperCase() || 'INITIATING'}
                      </Typography>
                    </Box>
                    <Box 
                      ref={terminalRef}
                      sx={{ 
                        p: 2, 
                        height: '200px', 
                        overflowY: 'auto', 
                        fontFamily: 'monospace', 
                        fontSize: '12px', 
                        color: '#10b981',
                        whiteSpace: 'pre-wrap',
                        '&::-webkit-scrollbar': { width: '4px' },
                        '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(0, 243, 255, 0.2)' }
                      }}
                    >
                      {pullStatus?.log || 'Preparing environment...'}
                    </Box>
                  </Paper>
                </Box>
              )}
            </Stack>
          </TacticalPanel>
        </Grid>

        {/* Model Info Sidebar (Ollama only) */}
        {selectedProvider === 'ollama' && (
          <Grid size={{xs: 12, lg: 3}} >
            <TacticalPanel title="MODEL_INSIGHTS" icon={<Info size={18} />}>
              {!currentModel ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Ghost size={40} color="rgba(255,255,255,0.1)" />
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.3)', mt: 2 }}>
                    Select a model to view technical specifications.
                  </Typography>
                </Box>
              ) : (
                <Stack spacing={3}>
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', lineHeight: 1.6 }}>
                    {currentModel.description || 'No detailed description available for this model variant.'}
                  </Typography>
                  
                  <Box>
                    <Typography sx={{ color: 'rgba(0, 243, 255, 0.5)', fontSize: '10px', fontFamily: 'Orbitron', mb: 0.5 }}>EXPERTISE</Typography>
                    <Typography sx={{ color: '#fff', fontSize: '0.9rem', fontWeight: 600 }}>{currentModel.expertise || 'General Purpose'}</Typography>
                  </Box>

                  <Box>
                    <Typography sx={{ color: 'rgba(0, 243, 255, 0.5)', fontSize: '10px', fontFamily: 'Orbitron', mb: 0.5 }}>DISK_FOOTPRINT</Typography>
                    <Typography sx={{ color: '#fff', fontSize: '0.9rem', fontWeight: 600 }}>{currentModel.size || 'N/A'}</Typography>
                  </Box>

                  <Box>
                    <Typography sx={{ color: 'rgba(0, 243, 255, 0.5)', fontSize: '10px', fontFamily: 'Orbitron', mb: 0.5 }}>SUGGESTED_RAM</Typography>
                    <Typography sx={{ color: '#fff', fontSize: '0.9rem', fontWeight: 600 }}>{currentModel.suggested_ram || 'N/A'}</Typography>
                  </Box>

                  <Alert 
                    severity="warning" 
                    icon={<AlertCircle size={20} />}
                    sx={{ 
                      bgcolor: 'rgba(255, 214, 0, 0.05)', 
                      color: '#ffd600',
                      border: '1px solid rgba(255, 214, 0, 0.2)',
                      fontSize: '11px',
                      '& .MuiAlert-icon': { color: '#ffd600' }
                    }}
                  >
                    Local models perform significantly better with GPU acceleration. CPU inference may result in high latency.
                  </Alert>
                </Stack>
              )}
            </TacticalPanel>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};
