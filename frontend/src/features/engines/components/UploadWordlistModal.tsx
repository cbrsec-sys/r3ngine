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
  Paper
} from '@mui/material';
import { X, FileUp, Upload } from 'lucide-react';
import { useUploadWordlist } from '../api';

interface UploadWordlistModalProps {
  open: boolean;
  onClose: () => void;
}

export const UploadWordlistModal: React.FC<UploadWordlistModalProps> = ({ open, onClose }) => {
  const [name, setName] = useState('');
  const [shortName, setShortName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const uploadWordlist = useUploadWordlist();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async () => {
    if (!name || !shortName || !file) return;

    const formData = new FormData();
    formData.append('name', name);
    formData.append('short_name', shortName);
    formData.append('upload_file', file);

    try {
      await uploadWordlist.mutateAsync(formData);
      setName('');
      setShortName('');
      setFile(null);
      onClose();
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            bgcolor: '#0a0a0c',
            border: '1px solid rgba(255, 0, 255, 0.2)',
            boxShadow: '0 0 30px rgba(255, 0, 255, 0.1)',
            backgroundImage: 'linear-gradient(rgba(255, 0, 255, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 0, 255, 0.05) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }
        }
      }}
    >
      <DialogTitle sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid rgba(255, 0, 255, 0.1)',
        pb: 2
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <FileUp size={20} style={{ color: '#ff00ff' }} />
          <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 800, color: '#fff', letterSpacing: 1 }}>
            UPLOAD_WORDLIST_PAYLOAD
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small" sx={{ color: 'rgba(255,255,255,0.5)' }}>
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ mt: 2 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <TextField
            label="WORDLIST_NAME"
            placeholder="e.g. Awesome Wordlist"
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
              '& .MuiInputLabel-root': { color: 'rgba(255, 0, 255, 0.5)', fontFamily: 'Orbitron', fontSize: '0.7rem' }
            }}
          />

          <TextField
            label="SHORT_IDENTIFIER"
            placeholder="e.g. awesome_wordlist"
            fullWidth
            value={shortName}
            onChange={(e) => setShortName(e.target.value)}
            variant="filled"
            sx={{
              '& .MuiFilledInput-root': {
                bgcolor: 'rgba(255,255,255,0.03)',
                '&:before, &:after': { display: 'none' },
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#fff',
                fontFamily: 'monospace'
              },
              '& .MuiInputLabel-root': { color: 'rgba(255, 0, 255, 0.5)', fontFamily: 'Orbitron', fontSize: '0.7rem' }
            }}
          />

          <Box>
            <Typography variant="caption" sx={{ color: 'rgba(255, 0, 255, 0.5)', fontFamily: 'Orbitron', fontSize: '0.7rem', mb: 1, display: 'block' }}>
              SELECT_PAYLOAD_FILE (.TXT)
            </Typography>
            <input
              type="file"
              accept=".txt"
              style={{ display: 'none' }}
              id="wordlist-file-input"
              onChange={handleFileChange}
            />
            <label htmlFor="wordlist-file-input">
              <Paper sx={{
                p: 3,
                bgcolor: 'rgba(255,255,255,0.02)',
                border: '1px dashed rgba(255,0,255,0.3)',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 1,
                transition: 'all 0.2s',
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.04)',
                  borderColor: '#ff00ff'
                }
              }}>
                <Upload size={24} style={{ color: file ? '#ff00ff' : 'rgba(255,255,255,0.3)' }} />
                <Typography sx={{ color: file ? '#fff' : 'rgba(255,255,255,0.5)', fontSize: '0.8rem', fontFamily: 'monospace' }}>
                  {file ? file.name : 'CLICK_TO_SCAN_FILESYSTEM'}
                </Typography>
              </Paper>
            </label>
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
          disabled={!name || !shortName || !file || uploadWordlist.isPending}
          variant="contained"
          sx={{
            bgcolor: '#ff00ff',
            color: '#fff',
            fontFamily: 'Orbitron',
            fontWeight: 900,
            fontSize: '0.75rem',
            px: 4,
            '&:hover': { bgcolor: '#e600e6' },
            '&.Mui-disabled': { bgcolor: 'rgba(255,0,255,0.1)', color: 'rgba(255,255,255,0.2)' }
          }}
        >
          {uploadWordlist.isPending ? 'UPLOADING...' : 'COMMIT_PAYLOAD'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
