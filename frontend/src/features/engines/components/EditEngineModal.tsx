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
  CircularProgress
} from '@mui/material';
import { X, Cpu, Save } from 'lucide-react';
import { fetchEngineDetails, useUpdateEngine } from '../api';

interface EditEngineModalProps {
  open: boolean;
  onClose: () => void;
  engineId: number | null;
}

export const EditEngineModal: React.FC<EditEngineModalProps> = ({ open, onClose, engineId }) => {
  const [name, setName] = useState('');
  const [yaml, setYaml] = useState('');
  const [loading, setLoading] = useState(false);
  const updateEngine = useUpdateEngine();
  const backgroundRef = React.useRef<HTMLPreElement>(null);

  const handleScroll = (e: React.UIEvent<HTMLTextAreaElement>) => {
    if (backgroundRef.current) {
      backgroundRef.current.scrollTop = e.currentTarget.scrollTop;
    }
  };

  useEffect(() => {
    if (open && engineId) {
      setLoading(true);
      fetchEngineDetails(engineId)
        .then(data => {
          setName(data.engine_name);
          setYaml(data.yaml_configuration);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setLoading(false);
        });
    }
  }, [open, engineId]);

  const handleSubmit = async () => {
    if (!name || !yaml || !engineId) return;
    try {
      await updateEngine.mutateAsync({
        engine_id: engineId,
        engine_name: name,
        yaml_configuration: yaml
      });
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
            MODIFY_ENGINE_CONFIG
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small" sx={{ color: 'rgba(255,255,255,0.5)' }}>
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ mt: 2, minHeight: 400, display: 'flex', flexDirection: 'column' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flexGrow: 1 }}>
            <CircularProgress sx={{ color: '#00f3ff' }} />
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <TextField
              label="ENGINE_IDENTITY"
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

            <Box sx={{
              position: 'relative',
              width: '100%',
              height: 500,
              bgcolor: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 1,
              overflow: 'hidden'
            }}>
              <pre
                ref={backgroundRef}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  margin: 0,
                  padding: '16px',
                  pointerEvents: 'none',
                  overflow: 'hidden',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  fontFamily: 'monospace',
                  fontSize: '14px',
                  lineHeight: '1.5',
                  color: 'transparent',
                  boxSizing: 'border-box',
                }}
              >
                {yaml.split('\n').map((line, i) => {
                  const cleanLine = line.replace('\r', '');
                  const isComment = cleanLine.trim().startsWith('#');
                  const keyMatch = cleanLine.match(/^(\s*)([^#\s][^:]+:)(.*)$/);

                  if (isComment) {
                    return (
                      <span key={i} style={{ color: 'rgba(255,255,255,0.3)' }}>
                        {cleanLine}{i === yaml.split('\n').length - 1 ? '' : '\n'}
                      </span>
                    );
                  }

                  if (keyMatch) {
                    const [full, indent, key, rest] = keyMatch;
                    const isTopLevel = indent.length === 0;

                    return (
                      <span key={i}>
                        <span>{indent}</span>
                        <span style={{
                          color: isTopLevel ? '#ff3333' : '#e5c07b',
                          fontWeight: isTopLevel ? 900 : 400
                        }}>
                          {key}
                        </span>
                        <span style={{ color: '#fff' }}>{rest}</span>
                        {i === yaml.split('\n').length - 1 ? '' : '\n'}
                      </span>
                    );
                  }

                  return (
                    <span key={i} style={{ color: '#fff' }}>
                      {cleanLine}{i === yaml.split('\n').length - 1 ? '' : '\n'}
                    </span>
                  );
                })}
              </pre>
              <textarea
                value={yaml}
                onChange={(e) => setYaml(e.target.value)}
                onScroll={(e) => {
                  if (backgroundRef.current) {
                    backgroundRef.current.scrollTop = e.currentTarget.scrollTop;
                  }
                }}
                spellCheck={false}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  width: '100%',
                  height: '100%',
                  margin: 0,
                  padding: '16px',
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  resize: 'none',
                  fontFamily: 'monospace',
                  fontSize: '14px',
                  lineHeight: '1.5',
                  color: 'transparent',
                  caretColor: '#fff',
                  boxSizing: 'border-box',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  overflowY: 'auto',
                }}
              />
            </Box>
          </Box>
        )}
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
          disabled={!name || !yaml || updateEngine.isPending || loading}
          variant="contained"
          startIcon={<Save size={16} />}
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
          {updateEngine.isPending ? 'SYNCHRONIZING...' : 'COMMIT_CHANGES'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
