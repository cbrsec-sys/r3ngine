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
  useTheme,
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
  Server,
  Key,
  Lock,
} from 'lucide-react';
import { useParams, Link } from '@tanstack/react-router';
import { 
  useAttackPaths, 
  useTriggerAttackPathModeling,
  useRecalculateAttackPaths,
  useExplainAttackPath,
  type AttackPath, 
  type AttackStep,
  type EnrichedNode
} from '../api/useAttackPaths';
import { TacticalPanel } from '../../../components/TacticalPanel';
import { Bot, Brain } from 'lucide-react';
import { useThemeTokens } from '../../../theme/useThemeTokens';

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
  const { tokens } = useThemeTokens();
  const color = RISK_COLOR[risk] ?? RISK_COLOR.unknown;
  const label = RISK_LABEL[risk] ?? risk?.toUpperCase() ?? 'UNKNOWN';
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

// ─── Enriched Node Rendering ──────────────────────────────────────────────────
const RenderNode: React.FC<{ node: EnrichedNode | undefined; rawId: string; projectSlug?: string }> = ({ node, rawId, projectSlug }) => {
  const { tokens } = useThemeTokens();
  const theme = useTheme();
  const type = node?.type ?? (rawId.startsWith('vuln::') ? 'Vulnerability' : rawId.startsWith('goal::capability::') ? 'Capability' : rawId.startsWith('goal::privilege::') ? 'Privilege' : 'Asset');
  const subtype = node?.subtype ?? rawId.split('::').pop() ?? '';
  const name = node?.name ?? (type === 'Vulnerability' ? `Vulnerability #${subtype}` : subtype);
  
  let color = tokens.accent.primary;
  let icon = <Server size={14} />;
  let bgColor = 'rgba(0, 243, 255, 0.03)';
  let borderColor = `${tokens.accent.primary}15`;
  
  if (type === 'Vulnerability') {
    const severity = node?.severity ?? 2;
    const sevColors = ['#00ff62', '#00ff62', '#fffc00', '#ff9f00', '#ff003c'];
    color = sevColors[severity] ?? '#ff9f00';
    icon = <ShieldAlert size={14} />;
    bgColor = `${color}08`;
    borderColor = `${color}20`;
  } else if (type === 'Capability') {
    color = '#d500f9';
    icon = <Zap size={14} />;
    bgColor = 'rgba(213, 0, 249, 0.03)';
    borderColor = 'rgba(213, 0, 249, 0.1)';
  } else if (type === 'Privilege') {
    color = '#ffab00';
    icon = <Key size={14} />;
    bgColor = 'rgba(255, 171, 0, 0.03)';
    borderColor = 'rgba(255, 171, 0, 0.1)';
  } else if (type === 'Credential') {
    color = '#ffab00';
    icon = <Lock size={14} />;
    bgColor = 'rgba(255, 171, 0, 0.03)';
    borderColor = 'rgba(255, 171, 0, 0.1)';
  }

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        p: 1.5,
        borderRadius: 1,
        bgcolor: bgColor,
        border: `1px solid ${borderColor}`,
        width: '100%',
        boxShadow: `0 4px 12px rgba(0,0,0,0.15)`,
      }}
    >
      <Box
        sx={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          bgcolor: `${color}15`,
          border: `1px solid ${color}33`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: color,
          flexShrink: 0,
        }}
      >
        {icon}
      </Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 0.3 }}>
          <Typography
            sx={{
              fontSize: '0.55rem',
              fontWeight: 900,
              fontFamily: 'Orbitron',
              color: 'text.secondary',
              letterSpacing: 0.5,
            }}
          >
            {type.toUpperCase()} ({subtype.toUpperCase()})
          </Typography>
          {type === 'Vulnerability' && node?.cvss_score !== undefined && (
            <Chip
              label={`CVSS ${node.cvss_score}`}
              size="small"
              sx={{
                height: 14,
                fontSize: '0.5rem',
                fontFamily: 'monospace',
                bgcolor: 'action.hover',
                color: 'text.primary',
                border: '1px solid rgba(255,255,255,0.1)',
                '& .MuiChip-label': { px: 0.5 }
              }}
            />
          )}
        </Stack>
        <Typography
          noWrap
          sx={{
            fontSize: '0.74rem',
            color: 'rgba(255, 255, 255, 0.95)',
            fontWeight: 700,
          }}
        >
          {name}
        </Typography>
      </Box>
      {type === 'Vulnerability' && node?.vuln_id && projectSlug && (
        <Button
          size="small"
          component={Link}
          to={`/${projectSlug}/vulns`}
          sx={{
            fontSize: '0.55rem',
            color: color,
            borderColor: `${color}44`,
            border: '1px solid',
            px: 1,
            py: 0,
            height: 20,
            fontFamily: 'Orbitron',
            minWidth: 'auto',
            '&:hover': {
              bgcolor: `${color}11`,
              borderColor: color,
            }
          }}
        >
          VIEW
        </Button>
      )}
    </Box>
  );
};

// ─── Timeline Connector Edge ──────────────────────────────────────────────────
const TimelineConnector: React.FC<{ step: AttackStep }> = ({ step }) => {
  const { tokens } = useThemeTokens();
  const isValidated = step.validated;
  const edgeColor = isValidated ? '#00ff62' : '#ff9f00';
  const Icon = isValidated ? CheckCircle2 : HelpCircle;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'stretch', my: 0.5, pl: 1.5, position: 'relative', width: '100%' }}>
      <Box
        sx={{
          position: 'absolute',
          left: 14, // align with RenderNode circle center
          top: -10,
          bottom: -10,
          width: 2,
          borderLeft: `2px dashed ${edgeColor}44`,
          zIndex: 0,
        }}
      />

      <Box
        sx={{
          ml: 4,
          p: 1.5,
          borderRadius: 1,
          bgcolor: 'action.hover',
          border: '1px solid rgba(255,255,255,0.03)',
          zIndex: 1,
        }}
      >
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 0.8, flexWrap: 'wrap', gap: 0.5 }}>
          <Chip
            label={step.edge_type}
            size="small"
            sx={{
              height: 16,
              fontSize: '0.55rem',
              fontWeight: 900,
              bgcolor: 'rgba(112,0,255,0.1)',
              border: '1px solid rgba(112,0,255,0.2)',
              color: '#aa00ff',
              fontFamily: 'Orbitron',
            }}
          />
          <Typography sx={{ fontSize: '0.6rem', color: 'text.disabled', fontWeight: 700 }}>
            CONF: <Box component="span" sx={{ color: tokens.accent.primary }}>{(step.confidence * 100).toFixed(0)}%</Box>
          </Typography>
          <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center', ml: 'auto' }}>
            <Icon size={10} color={edgeColor} />
            <Typography sx={{ fontSize: '0.55rem', color: edgeColor, fontWeight: 900, fontFamily: 'Orbitron', letterSpacing: 0.5 }}>
              {step.status.toUpperCase()}
            </Typography>
          </Stack>
        </Stack>

        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.4 }}>
          {step.action}
        </Typography>
      </Box>
    </Box>
  );
};

// ─── Timeline Assembler ───────────────────────────────────────────────────────
const AttackPathTimeline: React.FC<{ steps: AttackStep[]; projectSlug?: string }> = ({ steps, projectSlug }) => {
  const { tokens } = useThemeTokens();
  if (!steps || steps.length === 0) return null;

  return (
    <Stack spacing={0} sx={{ mt: 1, position: 'relative' }}>
      {steps.map((step, i) => {
        const isLast = i === steps.length - 1;
        return (
          <React.Fragment key={i}>
            <RenderNode node={step.from_node} rawId={step.from} projectSlug={projectSlug} />
            <TimelineConnector step={step} />
            {isLast && (
              <RenderNode node={step.to_node} rawId={step.to} projectSlug={projectSlug} />
            )}
          </React.Fragment>
        );
      })}
    </Stack>
  );
};

// ─── Single attack path card ──────────────────────────────────────────────────
interface AttackPathCardProps {
  path: AttackPath;
  rank: number;
  projectSlug?: string;
}

const AttackPathCard: React.FC<AttackPathCardProps> = ({ path, rank, projectSlug }) => {
  const { tokens } = useThemeTokens();
  const [expanded, setExpanded] = useState(rank === 0);
  const riskColor = RISK_COLOR[path.risk] ?? RISK_COLOR.unknown;
  const validatedCount = path.steps.filter((s) => s.validated).length;
  const inferredCount = path.steps.length - validatedCount;
  const { scanId: scanIdStr } = useParams({ strict: false });
  const scanId = Number(scanIdStr);
  const explainMutation = useExplainAttackPath();

  const handleExplain = async () => {
    if (!scanId || !path.path_id) return;
    try {
      await explainMutation.mutateAsync({ pathId: path.path_id, scanId });
    } catch (err) {
      console.error('Failed to generate path explanation', err);
    }
  };


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
          '&:hover': { bgcolor: 'action.hover' },
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
              sx={{ fontSize: '0.7rem', color: 'text.secondary', fontFamily: 'monospace', fontStyle: 'italic' }}
            >
              {path.path_id}
            </Typography>
          </Stack>
          <Typography
            sx={{
              fontSize: '0.72rem',
              color: 'rgba(255,255,255,0.7)',
              fontWeight: 700,
              display: '-webkit-box',
              WebkitLineClamp: expanded ? 1 : 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {path.potential_impact}
          </Typography>
        </Box>

        {/* Stats */}
        <Stack direction="row" spacing={{ xs: 1, sm: 2 }} sx={{ alignItems: 'center', flexShrink: 0, ml: 'auto' }}>
          <Stack sx={{ alignItems: 'center' }}>
            <Typography sx={{ fontSize: { xs: '0.8rem', sm: '1rem' }, fontWeight: 900, color: riskColor, fontFamily: 'Orbitron' }}>
              {path.score.toFixed(2)}
            </Typography>
            <Typography sx={{ fontSize: '0.55rem', color: 'text.disabled', fontWeight: 700 }}>SCORE</Typography>
          </Stack>
          <Stack sx={{ alignItems: 'center' }}>
            <Typography sx={{ fontSize: { xs: '0.8rem', sm: '1rem' }, fontWeight: 900, color: tokens.accent.primary, fontFamily: 'Orbitron' }}>
              {path.step_count}
            </Typography>
            <Typography sx={{ fontSize: '0.55rem', color: 'text.disabled', fontWeight: 700 }}>STEPS</Typography>
          </Stack>
          <IconButton size="small" sx={{ color: 'text.secondary', display: { xs: 'none', sm: 'inline-flex' } }}>
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
        <Box sx={{ px: 2.5, pb: 2.5, pt: 1.5 }}>
          {/* Executive Narrative */}
          <Box
            sx={{
              mb: 3,
              p: 2,
              borderRadius: 1.5,
              bgcolor: 'rgba(0, 0, 0, 0.25)',
              border: '1px solid rgba(255, 255, 255, 0.03)',
            }}
          >
            <Typography
              sx={{
                fontSize: '0.62rem',
                color: riskColor,
                fontWeight: 900,
                fontFamily: 'Orbitron',
                letterSpacing: 1,
                mb: 1.5,
              }}
            >
              EXECUTIVE NARRATIVE
            </Typography>
            <Typography
              sx={{
                fontSize: '0.76rem',
                color: 'rgba(255,255,255,0.85)',
                lineHeight: 1.6,
                whiteSpace: 'pre-line',
              }}
            >
              {path.potential_impact}
            </Typography>
          </Box>

          {/* Explain Path Section */}
          <Box
            sx={{
              mb: 3,
              p: 2,
              borderRadius: 1.5,
              bgcolor: 'rgba(0, 243, 255, 0.02)',
              border: '1px solid rgba(0, 243, 255, 0.08)',
            }}
          >
            <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
              <Typography
                sx={{
                  fontSize: '0.62rem',
                  color: tokens.accent.primary,
                  fontWeight: 900,
                  fontFamily: 'Orbitron',
                  letterSpacing: 1,
                }}
              >
                TACTICAL AI EXPLANATION
              </Typography>
              {!path.explanation && (
                <Button
                  size="small"
                  variant="outlined"
                  onClick={handleExplain}
                  disabled={explainMutation.isPending}
                  startIcon={explainMutation.isPending ? <CircularProgress size={10} color="inherit" /> : <Brain size={12} />}
                  sx={{
                    fontSize: '0.55rem',
                    height: 20,
                    borderColor: `${tokens.accent.primary}4D`,
                    color: tokens.accent.primary,
                    fontFamily: 'Orbitron',
                    '&:hover': {
                      borderColor: tokens.accent.primary,
                      bgcolor: `${tokens.accent.primary}0D`,
                    },
                  }}
                >
                  {explainMutation.isPending ? 'GENERATING...' : 'EXPLAIN THIS'}
                </Button>
              )}
            </Stack>
            {path.explanation ? (
              <Typography
                sx={{
                  fontSize: '0.74rem',
                  color: 'rgba(255,255,255,0.8)',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-line',
                }}
              >
                {path.explanation}
              </Typography>
            ) : (
              <Typography
                sx={{
                  fontSize: '0.7rem',
                  color: 'text.secondary',
                  fontStyle: 'italic',
                }}
              >
                {explainMutation.isPending
                  ? 'Analyzing tactical vector patterns. This may take up to a minute...'
                  : 'Click "EXPLAIN THIS" to generate an in-depth, step-by-step intelligence breakdown of this attack vector.'}
              </Typography>
            )}
          </Box>


          <Typography
            sx={{ fontSize: '0.6rem', color: 'text.disabled', fontWeight: 800, mb: 2, letterSpacing: 1 }}
          >
            COMPROMISE CHAIN TIMELINE
          </Typography>
          
          <AttackPathTimeline steps={path.steps} projectSlug={projectSlug} />
        </Box>
      </Collapse>
    </Box>
  );
};

// ─── Empty state ──────────────────────────────────────────────────────────────
const EmptyState: React.FC = () => {
  const { tokens } = useThemeTokens();
  return (
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
    <GitBranch size={48} color={tokens.accent.primary} />
    <Box>
      <Typography sx={{ fontSize: '0.9rem', fontWeight: 800, color: 'text.primary', mb: 0.5 }}>
        No Attack Paths Found
      </Typography>
      <Typography sx={{ fontSize: '0.75rem', color: 'text.secondary', maxWidth: 320, mx: 'auto' }}>
        The Attack Path Modeling Engine (APME) runs automatically after vulnerability scanning.
        No exploitable paths were detected for this scan.
      </Typography>
    </Box>
  </Box>
);
};

// ─── Main Tab ─────────────────────────────────────────────────────────────────
interface AttackPathsTabProps {
  scanId: number;
}

export const AttackPathsTab: React.FC<AttackPathsTabProps> = ({ scanId }) => {
  const { tokens } = useThemeTokens();
  const { data, isLoading, isError, refetch } = useAttackPaths(scanId);
  const triggerAi = useTriggerAttackPathModeling();
  const recalculatePaths = useRecalculateAttackPaths();
  const { projectSlug } = useParams({ strict: false });

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

  const handleRecalculatePaths = async () => {
    try {
      await recalculatePaths.mutateAsync(scanId);
      setSnackbar({ open: true, message: 'Recalculation initiated in background', severity: 'success' });
      // Refresh after a delay
      setTimeout(refetch, 5000);
    } catch {
      setSnackbar({ open: true, message: 'Failed to trigger recalculation', severity: 'error' });
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
            onClick={handleRecalculatePaths}
            disabled={recalculatePaths.isPending}
            startIcon={recalculatePaths.isPending ? <CircularProgress size={12} /> : <GitBranch size={14} />}
            sx={{
              fontSize: '0.6rem',
              height: 24,
              borderColor: `${tokens.accent.primary}4D`,
              color: tokens.accent.primary,
              fontFamily: 'Orbitron',
              '&:hover': {
                borderColor: tokens.accent.primary,
                bgcolor: `${tokens.accent.primary}0D`,
              },
            }}
          >
            {recalculatePaths.isPending ? 'RECALCULATING...' : 'RE-CALCULATE PATHS'}
          </Button>
          <Button
            size="small"
            variant="outlined"
            onClick={handleTriggerAi}
            disabled={triggerAi.isPending}
            startIcon={triggerAi.isPending ? <CircularProgress size={12} /> : <Bot size={14} />}
            sx={{
              fontSize: '0.6rem',
              height: 24,
              borderColor: `${tokens.accent.primary}4D`,
              color: tokens.accent.primary,
              fontFamily: 'Orbitron',
              '&:hover': {
                borderColor: tokens.accent.primary,
                bgcolor: `${tokens.accent.primary}0D`,
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
            border: 1, borderColor: 'divider',
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
            <CircularProgress size={32} sx={{ color: tokens.accent.primary }} />
            <Typography sx={{ mt: 2, fontSize: '0.75rem', color: 'text.secondary' }}>
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
                <AttackPathCard key={path.path_id} path={path} rank={i} projectSlug={projectSlug} />
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
            bgcolor: snackbar.severity === 'success' ? `${tokens.accent.primary}E6` : 'rgba(255, 0, 85, 0.9)',
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
