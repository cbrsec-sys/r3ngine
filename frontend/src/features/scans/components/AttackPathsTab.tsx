import React, { useState } from 'react';
import {
  Box,
  Stack,
  Typography,
  CircularProgress,
  Chip,
  Collapse,
  IconButton,
  Divider,
  Tooltip,
  Button,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  ChevronDown,
  ChevronRight,
  ShieldAlert,
  CheckCircle2,
  HelpCircle,
  GitBranch,
  Zap,
  AlertTriangle,
  ArrowRight,
} from 'lucide-react';
import { 
  useAttackPaths, 
  useTriggerAttackPathModeling,
  type AttackPath, 
  type AttackStep 
} from '../api/useAttackPaths';
import { TacticalPanel } from '../../../components/TacticalPanel';
import { Bot } from 'lucide-react';

// ─── Risk → color mapping ────────────────────────────────────────────────────
const RISK_COLOR: Record<string, string> = {
  critical: '#ff003c',
  high: '#ff9f00',
  medium: '#fffc00',
  low: '#00ff62',
  unknown: '#7000ff',
};

const RISK_LABEL: Record<string, string> = {
  critical: 'CRITICAL',
  high: 'HIGH',
  medium: 'MEDIUM',
  low: 'LOW',
  unknown: 'UNKNOWN',
};

// ─── Risk badge ───────────────────────────────────────────────────────────────
const RiskBadge: React.FC<{ risk: string }> = ({ risk }) => {
  const color = RISK_COLOR[risk] ?? RISK_COLOR.unknown;
  const label = RISK_LABEL[risk] ?? risk.toUpperCase();
  return (
    <Box
      sx={{
        display: 'inline-flex',
        px: 1,
        py: 0.2,
        borderRadius: 0.5,
        bgcolor: `${color}20`,
        border: `1px solid ${color}50`,
        color,
        fontSize: '0.6rem',
        fontWeight: 900,
        letterSpacing: 1,
        fontFamily: 'Orbitron',
      }}
    >
      {label}
    </Box>
  );
};

// ─── Individual step row ──────────────────────────────────────────────────────
const StepRow: React.FC<{ step: AttackStep; index: number }> = ({ step, index }) => {
  const isValidated = step.validated;
  const color = isValidated ? '#00ff62' : '#ff9f00';
  const StatusIcon = isValidated ? CheckCircle2 : HelpCircle;

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 1.5,
        py: 1,
        px: 1.5,
        borderRadius: 1,
        bgcolor: isValidated ? 'rgba(0,255,98,0.03)' : 'rgba(255,159,0,0.03)',
        border: `1px solid ${isValidated ? 'rgba(0,255,98,0.1)' : 'rgba(255,159,0,0.1)'}`,
      }}
    >
      {/* Step number */}
      <Box
        sx={{
          minWidth: 22,
          height: 22,
          borderRadius: '50%',
          bgcolor: 'rgba(0,243,255,0.1)',
          border: '1px solid rgba(0,243,255,0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#00f3ff',
          fontSize: '0.6rem',
          fontWeight: 900,
          flexShrink: 0,
        }}
      >
        {index + 1}
      </Box>

      {/* From → To */}
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 0.5 }}>
          <Typography
            noWrap
            sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.6)', fontFamily: 'monospace', maxWidth: 160 }}
          >
            {step.from.split('::').pop()}
          </Typography>
          <ArrowRight size={12} color="#00f3ff" />
          <Typography
            noWrap
            sx={{ fontSize: '0.7rem', color: '#00f3ff', fontFamily: 'monospace', fontWeight: 700, maxWidth: 160 }}
          >
            {step.to.split('::').pop()}
          </Typography>
        </Stack>
        <Stack direction="row" spacing={0.5} sx={{ mt: 0.4, alignItems: 'center' }}>
          <Box
            sx={{
              px: 0.7,
              py: 0.1,
              bgcolor: 'rgba(112,0,255,0.1)',
              border: '1px solid rgba(112,0,255,0.2)',
              borderRadius: 0.4,
              fontSize: '0.55rem',
              color: '#aa00ff',
              fontWeight: 800,
            }}
          >
            {step.edge_type}
          </Box>
          <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.35)' }}>
            conf: {(step.confidence * 100).toFixed(0)}%
          </Typography>
        </Stack>
      </Box>

      {/* Validated/Inferred badge */}
      <Tooltip title={isValidated ? 'ERL-confirmed — evidence available' : 'Rule-derived — no direct evidence'}>
        <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center', flexShrink: 0 }}>
          <StatusIcon size={12} color={color} />
          <Typography sx={{ fontSize: '0.6rem', color, fontWeight: 800, letterSpacing: 0.5 }}>
            {step.status.toUpperCase()}
          </Typography>
        </Stack>
      </Tooltip>
    </Box>
  );
};

// ─── Single attack path card ──────────────────────────────────────────────────
const AttackPathCard: React.FC<{ path: AttackPath; rank: number }> = ({ path, rank }) => {
  const [expanded, setExpanded] = useState(rank === 0); // expand first by default
  const riskColor = RISK_COLOR[path.risk] ?? RISK_COLOR.unknown;
  const validatedCount = path.steps.filter((s) => s.validated).length;
  const inferredCount = path.steps.length - validatedCount;

  return (
    <Box
      sx={{
        borderRadius: 1.5,
        border: `1px solid ${riskColor}30`,
        bgcolor: `${riskColor}08`,
        overflow: 'hidden',
        transition: 'border-color 0.2s',
        '&:hover': { borderColor: `${riskColor}60` },
      }}
    >
      {/* Header */}
      <Stack
        direction="row"
        spacing={1.5}
        sx={{
          alignItems: 'center',
          px: 2,
          py: 1.5,
          cursor: 'pointer',
          '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' },
        }}
        onClick={() => setExpanded((p) => !p)}
      >
        {/* Rank */}
        <Box
          sx={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            bgcolor: `${riskColor}20`,
            border: `1px solid ${riskColor}50`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: riskColor,
            fontSize: '0.7rem',
            fontWeight: 900,
            fontFamily: 'Orbitron',
            flexShrink: 0,
          }}
        >
          #{rank + 1}
        </Box>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 0.3, flexWrap: 'wrap', gap: 0.5 }}>
            <RiskBadge risk={path.risk} />
            <Typography
              noWrap
              sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace', fontStyle: 'italic' }}
            >
              {path.path_id}
            </Typography>
          </Stack>
          <Typography noWrap sx={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.7)', fontWeight: 700 }}>
            {path.potential_impact}
          </Typography>
        </Box>

        {/* Stats */}
        <Stack direction="row" spacing={{ xs: 1, sm: 2 }} sx={{ alignItems: 'center', flexShrink: 0, ml: 'auto' }}>
          <Stack sx={{ alignItems: 'center' }}>
            <Typography sx={{ fontSize: { xs: '0.8rem', sm: '1rem' }, fontWeight: 900, color: riskColor, fontFamily: 'Orbitron' }}>
              {path.score.toFixed(2)}
            </Typography>
            <Typography sx={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.3)', fontWeight: 700 }}>SCORE</Typography>
          </Stack>
          <Stack sx={{ alignItems: 'center' }}>
            <Typography sx={{ fontSize: { xs: '0.8rem', sm: '1rem' }, fontWeight: 900, color: '#00f3ff', fontFamily: 'Orbitron' }}>
              {path.step_count}
            </Typography>
            <Typography sx={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.3)', fontWeight: 700 }}>STEPS</Typography>
          </Stack>
          <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.4)', display: { xs: 'none', sm: 'inline-flex' } }}>
            {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </IconButton>
        </Stack>
      </Stack>

      {/* Step counts bar */}
      <Box sx={{ px: 2, pb: expanded ? 0 : 1 }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
          <Chip
            icon={<CheckCircle2 size={10} />}
            label={`${validatedCount} validated`}
            size="small"
            sx={{
              height: 18,
              fontSize: '0.6rem',
              fontWeight: 700,
              bgcolor: 'rgba(0,255,98,0.08)',
              border: '1px solid rgba(0,255,98,0.2)',
              color: '#00ff62',
              '& .MuiChip-icon': { color: '#00ff62', ml: '4px' },
            }}
          />
          <Chip
            icon={<HelpCircle size={10} />}
            label={`${inferredCount} inferred`}
            size="small"
            sx={{
              height: 18,
              fontSize: '0.6rem',
              fontWeight: 700,
              bgcolor: 'rgba(255,159,0,0.08)',
              border: '1px solid rgba(255,159,0,0.2)',
              color: '#ff9f00',
              '& .MuiChip-icon': { color: '#ff9f00', ml: '4px' },
            }}
          />
        </Stack>
      </Box>

      {/* Expanded steps */}
      <Collapse in={expanded}>
        <Divider sx={{ borderColor: `${riskColor}20`, my: 0.5 }} />
        <Box sx={{ px: 2, pb: 2, pt: 1 }}>
          <Typography
            sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', fontWeight: 800, mb: 1, letterSpacing: 1 }}
          >
            COMPROMISE CHAIN
          </Typography>
          <Stack spacing={0.75}>
            {path.steps.map((step, i) => (
              <StepRow key={i} step={step} index={i} />
            ))}
          </Stack>
        </Box>
      </Collapse>
    </Box>
  );
};

// ─── Empty state ──────────────────────────────────────────────────────────────
const EmptyState: React.FC = () => (
  <Box
    sx={{
      py: 8,
      textAlign: 'center',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 2,
      opacity: 0.5,
    }}
  >
    <GitBranch size={48} color="#00f3ff" />
    <Box>
      <Typography sx={{ fontSize: '0.9rem', fontWeight: 800, color: '#fff', mb: 0.5 }}>
        No Attack Paths Found
      </Typography>
      <Typography sx={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', maxWidth: 320, mx: 'auto' }}>
        The Attack Path Modeling Engine (APME) runs automatically after vulnerability scanning.
        No exploitable paths were detected for this scan.
      </Typography>
    </Box>
  </Box>
);

// ─── Main Tab ─────────────────────────────────────────────────────────────────
interface AttackPathsTabProps {
  scanId: number;
}

export const AttackPathsTab: React.FC<AttackPathsTabProps> = ({ scanId }) => {
  const { data, isLoading, isError, refetch } = useAttackPaths(scanId);
  const triggerAi = useTriggerAttackPathModeling();

  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const handleTriggerAi = async () => {
    try {
      await triggerAi.mutateAsync(scanId);
      setSnackbar({ open: true, message: 'AI Modeling initiated in background', severity: 'success' });
      // Refresh after a delay to see if results started appearing
      setTimeout(refetch, 5000);
    } catch {
      setSnackbar({ open: true, message: 'Failed to trigger AI modeling', severity: 'error' });
    }
  };

  return (
    <TacticalPanel
      title="ATTACK PATH MODELING"
      icon={<ShieldAlert size={14} color="#ff003c" />}
      headerAction={
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ alignItems: { xs: 'flex-start', sm: 'center' }, gap: 1 }}>
          <Button
            size="small"
            variant="outlined"
            onClick={handleTriggerAi}
            disabled={triggerAi.isPending}
            startIcon={triggerAi.isPending ? <CircularProgress size={12} /> : <Bot size={14} />}
            sx={{
              fontSize: '0.6rem',
              height: 24,
              borderColor: 'rgba(0,243,255,0.3)',
              color: '#00f3ff',
              fontFamily: 'Orbitron',
              '&:hover': {
                borderColor: '#00f3ff',
                bgcolor: 'rgba(0,243,255,0.05)',
              },
            }}
          >
            {triggerAi.isPending ? 'MODELING...' : 'TRIGGER AI MODELING'}
          </Button>
          {data && data.total_paths > 0 && (
            <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
              <Zap size={12} color="#fffc00" />
              <Typography sx={{ fontSize: '0.65rem', color: '#fffc00', fontWeight: 900, fontFamily: 'Orbitron' }}>
                {data.total_paths} PATHS FOUND
              </Typography>
            </Stack>
          )}
        </Stack>
      }
    >
      <Box sx={{ p: 2 }}>
        {/* Legend */}
        <Stack
          direction="row"
          spacing={2}
          sx={{
            mb: 2,
            p: 1.5,
            borderRadius: 1,
            bgcolor: 'rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.05)',
            flexWrap: 'wrap',
            gap: 1,
          }}
        >
          <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
            <CheckCircle2 size={12} color="#00ff62" />
            <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.6)', fontWeight: 600 }}>
              <Box component="span" sx={{ color: '#00ff62', fontWeight: 800 }}>Validated</Box>
              {' — ERL-confirmed with direct evidence'}
            </Typography>
          </Stack>
          <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
            <HelpCircle size={12} color="#ff9f00" />
            <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.6)', fontWeight: 600 }}>
              <Box component="span" sx={{ color: '#ff9f00', fontWeight: 800 }}>Inferred</Box>
              {' — Rule-derived, no direct exploit evidence'}
            </Typography>
          </Stack>
          <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
            <AlertTriangle size={12} color="#ff003c" />
            <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.6)', fontWeight: 600 }}>
              Paths sorted by risk score (highest first)
            </Typography>
          </Stack>
        </Stack>

        {/* Content */}
        {isLoading && (
          <Box sx={{ py: 6, textAlign: 'center' }}>
            <CircularProgress size={32} sx={{ color: '#00f3ff' }} />
            <Typography sx={{ mt: 2, fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>
              Loading attack paths...
            </Typography>
          </Box>
        )}

        {isError && (
          <Box
            sx={{
              p: 2,
              bgcolor: 'rgba(255,0,60,0.05)',
              border: '1px solid rgba(255,0,60,0.2)',
              borderRadius: 1,
              textAlign: 'center',
            }}
          >
            <Typography sx={{ fontSize: '0.75rem', color: '#ff003c', fontWeight: 700 }}>
              Failed to load attack paths. The APME may not have completed for this scan.
            </Typography>
          </Box>
        )}

        {!isLoading && !isError && data && (
          data.total_paths === 0 ? (
            <EmptyState />
          ) : (
            <Stack spacing={1.5}>
              {data.paths.map((path, i) => (
                <AttackPathCard key={path.path_id} path={path} rank={i} />
              ))}
            </Stack>
          )
        )}
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={5000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          variant="filled"
          sx={{
            fontFamily: 'Orbitron',
            fontSize: '0.8rem',
            fontWeight: 700,
            bgcolor: snackbar.severity === 'success' ? 'rgba(0, 243, 255, 0.9)' : 'rgba(255, 0, 85, 0.9)',
            color: '#000',
            border: '1px solid rgba(255,255,255,0.1)',
            '& .MuiAlert-icon': { color: '#000' }
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </TacticalPanel>
  );
};
