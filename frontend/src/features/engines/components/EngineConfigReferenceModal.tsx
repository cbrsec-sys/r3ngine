import React, { useState, useRef, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  CircularProgress,
  InputAdornment,
  IconButton,
  Tooltip,
  useTheme,
  alpha,
} from '@mui/material';
import { BookOpen, X, Search, Copy, Check } from 'lucide-react';
import { useYamlConfigReference } from '../api';

interface EngineConfigReferenceModalProps {
  open: boolean;
  onClose: () => void;
}

function colorForLine(line: string, isLight: boolean): string {
  const trimmed = line.trimStart();
  if (trimmed.startsWith('#')) return isLight ? 'rgba(0,0,0,0.45)' : 'rgba(255,255,255,0.4)';
  if (/^[a-zA-Z_]/.test(line)) return isLight ? '#c2410c' : '#ff3333';
  if (/^ {2}[a-zA-Z_]/.test(line)) return isLight ? '#b45309' : '#e5c07b';
  return isLight ? '#0f172a' : '#ffffff';
}

export const EngineConfigReferenceModal: React.FC<EngineConfigReferenceModalProps> = ({
  open,
  onClose,
}) => {
  const [search, setSearch] = useState('');
  const [copied, setCopied] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const { data: content, isLoading } = useYamlConfigReference();
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';

  const lines = content ? content.split('\n') : [];
  const lowerSearch = search.toLowerCase();

  const matchIndex =
    search.length > 0
      ? lines.findIndex(l => l.toLowerCase().includes(lowerSearch))
      : -1;

  useEffect(() => {
    if (matchIndex >= 0 && containerRef.current) {
      const el = containerRef.current.querySelector<HTMLElement>(
        `#ref-line-${matchIndex}`
      );
      el?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  }, [matchIndex, search]);

  useEffect(() => {
    if (!open) setSearch('');
  }, [open]);

  const handleCopy = async () => {
    if (!content) return;
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            bgcolor: isLight ? 'background.paper' : '#0a0a0c',
            border: isLight ? '1px solid rgba(0,0,0,0.1)' : '1px solid rgba(0,243,255,0.2)',
            boxShadow: isLight ? 'none' : '0 0 30px rgba(0,243,255,0.1)',
            backgroundImage: isLight
              ? 'none'
              : 'linear-gradient(rgba(0,243,255,0.05) 1px, transparent 1px), ' +
                'linear-gradient(90deg, rgba(0,243,255,0.05) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
            maxHeight: '88vh',
          },
        },
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid',
          borderColor: 'divider',
          pb: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <BookOpen size={20} style={{ color: isLight ? theme.palette.primary.main : '#00f3ff' }} />
          <Typography
            sx={{ fontFamily: 'Orbitron', fontWeight: 800, color: 'text.primary', letterSpacing: 1 }}
          >
            CONFIGURATION REFERENCE
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small" sx={{ color: 'text.secondary' }}>
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2, pb: 1 }}>
        <TextField
          size="small"
          placeholder="Search configuration keys..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          fullWidth
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <Search size={14} style={{ color: isLight ? 'text.secondary' : 'rgba(0,243,255,0.5)' }} />
                </InputAdornment>
              ),
            },
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              fontFamily: 'monospace',
              fontSize: '0.75rem',
              color: 'text.primary',
              '& fieldset': { borderColor: isLight ? 'rgba(0,0,0,0.15)' : 'rgba(0,243,255,0.3)' },
              '&:hover fieldset': { borderColor: isLight ? theme.palette.primary.main : 'rgba(0,243,255,0.5)' },
              '&.Mui-focused fieldset': { borderColor: isLight ? theme.palette.primary.main : '#00f3ff' },
              bgcolor: isLight ? 'rgba(0,0,0,0.02)' : 'transparent',
            },
            '& input::placeholder': { color: 'text.secondary', opacity: 1 },
          }}
        />

        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress size={28} sx={{ color: isLight ? 'primary.main' : '#00f3ff' }} />
          </Box>
        ) : (
          <Box
            ref={containerRef}
            sx={{
              fontFamily: 'monospace',
              fontSize: '12px',
              lineHeight: 1.65,
              overflowY: 'auto',
              maxHeight: '62vh',
              bgcolor: isLight ? 'rgba(0,0,0,0.02)' : 'rgba(0,0,0,0.35)',
              border: isLight ? '1px solid rgba(0,0,0,0.15)' : '1px solid rgba(0,243,255,0.1)',
              borderRadius: 1,
              p: 1.5,
            }}
          >
            {lines.map((line, i) => {
              const isMatch =
                search.length > 0 && line.toLowerCase().includes(lowerSearch);
              const color = colorForLine(line, isLight);
              const matchStart = isMatch ? line.toLowerCase().indexOf(lowerSearch) : -1;

              return (
                <Box
                  key={i}
                  id={`ref-line-${i}`}
                  component="div"
                  sx={{
                    display: 'flex',
                    bgcolor: isMatch ? (isLight ? 'rgba(14,165,233,0.1)' : 'rgba(0,243,255,0.07)') : 'transparent',
                    borderRadius: 0.25,
                    px: 0.5,
                  }}
                >
                  <Box
                    component="span"
                    sx={{
                      color: isLight ? 'text.secondary' : 'rgba(0,243,255,0.2)',
                      userSelect: 'none',
                      minWidth: '3ch',
                      mr: 1.5,
                      flexShrink: 0,
                      textAlign: 'right',
                      fontSize: '10px',
                      lineHeight: 1.65,
                    }}
                  >
                    {i + 1}
                  </Box>
                  <Box component="span" sx={{ color, whiteSpace: 'pre', flexGrow: 1 }}>
                    {isMatch && matchStart >= 0 ? (
                      <>
                        {line.slice(0, matchStart)}
                        <mark
                          style={{
                            background: isLight ? 'rgba(14,165,233,0.25)' : 'rgba(0,243,255,0.3)',
                            color: isLight ? 'inherit' : '#fff',
                            borderRadius: '2px',
                          }}
                        >
                          {line.slice(matchStart, matchStart + search.length)}
                        </mark>
                        {line.slice(matchStart + search.length)}
                      </>
                    ) : (
                      line || ' '
                    )}
                  </Box>
                </Box>
              );
            })}
          </Box>
        )}
      </DialogContent>

      <DialogActions
        sx={{ borderTop: '1px solid', borderColor: 'divider', px: 2, py: 1.5, gap: 1 }}
      >
        <Typography
          sx={{
            color: 'text.secondary',
            fontSize: '0.65rem',
            fontFamily: 'Orbitron',
            flexGrow: 1,
          }}
        >
          {matchIndex >= 0
            ? `MATCH AT LINE ${matchIndex + 1}`
            : search.length > 0
            ? 'NO MATCH FOUND'
            : `${lines.length} LINES`}
        </Typography>
        <Tooltip title={copied ? 'Copied!' : 'Copy full config to clipboard'}>
          <Button
            size="small"
            onClick={handleCopy}
            disabled={!content}
            startIcon={copied ? <Check size={14} /> : <Copy size={14} />}
            sx={{
              fontFamily: 'Orbitron',
              fontSize: '0.65rem',
              letterSpacing: 1,
              color: copied ? '#00ff88' : (isLight ? 'primary.main' : '#00f3ff'),
              border: `1px solid ${
                copied
                  ? 'rgba(0,255,136,0.3)'
                  : isLight
                  ? alpha(theme.palette.primary.main, 0.3)
                  : 'rgba(0,243,255,0.3)'
              }`,
              '&:hover': {
                borderColor: copied
                  ? 'rgba(0,255,136,0.6)'
                  : isLight
                  ? theme.palette.primary.main
                  : 'rgba(0,243,255,0.6)',
              },
            }}
          >
            {copied ? 'COPIED' : 'COPY ALL'}
          </Button>
        </Tooltip>
        <Button
          size="small"
          onClick={onClose}
          sx={{
            fontFamily: 'Orbitron',
            fontSize: '0.65rem',
            letterSpacing: 1,
            color: 'text.secondary',
            border: '1px solid',
            borderColor: 'divider',
            '&:hover': { borderColor: 'text.primary' },
          }}
        >
          CLOSE
        </Button>
      </DialogActions>
    </Dialog>
  );
};
