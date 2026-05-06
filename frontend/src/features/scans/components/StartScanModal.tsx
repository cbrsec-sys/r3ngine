import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  IconButton,
  MenuItem,
  CircularProgress,
  Alert,
  TextField,
  FormControlLabel,
  Switch,
  Divider,
  Grid
} from '@mui/material';
import { X, Play, Zap, Shield, Search, Terminal, Globe } from 'lucide-react';
import { useEngines } from '../../engines/api';
import { useInitiateScan } from '../api';
import { useNavigate } from '@tanstack/react-router';
import { generateDorks } from '../utils/dorkUtils';

interface StartScanModalProps {
  open: boolean;
  onClose: () => void;
  domainIds: number[];
  domainNames: string[];
  projectSlug: string;
}

export const StartScanModal: React.FC<StartScanModalProps> = ({
  open,
  onClose,
  domainIds,
  domainNames,
  projectSlug
}) => {
  const [formData, setFormData] = useState({
    engine_id: '' as number | '',
    customDorkSwitch: false,
    customDorkTextarea: '',
    spiderfoot_scan: false,
    importSubdomainTextArea: '',
    outOfScopeSubdomainTextarea: '',
  });

  const { data: engines, isLoading: loadingEngines } = useEngines();
  const { mutate: initiateScan, isPending, error, reset } = useInitiateScan(projectSlug);
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.engine_id || domainIds.length === 0) return;

    initiateScan({
      domain_id: domainIds.length === 1 ? domainIds[0] : domainIds as any,
      engine_id: formData.engine_id as number,
      customDorkSwitch: formData.customDorkSwitch,
      customDorkTextarea: formData.customDorkTextarea,
      spiderfoot_scan: formData.spiderfoot_scan,
      importSubdomainTextArea: formData.importSubdomainTextArea.split('\n').filter(s => s.trim()),
      outOfScopeSubdomainTextarea: formData.outOfScopeSubdomainTextarea.split('\n').filter(s => s.trim()),
    }, {
      onSuccess: () => {
        onClose();
        reset();
        navigate({ to: `/${projectSlug}/scans` });
      },
    });
  };

  const handleClose = () => {
    onClose();
    reset();
  };

  const targetLabel = domainNames.length > 1
    ? `${domainNames.length} SELECTED TARGETS`
    : domainNames[0]?.toUpperCase() || 'N/A';

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            bgcolor: 'rgba(10, 10, 20, 0.95)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(0, 255, 98, 0.2)',
            borderRadius: 4,
            backgroundImage: 'radial-gradient(circle at top right, rgba(0, 255, 98, 0.05), transparent)',
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
            bgcolor: 'rgba(0, 255, 98, 0.1)',
            color: '#00ff62',
            display: 'flex'
          }}>
            <Zap size={20} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{
              fontFamily: 'Orbitron',
              fontWeight: 800,
              letterSpacing: 1,
              color: '#fff',
              lineHeight: 1.2
            }}>
              LAUNCH RECONNAISSANCE
            </Typography>
            <Typography variant="caption" sx={{ color: '#00ff62', fontWeight: 700, letterSpacing: 1 }}>
              TARGET: {targetLabel}
            </Typography>
          </Box>
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

          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }} >
              <Typography variant="overline" sx={{ color: 'rgba(255,255,255,0.4)', fontWeight: 800, mb: 1, display: 'block' }}>
                PRIMARY CONFIGURATION
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <TextField
                  label="Scan Engine"
                  select
                  fullWidth
                  required
                  value={formData.engine_id}
                  onChange={(e) => setFormData({ ...formData, engine_id: Number(e.target.value) })}
                  sx={fieldStyles}
                  slotProps={{
                    input: {
                      startAdornment: <Shield size={18} style={{ marginRight: 12, color: '#00ff62' }} />
                    }
                  }}
                >
                  {engines?.map((engine) => (
                    <MenuItem key={engine.id} value={engine.id}>
                      {engine.engine_name}
                    </MenuItem>
                  ))}
                </TextField>

                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.spiderfoot_scan}
                      onChange={(e) => setFormData({ ...formData, spiderfoot_scan: e.target.checked })}
                      sx={switchStyles}
                    />
                  }
                  label={
                    <Typography sx={{ color: '#fff', fontSize: '0.85rem', fontWeight: 600 }}>
                      Enable SpiderFoot OSINT
                    </Typography>
                  }
                />

                <Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />

                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.customDorkSwitch}
                      onChange={(e) => setFormData({ ...formData, customDorkSwitch: e.target.checked })}
                      sx={switchStyles}
                    />
                  }
                  label={
                    <Typography sx={{ color: '#fff', fontSize: '0.85rem', fontWeight: 600 }}>
                      Custom Github Dorks
                    </Typography>
                  }
                />

                {formData.customDorkSwitch && (
                  <>
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
                      <Button
                        size="small"
                        onClick={() => setFormData({ 
                          ...formData, 
                          customDorkTextarea: generateDorks(domainNames) 
                        })}
                        startIcon={<Terminal size={14} />}
                        sx={{
                          color: '#00ff62',
                          fontFamily: 'Orbitron',
                          fontSize: '0.65rem',
                          fontWeight: 800,
                          border: '1px solid rgba(0, 255, 98, 0.2)',
                          '&:hover': {
                            bgcolor: 'rgba(0, 255, 98, 0.05)',
                            border: '1px solid #00ff62',
                          }
                        }}
                      >
                        AUTOGENERATE DORKS
                      </Button>
                    </Box>
                    <TextField
                      label="Github Dorks"
                      fullWidth
                      multiline
                      rows={4}
                      value={formData.customDorkTextarea}
                      onChange={(e) => setFormData({ ...formData, customDorkTextarea: e.target.value })}
                      placeholder="Enter custom dorks, one per line..."
                      sx={fieldStyles}
                    />
                  </>
                )}

              </Box>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }} >
              <Typography variant="overline" sx={{ color: 'rgba(255,255,255,0.4)', fontWeight: 800, mb: 1, display: 'block' }}>
                ADVANCED SCOPE
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <TextField
                  label="Import Subdomains"
                  fullWidth
                  multiline
                  rows={4}
                  value={formData.importSubdomainTextArea}
                  onChange={(e) => setFormData({ ...formData, importSubdomainTextArea: e.target.value })}
                  placeholder="Paste subdomains to include..."
                  sx={fieldStyles}
                  helperText="One subdomain per line"
                />

                <TextField
                  label="Out of Scope Subdomains"
                  fullWidth
                  multiline
                  rows={4}
                  value={formData.outOfScopeSubdomainTextarea}
                  onChange={(e) => setFormData({ ...formData, outOfScopeSubdomainTextarea: e.target.value })}
                  placeholder="Paste subdomains to exclude..."
                  sx={fieldStyles}
                  helperText="One subdomain per line"
                />
              </Box>
            </Grid>
          </Grid>
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
            CANCEL
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={isPending || !formData.engine_id || domainIds.length === 0}
            sx={{
              bgcolor: '#00ff62',
              color: '#000',
              fontWeight: 900,
              fontFamily: 'Orbitron',
              letterSpacing: 1,
              px: 4,
              '&:hover': {
                bgcolor: '#00cc4f',
                boxShadow: '0 0 20px rgba(0, 255, 98, 0.4)'
              },
              '&.Mui-disabled': {
                bgcolor: 'rgba(0, 255, 98, 0.2)',
                color: 'rgba(0, 0, 0, 0.5)'
              }
            }}
          >
            {isPending ? <CircularProgress size={20} sx={{ color: '#000' }} /> : 'START MISSION'}
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
    '&:hover fieldset': { borderColor: 'rgba(0, 255, 98, 0.3)' },
    '&.Mui-focused fieldset': { borderColor: '#00ff62' },
    bgcolor: 'rgba(255,255,255,0.03)',
  },
  '& .MuiInputLabel-root': {
    color: 'rgba(255,255,255,0.4)',
    '&.Mui-focused': { color: '#00ff62' }
  },
  '& .MuiSelect-icon': { color: 'rgba(255,255,255,0.4)' },
  '& .MuiFormHelperText-root': { color: 'rgba(255,255,255,0.3)' }
};

const switchStyles = {
  '& .MuiSwitch-switchBase.Mui-checked': {
    color: '#00ff62',
    '& + .MuiSwitch-track': {
      backgroundColor: '#00ff62',
    },
  },
};
