import React, { useState, useEffect } from 'react';
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
  Tooltip,
} from '@mui/material';
import { X, Cpu, BookOpen } from 'lucide-react';
import { useCreateEngine, useFullYamlConfig } from '../api';
import { EngineConfigReferenceModal } from './EngineConfigReferenceModal';

interface AddEngineModalProps {
  open: boolean;
  onClose: () => void;
}

export const AddEngineModal: React.FC<AddEngineModalProps> = ({ open, onClose }) => {
  const [name, setName] = useState('');
  const [yaml, setYaml] = useState('');
  const [refOpen, setRefOpen] = useState(false);
  const createEngine = useCreateEngine();
  const { data: fullConfig } = useFullYamlConfig();

  useEffect(() => {
    if (fullConfig) {
      setYaml(fullConfig);
    }
  }, [fullConfig]);

  const handleSubmit = async () => {
    if (!name || !yaml) return;
    try {
      await createEngine.mutateAsync({ engine_name: name, yaml_configuration: yaml });
      setName('');
      setYaml('');
      onClose();
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            bgcolor: '#0a0a0c',
            border: '1px solid rgba(0, 243, 255, 0.2)',
            boxShadow: '0 0 30px rgba(0, 243, 255, 0.1)',
            backgroundImage: 'linear-gradient(rgba(0, 243, 255, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 243, 255, 0.05) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }
        }
      }}
    >
      <DialogTitle sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid rgba(0, 243, 255, 0.1)',
        pb: 2
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Cpu size={20} style={{ color: '#00f3ff' }} />
          <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 800, color: '#fff', letterSpacing: 1 }}>
            PROVISION NEW ENGINE
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small" sx={{ color: 'rgba(255,255,255,0.5)' }}>
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ mt: 2 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <TextField
            label="ENGINE IDENTITY"
            placeholder="e.g. Full Recon Suite"
            fullWidth
            value={name}
            onChange={(e) => setName(e.target.value)}
            variant="filled"
            sx={{
              '& .MuiFilledInput-root': {
                bgcolor: 'rgba(255,255,255,0.03)',
                '&:before, &:after': { display: 'none' },
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#fff',
                fontFamily: 'monospace'
              },
              '& .MuiInputLabel-root': { color: 'rgba(0, 243, 255, 0.5)', fontFamily: 'Orbitron', fontSize: '0.7rem' }
            }}
          />

          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
              <Typography sx={{ color: 'rgba(0,243,255,0.5)', fontFamily: 'Orbitron', fontSize: '0.7rem' }}>
                YAML CONFIGURATION BLUEPRINT
              </Typography>
              <Tooltip title="View configuration reference">
                <IconButton
                  size="small"
                  onClick={() => setRefOpen(true)}
                  sx={{
                    color: 'rgba(0,243,255,0.6)',
                    p: 0.5,
                    '&:hover': { color: '#00f3ff', bgcolor: 'rgba(0,243,255,0.08)' },
                  }}
                >
                  <BookOpen size={14} />
                </IconButton>
              </Tooltip>
            </Box>
            <TextField
              placeholder="# Enter your engine configuration here"
              fullWidth
              multiline
              rows={15}
              value={yaml}
              onChange={(e) => setYaml(e.target.value)}
              variant="filled"
              sx={{
                '& .MuiFilledInput-root': {
                  bgcolor: 'rgba(255,255,255,0.03)',
                  '&:before, &:after': { display: 'none' },
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#00f3ff',
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                },
              }}
            />
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 3, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <Button
          onClick={onClose}
          sx={{ color: 'rgba(255,255,255,0.5)', fontFamily: 'Orbitron', fontSize: '0.7rem' }}
        >
          CANCEL
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={!name || !yaml || createEngine.isPending}
          variant="contained"
          sx={{
            bgcolor: '#00f3ff',
            color: '#000',
            fontFamily: 'Orbitron',
            fontWeight: 900,
            fontSize: '0.75rem',
            px: 4,
            '&:hover': { bgcolor: '#00d8e6' },
            '&.Mui-disabled': { bgcolor: 'rgba(0,243,255,0.1)', color: 'rgba(255,255,255,0.2)' }
          }}
        >
          {createEngine.isPending ? 'PROVISIONING...' : 'INITIALIZE ENGINE'}
        </Button>
      </DialogActions>
      <EngineConfigReferenceModal open={refOpen} onClose={() => setRefOpen(false)} />
    </Dialog>
  );
};
