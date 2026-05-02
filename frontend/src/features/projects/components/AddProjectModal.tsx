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
  CircularProgress,
  Alert,
} from '@mui/material';
import { X, FolderPlus } from 'lucide-react';
import { useCreateProject } from '../api';

interface AddProjectModalProps {
  open: boolean;
  onClose: () => void;
}

export const AddProjectModal: React.FC<AddProjectModalProps> = ({ open, onClose }) => {
  const [projectName, setProjectName] = useState('');
  const { mutate: createProject, isPending, error, reset } = useCreateProject();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim()) return;
    
    createProject(projectName, {
      onSuccess: () => {
        onClose();
        setProjectName('');
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
      PaperProps={{
        sx: {
          bgcolor: 'rgba(10, 10, 20, 0.95)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(0, 243, 255, 0.2)',
          borderRadius: 4,
          backgroundImage: 'radial-gradient(circle at top right, rgba(0, 243, 255, 0.05), transparent)',
          maxWidth: 450,
          width: '100%'
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
            <FolderPlus size={20} />
          </Box>
          <Typography variant="h6" sx={{ 
            fontFamily: 'Orbitron', 
            fontWeight: 800, 
            letterSpacing: 1,
            color: '#fff'
          }}>
            NEW_PROJECT_INITIALIZATION
          </Typography>
        </Box>
        <IconButton onClick={handleClose} sx={{ color: 'rgba(255,255,255,0.3)', '&:hover': { color: '#ff003c' } }}>
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <form onSubmit={handleSubmit}>
        <DialogContent sx={{ mt: 3 }}>
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
              label="PROJECT_NAME"
              fullWidth
              autoFocus
              required
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g. Cybersec_Audit_2024"
              sx={fieldStyles}
              helperText="A slug will be automatically generated from the project name."
              FormHelperTextProps={{ sx: { color: 'rgba(255,255,255,0.3)' } }}
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
            disabled={isPending || !projectName.trim()}
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
            {isPending ? <CircularProgress size={20} sx={{ color: '#000' }} /> : 'INITIALIZE_PROJECT'}
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
};
