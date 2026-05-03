import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  CircularProgress,
  IconButton,
  Divider,
  Paper,
  Alert
} from '@mui/material';
import { X, RefreshCw, ExternalLink, ShieldCheck, AlertCircle } from 'lucide-react';
import { useRengineUpdateCheck } from '../api';
import type { RengineUpdateResponse } from '../api';

interface CheckForUpdateModalProps {
  open: boolean;
  onClose: () => void;
  onUpdateFound?: (available: boolean) => void;
}

export const CheckForUpdateModal: React.FC<CheckForUpdateModalProps> = ({ open, onClose, onUpdateFound }) => {
  const [result, setResult] = useState<RengineUpdateResponse | null>(null);
  const updateCheck = useRengineUpdateCheck();

  const handleCheck = async () => {
    try {
      const data = await updateCheck.mutateAsync();
      setResult(data);
      if (data.update_available && onUpdateFound) {
        onUpdateFound(true);
        localStorage.setItem('update_available', 'true');
      } else if (!data.update_available && onUpdateFound) {
        onUpdateFound(false);
        localStorage.setItem('update_available', 'false');
      }
    } catch (err) {
      console.error('Update check failed', err);
    }
  };

  const handleClose = () => {
    setResult(null);
    onClose();
  };

  React.useEffect(() => {
    if (open && !result && !updateCheck.isPending) {
      handleCheck();
    }
  }, [open]);

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      paperprops={{
        sx: {
          bgcolor: 'rgba(10, 10, 20, 0.95)',
          backdropFilter: 'blur(15px)',
          border: '1px solid rgba(0, 243, 255, 0.2)',
          borderRadius: 4,
          boxShadow: '0 0 40px rgba(0, 243, 255, 0.1)',
          backgroundImage: 'none'
        }
      }}
    >
      <DialogTitle sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        p: 3,
        pb: 1
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <RefreshCw size={24} color="#00f3ff" style={{ animation: updateCheck.isPending ? 'spin 2s linear infinite' : 'none' }} />
          <Typography variant="h5" sx={{ fontFamily: 'Orbitron', fontWeight: 900, color: '#fff', letterSpacing: 1 }}>
            VERSION_CHECK
          </Typography>
        </Box>
        <IconButton onClick={handleClose} sx={{ color: 'rgba(255,255,255,0.5)' }}>
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 3 }}>
        {updateCheck.isPending ? (
          <Box sx={{ py: 8, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
            <CircularProgress sx={{ color: '#00f3ff' }} size={60} thickness={2} />
            <Typography sx={{ color: 'rgba(0, 243, 255, 0.6)', fontFamily: 'Orbitron', fontSize: '0.8rem', letterSpacing: 2 }}>
              CONTACTING_CENTRAL_COMMAND...
            </Typography>
          </Box>
        ) : result ? (
          <Box>
            {result.update_available ? (
              <Box>
                <Alert
                  severity="info"
                  icon={<AlertCircle size={24} />}
                  sx={{
                    bgcolor: 'rgba(0, 243, 255, 0.1)',
                    color: '#00f3ff',
                    border: '1px solid rgba(0, 243, 255, 0.3)',
                    mb: 3,
                    '& .MuiAlert-icon': { color: '#00f3ff' }
                  }}
                >
                  <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 0.5 }}>
                    UPDATE AVAILABLE: v{result.latest_version}
                  </Typography>
                  <Typography variant="body2">
                    A newer version of reNgine is ready for deployment. Please follow the update instructions to upgrade from v{result.current_version}.
                  </Typography>
                </Alert>

                <Typography variant="overline" sx={{ color: 'rgba(255,255,255,0.4)', fontWeight: 900, letterSpacing: 2 }}>
                  CHANGELOG_DATA
                </Typography>
                <Paper sx={{
                  mt: 1,
                  p: 3,
                  bgcolor: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  maxHeight: 400,
                  overflowY: 'auto',
                  '&::-webkit-scrollbar': { width: 4 },
                  '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(0, 243, 255, 0.2)', borderRadius: 10 }
                }}>
                  <Box sx={{
                    color: 'rgba(255,255,255,0.8)',
                    '& h1, & h2, & h3': { color: '#00f3ff', fontFamily: 'Orbitron', mt: 2, mb: 1 },
                    '& p': { mb: 2, lineHeight: 1.6 },
                    '& ul, & ol': { pl: 3, mb: 2 },
                    '& li': { mb: 1 },
                    '& code': { bgcolor: 'rgba(0,0,0,0.3)', p: '2px 6px', borderRadius: 1, color: '#ff00ff' },
                    '& pre': { bgcolor: 'rgba(0,0,0,0.5)', p: 2, borderRadius: 2, overflowX: 'auto', mb: 2 }
                  }}>
                    {/* Using a simple formatter to bypass react-markdown build issues in this environment */}
                    <Box sx={{ whiteSpace: 'pre-wrap', fontFamily: 'Inter, sans-serif' }}>
                      {(result.changelog || 'No changelog provided.').split('\n').map((line, i) => {
                        if (line.startsWith('### ')) return <Typography key={i} variant="h6" sx={{ color: '#00f3ff', mt: 2, mb: 1, fontWeight: 800 }}>{line.replace('### ', '')}</Typography>;
                        if (line.startsWith('## ')) return <Typography key={i} variant="h5" sx={{ color: '#00f3ff', mt: 2, mb: 1, fontWeight: 800 }}>{line.replace('## ', '')}</Typography>;
                        if (line.startsWith('# ')) return <Typography key={i} variant="h4" sx={{ color: '#00f3ff', mt: 2, mb: 1, fontWeight: 800 }}>{line.replace('# ', '')}</Typography>;
                        if (line.startsWith('- ') || line.startsWith('* ')) return <Box key={i} sx={{ display: 'flex', gap: 1, mb: 0.5 }}><Typography sx={{ color: '#00f3ff' }}>•</Typography><Typography variant="body2">{line.substring(2)}</Typography></Box>;
                        return <Typography key={i} variant="body2" sx={{ mb: 1 }}>{line}</Typography>;
                      })}
                    </Box>
                  </Box>
                </Paper>
              </Box>
            ) : result.message === 'RateLimited' ? (
              <Box sx={{ py: 4, textAlign: 'center' }}>
                <AlertCircle size={48} color="#ff0055" style={{ marginBottom: 16 }} />
                <Typography variant="h6" sx={{ color: '#fff', mb: 1 }}>GitHub Rate Limit Exceeded</Typography>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                  We couldn't check for updates because GitHub's API rate limit was reached.
                  Please try again in about an hour.
                </Typography>
              </Box>
            ) : (
              <Box sx={{ py: 6, textAlign: 'center' }}>
                <ShieldCheck size={64} color="#00ff9d" style={{ marginBottom: 24, filter: 'drop-shadow(0 0 15px rgba(0, 255, 157, 0.3))' }} />
                <Typography variant="h5" sx={{ color: '#fff', fontFamily: 'Orbitron', fontWeight: 900, mb: 1 }}>
                  SYSTEM_OPTIMIZED
                </Typography>
                <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                  You are running the latest version of reNgine (v{result.current_version}).
                </Typography>
              </Box>
            )}
          </Box>
        ) : (
          <Typography sx={{ color: 'rgba(255,255,255,0.5)', textAlign: 'center', py: 4 }}>
            Something went wrong. Please try again.
          </Typography>
        )}
      </DialogContent>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />

      <DialogActions sx={{ p: 3 }}>
        <Button
          onClick={handleClose}
          sx={{ color: 'rgba(255,255,255,0.6)', fontFamily: 'Orbitron' }}
        >
          CLOSE
        </Button>
        {result?.update_available && (
          <Button
            variant="contained"
            startIcon={<ExternalLink size={18} />}
            href={result.redirect_link}
            target="_blank"
            sx={{
              bgcolor: '#00f3ff',
              color: '#000',
              fontWeight: 900,
              fontFamily: 'Orbitron',
              '&:hover': { bgcolor: '#00d0ff' }
            }}
          >
            UPDATE_NOW
          </Button>
        )}
        {!updateCheck.isPending && (
          <Button
            variant="outlined"
            onClick={handleCheck}
            startIcon={<RefreshCw size={18} />}
            sx={{
              borderColor: 'rgba(0, 243, 255, 0.5)',
              color: '#00f3ff',
              fontWeight: 900,
              fontFamily: 'Orbitron',
              '&:hover': { borderColor: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.05)' }
            }}
          >
            RECHECK
          </Button>
        )}
      </DialogActions>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </Dialog>
  );
};
