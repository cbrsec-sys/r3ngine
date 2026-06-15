import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  IconButton,
  CircularProgress,
  useTheme
} from '@mui/material';
import { X, FileText } from 'lucide-react';
import { fetchWordlistContent } from '../api';

interface ViewWordlistModalProps {
  open: boolean;
  onClose: () => void;
  wordlistId: number | null;
}

export const ViewWordlistModal: React.FC<ViewWordlistModalProps> = ({ open, onClose, wordlistId }) => {
  const [content, setContent] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';

  useEffect(() => {
    if (open && wordlistId) {
      setLoading(true);
      fetchWordlistContent(wordlistId)
        .then(data => {
          setContent(data.content);
          setName(data.name);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setLoading(false);
        });
    }
  }, [open, wordlistId]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            bgcolor: isLight ? 'background.paper' : '#0a0a0c',
            border: isLight ? '1px solid rgba(0, 0, 0, 0.1)' : '1px solid rgba(255, 0, 255, 0.2)',
            boxShadow: isLight ? 'none' : '0 0 30px rgba(255, 0, 255, 0.1)',
            backgroundImage: isLight ? 'none' : 'linear-gradient(rgba(255, 0, 255, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 0, 255, 0.05) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }
        }
      }}
    >
      <DialogTitle sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid',
        borderColor: 'divider',
        pb: 2
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <FileText size={20} style={{ color: isLight ? theme.palette.primary.main : '#ff00ff' }} />
          <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 800, color: 'text.primary', letterSpacing: 1 }}>
            {name ? `READ PAYLOAD: ${name.toUpperCase()}` : 'READ PAYLOAD'}
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small" sx={{ color: 'text.secondary' }}>
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ mt: 2, minHeight: 400, display: 'flex', flexDirection: 'column' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flexGrow: 1 }}>
            <CircularProgress sx={{ color: isLight ? 'primary.main' : '#ff00ff' }} />
          </Box>
        ) : (
          <Box
            component="div"
            sx={{
              bgcolor: isLight ? 'rgba(0,0,0,0.02)' : 'rgba(255,255,255,0.03)',
              p: 2,
              borderRadius: 1,
              border: isLight ? '1px solid rgba(0,0,0,0.15)' : '1px solid rgba(255,255,255,0.1)',
              color: isLight ? '#0f172a' : '#ff00ff',
              fontFamily: 'monospace',
              fontSize: '0.85rem',
              overflow: 'auto',
              flexGrow: 1,
              m: 0,
              whiteSpace: 'pre-wrap'
            }}
          >
            {content || 'PAYLOAD EMPTY OR UNAVAILABLE'}
          </Box>
        )}
        <Typography variant="caption" sx={{ mt: 1, color: 'text.secondary', fontFamily: 'Orbitron' }}>
          * SHOWING FIRST 1000 LINES OF PAYLOAD
        </Typography>
      </DialogContent>

      <DialogActions sx={{ p: 3, borderTop: '1px solid', borderColor: 'divider' }}>
        <Button
          onClick={onClose}
          sx={{ color: 'text.secondary', fontFamily: 'Orbitron', fontSize: '0.7rem' }}
        >
          CLOSE TERMINAL
        </Button>
      </DialogActions>
    </Dialog>
  );
};
