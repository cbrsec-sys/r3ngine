import React, { useState, useEffect } from 'react';
import {
  Backdrop,
  Box,
  Button,
  Typography,
  LinearProgress,
  Stack,
  Chip,
} from '@mui/material';
import {
  CheckCircle,
  XCircle,
  Circle,
  Loader,
  PackageOpen,
  ShieldCheck,
  RefreshCw,
  AlertTriangle,
  RotateCw,
} from 'lucide-react';
import { useInstallStatus, type InstallStep } from '../api/pluginsApi';

// All steps in the expected order — used to fill in pending steps before backend emits them
const ALL_STEPS: { key: string; label: string }[] = [
  { key: 'upload',     label: 'Saving plugin archive' },
  { key: 'extract',    label: 'Extracting archive' },
  { key: 'verify',     label: 'Verifying integrity' },
  { key: 'validate',   label: 'Validating manifest' },
  { key: 'backup',     label: 'Creating database backup' },
  { key: 'register',   label: 'Registering plugin' },
  { key: 'migrations', label: 'Running database migrations' },
  { key: 'assets',     label: 'Installing UI assets & fixtures' },
  { key: 'complete',   label: 'Installation complete' },
];

interface Props {
  installId: string | null;
  onComplete: (pluginName: string) => void;
  onError: (message: string) => void;
}

const RELOAD_COUNTDOWN_SECONDS = 30;

const InstallProgressOverlay: React.FC<Props> = ({ installId, onComplete, onError }) => {
  const { data } = useInstallStatus(installId);
  const [reloading, setReloading] = useState(false);
  const [countdown, setCountdown] = useState(RELOAD_COUNTDOWN_SECONDS);

  useEffect(() => {
    if (!reloading) return;
    if (countdown <= 0) {
      window.location.reload();
      return;
    }
    const timer = setTimeout(() => setCountdown(c => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [reloading, countdown]);

  const handleReload = () => {
    setReloading(true);
  };

  // Merge backend steps with the full ordered step list so pending steps are always visible
  const mergedSteps: InstallStep[] = ALL_STEPS.map(({ key, label }) => {
    const live = data?.steps.find(s => s.key === key);
    return live ?? { key, label, status: 'pending', message: '' };
  });

  const completedCount = mergedSteps.filter(s => s.status === 'completed' || s.status === 'skipped').length;
  const progress = Math.round((completedCount / ALL_STEPS.length) * 100);
  const isSuccess = data?.status === 'success';
  const isFailed = data?.status === 'failed';

  if (reloading) {
    return (
      <Backdrop
        open
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 100,
          backdropFilter: 'blur(8px)',
          bgcolor: 'rgba(0, 0, 0, 0.85)',
        }}
      >
        <Box
          sx={{
            width: 420,
            background: 'linear-gradient(145deg, rgba(8,8,18,0.99) 0%, rgba(12,12,22,1) 100%)',
            border: '1px solid rgba(0,243,255,0.25)',
            borderRadius: '20px',
            p: 5,
            textAlign: 'center',
            boxShadow: '0 0 80px rgba(0,243,255,0.1)',
          }}
        >
          <Box
            sx={{
              display: 'inline-flex',
              mb: 3,
              color: '#00f3ff',
              filter: 'drop-shadow(0 0 12px #00f3ff)',
              animation: 'spinSlow 2s linear infinite',
              '@keyframes spinSlow': { from: { transform: 'rotate(0deg)' }, to: { transform: 'rotate(360deg)' } },
            }}
          >
            <RotateCw size={48} />
          </Box>

          <Typography
            sx={{
              fontFamily: 'Orbitron',
              fontWeight: 900,
              fontSize: '1.1rem',
              letterSpacing: 3,
              color: '#00f3ff',
              mb: 1.5,
            }}
          >
            SYSTEM RELOADING
          </Typography>

          <Typography
            sx={{
              color: 'rgba(255,255,255,0.5)',
              fontSize: '0.8rem',
              fontFamily: 'monospace',
              lineHeight: 1.7,
              mb: 3,
            }}
          >
            The system is reloading to apply the newly installed plugin.
            <br />
            The page will automatically reload in
          </Typography>

          <Box
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 72,
              height: 72,
              borderRadius: '50%',
              border: '2px solid rgba(0,243,255,0.3)',
              bgcolor: 'rgba(0,243,255,0.05)',
              mb: 3,
              boxShadow: '0 0 20px rgba(0,243,255,0.1)',
            }}
          >
            <Typography
              sx={{
                fontFamily: 'Orbitron',
                fontWeight: 900,
                fontSize: '1.6rem',
                color: '#00f3ff',
                lineHeight: 1,
              }}
            >
              {countdown}
            </Typography>
          </Box>

          <LinearProgress
            variant="determinate"
            value={((RELOAD_COUNTDOWN_SECONDS - countdown) / RELOAD_COUNTDOWN_SECONDS) * 100}
            sx={{
              height: 3,
              borderRadius: 2,
              bgcolor: 'rgba(255,255,255,0.06)',
              '& .MuiLinearProgress-bar': {
                borderRadius: 2,
                bgcolor: '#00f3ff',
                boxShadow: '0 0 8px #00f3ff',
              },
            }}
          />

          <Typography
            sx={{
              mt: 1.5,
              color: 'rgba(255,255,255,0.25)',
              fontSize: '0.65rem',
              fontFamily: 'Orbitron',
              letterSpacing: 1,
            }}
          >
            SECONDS REMAINING
          </Typography>
        </Box>
      </Backdrop>
    );
  }

  return (
    <Backdrop
      open={!!installId}
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 100,
        backdropFilter: 'blur(6px)',
        bgcolor: 'rgba(0, 0, 0, 0.75)',
      }}
    >
      <Box
        sx={{
          width: 480,
          background: 'linear-gradient(145deg, rgba(8,8,18,0.98) 0%, rgba(12,12,22,0.99) 100%)',
          border: `1px solid ${isSuccess ? 'rgba(0,255,98,0.3)' : isFailed ? 'rgba(255,0,60,0.3)' : 'rgba(0,243,255,0.2)'}`,
          borderRadius: '20px',
          p: 4,
          boxShadow: `0 0 60px ${isSuccess ? 'rgba(0,255,98,0.1)' : isFailed ? 'rgba(255,0,60,0.1)' : 'rgba(0,243,255,0.08)'}`,
        }}
      >
        {/* Header */}
        <Stack direction="row" spacing={2} sx={{ mb: 3, alignItems: 'center' }}>
          <Box sx={{ color: isSuccess ? '#00ff62' : isFailed ? '#ff003c' : '#00f3ff', filter: `drop-shadow(0 0 8px currentColor)` }}>
            {isSuccess ? <ShieldCheck size={28} /> : isFailed ? <XCircle size={28} /> : <PackageOpen size={28} />}
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography
              sx={{
                fontFamily: 'Orbitron',
                fontWeight: 900,
                fontSize: '1rem',
                letterSpacing: 2,
                color: isSuccess ? '#00ff62' : isFailed ? '#ff003c' : '#fff',
              }}
            >
              {isSuccess ? 'INSTALL SUCCESSFUL' : isFailed ? 'INSTALLATION FAILED' : 'INSTALLING PLUGIN'}
            </Typography>
            {data?.plugin_name && (
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace', fontSize: '0.7rem' }}>
                {data.plugin_name}
              </Typography>
            )}
          </Box>
          <Chip
            label={`${progress}%`}
            size="small"
            sx={{
              fontFamily: 'Orbitron',
              fontWeight: 900,
              fontSize: '0.65rem',
              bgcolor: 'rgba(255,255,255,0.05)',
              color: 'rgba(255,255,255,0.6)',
              border: '1px solid rgba(255,255,255,0.1)',
            }}
          />
        </Stack>

        {/* Progress bar */}
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{
            mb: 3,
            height: 3,
            borderRadius: 2,
            bgcolor: 'rgba(255,255,255,0.06)',
            '& .MuiLinearProgress-bar': {
              borderRadius: 2,
              bgcolor: isSuccess ? '#00ff62' : isFailed ? '#ff003c' : '#00f3ff',
              boxShadow: `0 0 8px ${isSuccess ? '#00ff62' : isFailed ? '#ff003c' : '#00f3ff'}`,
            },
          }}
        />

        {/* Step list */}
        <Stack spacing={0.5}>
          {mergedSteps.map((step) => (
            <StepRow key={step.key} step={step} />
          ))}
        </Stack>

        {/* Unsigned / legacy warning */}
        {isSuccess && data?.warning && (
          <Box sx={{ mt: 2.5, p: 1.5, bgcolor: 'rgba(255,152,0,0.07)', border: '1px solid rgba(255,152,0,0.25)', borderRadius: 1, display: 'flex', gap: 1.25, alignItems: 'flex-start' }}>
            <Box sx={{ color: '#ff9800', flexShrink: 0, mt: '1px' }}>
              <AlertTriangle size={14} />
            </Box>
            <Typography variant="caption" sx={{ color: '#ff9800', fontFamily: 'monospace', fontSize: '0.68rem', lineHeight: 1.5 }}>
              {data.warning}
            </Typography>
          </Box>
        )}

        {/* Error message */}
        {isFailed && data?.error && (
          <Box sx={{ mt: 2.5, p: 1.5, bgcolor: 'rgba(255,0,60,0.07)', border: '1px solid rgba(255,0,60,0.2)', borderRadius: 1 }}>
            <Typography variant="caption" sx={{ color: '#ff003c', fontFamily: 'monospace', fontSize: '0.7rem', wordBreak: 'break-all' }}>
              {data.error}
            </Typography>
          </Box>
        )}

        {/* Close / reload button — shown after terminal states */}
        {(isSuccess || isFailed) && (
          <Button
            fullWidth
            onClick={handleReload}
            startIcon={<RefreshCw size={14} />}
            sx={{
              mt: 3,
              fontFamily: 'Orbitron',
              fontWeight: 900,
              fontSize: '0.7rem',
              letterSpacing: 1.5,
              borderRadius: '8px',
              py: 1,
              color: isSuccess ? '#00ff62' : '#ff003c',
              border: `1px solid ${isSuccess ? 'rgba(0,255,98,0.3)' : 'rgba(255,0,60,0.3)'}`,
              bgcolor: isSuccess ? 'rgba(0,255,98,0.05)' : 'rgba(255,0,60,0.05)',
              '&:hover': {
                bgcolor: isSuccess ? 'rgba(0,255,98,0.12)' : 'rgba(255,0,60,0.12)',
              },
            }}
          >
            {isSuccess ? 'CLOSE & RELOAD' : 'DISMISS & RELOAD'}
          </Button>
        )}
      </Box>
    </Backdrop>
  );
};

// ── Step row ──────────────────────────────────────────────────────────────────

const StepRow: React.FC<{ step: InstallStep }> = ({ step }) => {
  const { status, label, message } = step;

  const iconEl = (() => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={14} color="#00ff62" />;
      case 'failed':
        return <XCircle size={14} color="#ff003c" />;
      case 'skipped':
        return <Circle size={14} color="#4fc3f7" />;
      case 'in_progress':
        return (
          <Box
            sx={{
              display: 'flex',
              animation: 'spin 1s linear infinite',
              '@keyframes spin': { from: { transform: 'rotate(0deg)' }, to: { transform: 'rotate(360deg)' } },
            }}
          >
            <Loader size={14} color="#00f3ff" />
          </Box>
        );
      default:
        return <Circle size={14} color="rgba(255,255,255,0.2)" />;
    }
  })();

  const labelColor = (() => {
    if (status === 'completed') return 'rgba(255,255,255,0.7)';
    if (status === 'in_progress') return '#fff';
    if (status === 'failed') return '#ff003c';
    if (status === 'skipped') return 'rgba(79,195,247,0.6)';
    return 'rgba(255,255,255,0.25)';
  })();

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 0.6 }}>
        <Box sx={{ flexShrink: 0, width: 16, display: 'flex', justifyContent: 'center' }}>{iconEl}</Box>
        <Typography
          sx={{
            fontFamily: 'Orbitron',
            fontSize: '0.65rem',
            fontWeight: status === 'in_progress' ? 900 : 600,
            letterSpacing: 0.8,
            color: labelColor,
            flex: 1,
          }}
        >
          {label.toUpperCase()}
        </Typography>
        {status === 'in_progress' && (
          <Box sx={{ display: 'flex', gap: '3px', alignItems: 'center' }}>
            {[0, 1, 2].map(i => (
              <Box
                key={i}
                sx={{
                  width: 3,
                  height: 3,
                  borderRadius: '50%',
                  bgcolor: '#00f3ff',
                  animation: 'dotPulse 1.2s ease-in-out infinite',
                  animationDelay: `${i * 0.2}s`,
                  '@keyframes dotPulse': { '0%,80%,100%': { opacity: 0.2 }, '40%': { opacity: 1 } },
                }}
              />
            ))}
          </Box>
        )}
        {status === 'skipped' && (
          <Typography
            sx={{
              fontFamily: 'Orbitron',
              fontSize: '0.5rem',
              fontWeight: 700,
              letterSpacing: 0.5,
              color: 'rgba(79,195,247,0.5)',
              border: '1px solid rgba(79,195,247,0.2)',
              borderRadius: '3px',
              px: 0.6,
              py: 0.1,
              lineHeight: 1.6,
            }}
          >
            NOT REQUIRED
          </Typography>
        )}
      </Box>
      {status === 'failed' && message && (
        <Typography variant="caption" sx={{ color: 'rgba(255,0,60,0.6)', fontFamily: 'monospace', fontSize: '0.6rem', pl: 4, display: 'block' }}>
          {message}
        </Typography>
      )}
    </Box>
  );
};

export default InstallProgressOverlay;
