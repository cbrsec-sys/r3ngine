import { useThemeTokens } from '../theme/useThemeTokens';
import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Stack,
  IconButton,
  useTheme,
  alpha,
} from '@mui/material';
import { X, AlertTriangle, ShieldAlert } from 'lucide-react';

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  isDestructive?: boolean;
  isLoading?: boolean;
  type?: 'info' | 'warning' | 'danger' | 'success';
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'CONFIRM',
  cancelText = 'CANCEL',
  isDestructive = true,
  isLoading = false,
  type,
}) => {
  const { tokens } = useThemeTokens();
  const isActuallyDestructive = isDestructive || type === 'danger' || type === 'warning';
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';
  const accentColor = isActuallyDestructive ? '#ff003c' : theme.palette.primary.main;
  return (
    <Dialog
      open={open}
      onClose={isLoading ? undefined : onClose}
      maxWidth="xs"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            bgcolor: isLight ? theme.palette.background.paper : '#0d0c14',
            backgroundImage: isLight
              ? 'none'
              : 'linear-gradient(rgba(255, 0, 60, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 0, 60, 0.02) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
            border: isLight
              ? `1px solid ${alpha(accentColor, 0.3)}`
              : `1px solid ${isActuallyDestructive ? 'rgba(255, 0, 60, 0.3)' : 'rgba(0, 243, 255, 0.3)'}`,
            borderRadius: isLight ? 1 : 0,
            boxShadow: isLight
              ? `0 4px 20px ${alpha(accentColor, 0.15)}`
              : `0 0 30px rgba(0, 0, 0, 0.5), 0 0 10px ${isActuallyDestructive ? 'rgba(255, 0, 60, 0.1)' : 'rgba(0, 243, 255, 0.1)'}`,
          }
        }
      }}
    >
      <DialogTitle sx={{
        m: 0,
        p: 2,
        bgcolor: isLight ? alpha(accentColor, 0.05) : (isActuallyDestructive ? 'rgba(255, 0, 60, 0.05)' : 'rgba(0, 243, 255, 0.05)'),
        borderBottom: `1px solid ${isLight ? alpha(accentColor, 0.15) : (isActuallyDestructive ? 'rgba(255, 0, 60, 0.1)' : 'rgba(0, 243, 255, 0.1)')}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
          {isActuallyDestructive ? <ShieldAlert size={20} color="#ff003c" /> : <AlertTriangle size={20} color={tokens.accent.primary} />}
          <Typography sx={{
            fontFamily: 'var(--r3-heading-font)',
            fontWeight: 900,
            color: 'text.primary',
            letterSpacing: '0.1rem',
            fontSize: '0.9rem'
          }}>
            {title.toUpperCase()}
          </Typography>
        </Stack>
        {!isLoading && (
          <IconButton onClick={onClose} size="small" sx={{ color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.3)', '&:hover': { color: 'text.primary' } }}>
            <X size={18} />
          </IconButton>
        )}
      </DialogTitle>

      <DialogContent sx={{ px: 3, pb: 3, pt: '28px !important' }}>
        <Typography sx={{
          color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.7)',
          fontSize: '0.85rem',
          lineHeight: 1.6,
          textAlign: 'center'
        }}>
          {message}
        </Typography>
      </DialogContent>

      <DialogActions sx={{ p: 3, gap: 2 }}>
        <Button
          onClick={onClose}
          disabled={isLoading}
          sx={{
            flex: 1,
            color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.5)',
            fontFamily: 'var(--r3-heading-font)',
            fontWeight: 800,
            fontSize: '0.7rem',
            '&:hover': {
              color: 'text.primary',
              bgcolor: isLight ? alpha(theme.palette.divider, 0.5) : 'rgba(255,255,255,0.05)'
            }
          }}
        >
          {cancelText}
        </Button>
        <Button
          onClick={onConfirm}
          disabled={isLoading}
          variant="contained"
          sx={{
            flex: 1,
            bgcolor: accentColor,
            color: isLight ? (isActuallyDestructive ? '#fff' : '#000') : '#fff',
            fontFamily: isLight ? 'var(--r3-heading-font)' : 'Orbitron',
            fontWeight: 900,
            fontSize: '0.7rem',
            '&:hover': { bgcolor: isActuallyDestructive ? '#e60036' : theme.palette.primary.dark }
          }}
        >
          {confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
