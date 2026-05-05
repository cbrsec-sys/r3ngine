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
} from '@mui/material';
import { X, Target, Globe, Building2, Terminal } from 'lucide-react';
import { useAddTarget, useOrganizations } from '../api';

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
  });

  const { data: organizations, isLoading: loadingOrgs } = useOrganizations();
  const { mutate: addTarget, isPending, error, reset } = useAddTarget(projectSlug);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const organization_ids = formData.organization 
      ? organizations?.filter(org => org.name === formData.organization).map(org => org.id)
      : [];

    addTarget({ 
      domain_name: formData.domain_name, 
      project_slug: projectSlug,
      organization_ids: organization_ids
    }, {
      onSuccess: () => {
        onClose();
        setFormData({
          domain_name: '',
          description: '',
          organization: '',
          h1_team_handle: '',
        });
        reset();
      },
    });
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
            maxWidth: 500,
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
            INITIATE NEW TARGET
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
              label="Domain / IP / URL"
              fullWidth
              required
              value={formData.domain_name}
              onChange={(e) => setFormData({ ...formData, domain_name: e.target.value })}
              placeholder="example.com"
              sx={fieldStyles}
              slotProps={{
                input: {
                  startAdornment: <Globe size={18} style={{ marginRight: 12, color: '#00f3ff' }} />
                }
              }}
            />

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

            <TextField
              label="Description"
              fullWidth
              multiline
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Target reconnaissance notes..."
              sx={fieldStyles}
            />
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
            disabled={isPending}
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
            {isPending ? <CircularProgress size={20} sx={{ color: '#000' }} /> : 'DEPLOY TARGET'}
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
