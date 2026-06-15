import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  Tooltip,
  Select,
  MenuItem,
  ToggleButtonGroup,
  ToggleButton,
  Chip,
  Divider,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  ChevronRight,
  GripVertical,
  Shield,
  Cpu,
  Layers,
  PlugZap,
  ArrowDownToLine,
  ArrowUpToLine,
  Settings2,
} from 'lucide-react';
import type { Plugin } from '../api/pluginsApi';
import { useUpdatePluginWeight, useUpdatePluginPosition } from '../api/pluginsApi';

// ── Pipeline stage definitions ───────────────────────────────────────────────
// Each stage maps to the core scan tiers. `anchors` lists every anchor_step
// value that places a plugin at this stage.

interface PipelineStage {
  key: string;
  label: string;
  tier: number;
  description: string;
  anchors: string[];
}

const PIPELINE_STAGES: PipelineStage[] = [
  {
    key: 'tier_1',
    label: 'Subdomain Discovery',
    tier: 1,
    description: 'amass, subfinder, DNS, OSINT, firewall detection',
    anchors: ['tier_1'],
  },
  {
    key: 'tier_2',
    label: 'Port Scan & HTTP Crawl',
    tier: 2,
    description: 'naabu, httpx, vigolium discovery',
    anchors: ['tier_2'],
  },
  {
    key: 'tier_3',
    label: 'URL Fetching & Screenshot',
    tier: 3,
    description: 'gau, waybackurls, gowitness',
    anchors: ['tier_3'],
  },
  {
    key: 'tier_4',
    label: 'Directory & Param Fuzzing',
    tier: 4,
    description: 'ffuf, katana, ParamSpider, LinkFinder',
    anchors: ['tier_4'],
  },
  {
    key: 'tier_5',
    label: 'Web API & Secret Scan',
    tier: 5,
    description: 'kiterunner, arjun, gitleaks, WAF detection',
    anchors: ['tier_5'],
  },
  {
    key: 'tier_6',
    label: 'Vulnerability Scan',
    tier: 6,
    description: 'nuclei, vigolium scan, WAF bypass, brute force',
    anchors: ['tier_6'],
  },
  {
    key: 'tier_7',
    label: 'Correlation & Reporting',
    tier: 7,
    description: 'Neo4j APME, risk scoring, CVE correlation',
    anchors: ['tier_7'],
  },
];

// ── Plugin categorisation ────────────────────────────────────────────────────

function findStage(plugin: Plugin): PipelineStage | null {
  if (!plugin.anchor_step) return null;
  const step = plugin.anchor_step.toLowerCase().trim();
  if (step === 'standalone' || step === 'any' || step === '') return null;
  return (
    PIPELINE_STAGES.find(
      (s) => s.key === step || s.anchors.includes(step)
    ) ?? null
  );
}

type PluginCategory = 'positioned' | 'configurable' | 'standalone';

function categorise(plugin: Plugin): PluginCategory {
  if (!plugin.anchor_step || plugin.anchor_step === 'standalone' || plugin.anchor_step === '') {
    return 'standalone';
  }
  if (plugin.anchor_step === 'any') return 'configurable';
  return findStage(plugin) ? 'positioned' : 'standalone';
}

// ── Positioned plugin card (draggable, shown inline on the timeline) ─────────

const PositionedPluginCard: React.FC<{ plugin: Plugin }> = ({ plugin }) => {
  const theme = useTheme();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: plugin.slug });

  const isAfter = plugin.runtime_position === 'AFTER';

  return (
    <Box
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, zIndex: isDragging ? 100 : 1 }}
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        px: 1.5,
        py: 1,
        bgcolor: isDragging ? alpha(theme.palette.primary.main, 0.12) : alpha(theme.palette.primary.main, 0.04),
        border: '1px solid',
        borderColor: isDragging ? theme.palette.primary.main : alpha(theme.palette.primary.main, 0.15),
        borderRadius: '4px',
        mb: 0.75,
        opacity: plugin.is_enabled ? 1 : 0.45,
        transition: 'all 0.15s',
        '&:hover': { borderColor: alpha(theme.palette.primary.main, 0.35), bgcolor: alpha(theme.palette.primary.main, 0.08) },
      }}
    >
      <Box {...attributes} {...listeners} sx={{ cursor: 'grab', color: 'rgba(255,255,255,0.2)', display: 'flex', flexShrink: 0 }}>
        <GripVertical size={14} />
      </Box>

      <Box sx={{ color: isAfter ? theme.palette.primary.main : theme.palette.warning.main, flexShrink: 0 }}>
        {isAfter ? <ArrowDownToLine size={13} /> : <ArrowUpToLine size={13} />}
      </Box>

      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography
          noWrap
          sx={{ fontFamily: 'Orbitron', fontWeight: 800, fontSize: '0.68rem', color: '#fff', letterSpacing: 0.5 }}
        >
          {plugin.name.toUpperCase()}
        </Typography>
        <Typography sx={{ fontSize: '0.58rem', color: 'rgba(255,255,255,0.35)', fontWeight: 500 }}>
          v{plugin.version}
        </Typography>
      </Box>

      <Chip
        label={isAfter ? 'AFTER' : 'BEFORE'}
        size="small"
        sx={{
          height: 16,
          fontSize: '0.5rem',
          fontFamily: 'Orbitron',
          fontWeight: 900,
          letterSpacing: 0.5,
          bgcolor: alpha(isAfter ? theme.palette.primary.main : theme.palette.warning.main, 0.1),
          color: isAfter ? theme.palette.primary.main : theme.palette.warning.main,
          border: `1px solid ${alpha(isAfter ? theme.palette.primary.main : theme.palette.warning.main, 0.3)}`,
          '& .MuiChip-label': { px: 0.75 },
        }}
      />

      {!plugin.is_enabled && (
        <Chip
          label="OFF"
          size="small"
          sx={{
            height: 16, fontSize: '0.5rem', fontFamily: 'Orbitron', fontWeight: 900,
            bgcolor: 'rgba(255,0,60,0.08)', color: 'rgba(255,0,60,0.6)',
            border: '1px solid rgba(255,0,60,0.2)', '& .MuiChip-label': { px: 0.75 },
          }}
        />
      )}
    </Box>
  );
};

// ── Standalone plugin card (right column, no pipeline position) ──────────────

const StandalonePluginCard: React.FC<{ plugin: Plugin }> = ({ plugin }) => {
  const theme = useTheme();
  return (
    <Box
      sx={{
        p: 1.5,
        mb: 1.25,
        bgcolor: alpha(theme.palette.secondary.main, 0.04),
        border: `1px solid ${alpha(theme.palette.secondary.main, 0.15)}`,
        borderRadius: '6px',
        opacity: plugin.is_enabled ? 1 : 0.45,
        '&:hover': { borderColor: alpha(theme.palette.secondary.main, 0.35), bgcolor: alpha(theme.palette.secondary.main, 0.08) },
        transition: 'all 0.15s',
      }}
    >
      <Stack direction="row" spacing={1.25} sx={{ alignItems: 'flex-start' }}>
        <Box sx={{ color: theme.palette.secondary.main, flexShrink: 0, mt: '2px' }}>
          <PlugZap size={15} />
        </Box>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            noWrap
            sx={{ fontFamily: 'Orbitron', fontWeight: 800, fontSize: '0.7rem', color: '#fff', letterSpacing: 0.5 }}
          >
            {plugin.name.toUpperCase()}
          </Typography>
          <Typography sx={{ fontSize: '0.58rem', color: 'rgba(255,255,255,0.35)', fontWeight: 500 }}>
            v{plugin.version} · {plugin.author}
          </Typography>
          {plugin.description && (
            <Typography
              sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', mt: 0.5, lineHeight: 1.4 }}
              noWrap
            >
              {plugin.description}
            </Typography>
          )}
        </Box>
        <Chip
          label="STANDALONE"
          size="small"
          sx={{
            height: 16, fontSize: '0.48rem', fontFamily: 'Orbitron', fontWeight: 900, flexShrink: 0,
            bgcolor: alpha(theme.palette.secondary.main, 0.1), color: theme.palette.secondary.main,
            border: `1px solid ${alpha(theme.palette.secondary.main, 0.3)}`, '& .MuiChip-label': { px: 0.75 },
          }}
        />
      </Stack>
    </Box>
  );
};

// ── Configurable plugin card (right column, user-settable position) ──────────

const ConfigurablePluginCard: React.FC<{ plugin: Plugin }> = ({ plugin }) => {
  const theme = useTheme();
  const updatePosition = useUpdatePluginPosition();

  const [selectedStage, setSelectedStage] = useState(plugin.anchor_step || '');
  const [selectedPos, setSelectedPos] = useState<'BEFORE' | 'AFTER'>(plugin.runtime_position ?? 'AFTER');

  const handleSave = (stage: string, pos: 'BEFORE' | 'AFTER') => {
    if (!stage) return;
    updatePosition.mutate({ slug: plugin.slug, anchor_step: stage, runtime_position: pos });
  };

  return (
    <Box
      sx={{
        p: 1.5,
        mb: 1.25,
        bgcolor: alpha(theme.palette.primary.main, 0.03),
        border: `1px solid ${alpha(theme.palette.primary.main, 0.15)}`,
        borderRadius: '6px',
        opacity: plugin.is_enabled ? 1 : 0.45,
      }}
    >
      <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center', mb: 1 }}>
        <Box sx={{ color: theme.palette.primary.main, flexShrink: 0 }}>
          <Settings2 size={14} />
        </Box>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography noWrap sx={{ fontFamily: 'Orbitron', fontWeight: 800, fontSize: '0.7rem', color: '#fff', letterSpacing: 0.5 }}>
            {plugin.name.toUpperCase()}
          </Typography>
          <Typography sx={{ fontSize: '0.58rem', color: 'rgba(255,255,255,0.35)' }}>
            v{plugin.version}
          </Typography>
        </Box>
        <Chip
          label="CONFIGURABLE"
          size="small"
          sx={{
            height: 16, fontSize: '0.48rem', fontFamily: 'Orbitron', fontWeight: 900, flexShrink: 0,
            bgcolor: alpha(theme.palette.primary.main, 0.08), color: theme.palette.primary.main,
            border: `1px solid ${alpha(theme.palette.primary.main, 0.25)}`, '& .MuiChip-label': { px: 0.75 },
          }}
        />
      </Stack>

      <Typography sx={{ fontSize: '0.58rem', color: 'rgba(255,255,255,0.4)', mb: 0.75, fontWeight: 600 }}>
        INJECT AT PIPELINE STAGE:
      </Typography>

      <Select
        size="small"
        fullWidth
        value={selectedStage}
        onChange={(e) => {
          setSelectedStage(e.target.value);
          handleSave(e.target.value, selectedPos);
        }}
        sx={{
          mb: 1,
          fontSize: '0.65rem',
          fontFamily: 'Orbitron',
          color: '#fff',
          bgcolor: 'rgba(255,255,255,0.03)',
          '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1)' },
          '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: alpha(theme.palette.primary.main, 0.3) },
          '.MuiSelect-icon': { color: 'rgba(255,255,255,0.4)' },
        }}
        MenuProps={{
          slotProps: {
            paper: {
              sx: { bgcolor: theme.palette.background.paper, border: `1px solid ${alpha(theme.palette.primary.main, 0.15)}`, color: theme.palette.common.white },
            },
          },
        }}
      >
        <MenuItem value="" sx={{ fontSize: '0.65rem', fontFamily: 'Orbitron', color: 'rgba(255,255,255,0.4)' }}>
          — SELECT STAGE —
        </MenuItem>
        {PIPELINE_STAGES.map((s) => (
          <MenuItem key={s.key} value={s.key} sx={{ fontSize: '0.65rem', fontFamily: 'Orbitron' }}>
            T{s.tier} — {s.label.toUpperCase()}
          </MenuItem>
        ))}
      </Select>

      <ToggleButtonGroup
        size="small"
        exclusive
        value={selectedPos}
        onChange={(_, val) => {
          if (!val) return;
          setSelectedPos(val);
          handleSave(selectedStage, val);
        }}
        sx={{ width: '100%' }}
      >
        {(['BEFORE', 'AFTER'] as const).map((pos) => (
          <ToggleButton
            key={pos}
            value={pos}
            sx={{
              flex: 1,
              fontSize: '0.55rem',
              fontFamily: 'Orbitron',
              fontWeight: 900,
              letterSpacing: 0.8,
              py: 0.4,
              color: 'rgba(255,255,255,0.4)',
              borderColor: 'rgba(255,255,255,0.08)',
              '&.Mui-selected': {
                color: pos === 'AFTER' ? theme.palette.primary.main : theme.palette.warning.main,
                bgcolor: pos === 'AFTER' ? alpha(theme.palette.primary.main, 0.1) : alpha(theme.palette.warning.main, 0.1),
                borderColor: pos === 'AFTER' ? alpha(theme.palette.primary.main, 0.3) : alpha(theme.palette.warning.main, 0.3),
              },
            }}
          >
            {pos}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </Box>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  plugins: Plugin[];
}

const PipelineBuilder: React.FC<Props> = ({ plugins }) => {
  const theme = useTheme();
  const updateWeightMutation = useUpdatePluginWeight();

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  if (!Array.isArray(plugins)) return null;

  const positionedPlugins = plugins.filter((p) => categorise(p) === 'positioned');
  const standalonePlugins = plugins.filter((p) => categorise(p) === 'standalone');
  const configurablePlugins = plugins.filter((p) => categorise(p) === 'configurable');

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    // Find both plugins and compute new order_weight
    const activePlugin = plugins.find((p) => p.slug === active.id);
    const overPlugin = plugins.find((p) => p.slug === over.id);
    if (activePlugin && overPlugin) {
      updateWeightMutation.mutate({ slug: activePlugin.slug, order_weight: overPlugin.order_weight });
    }
  };

  return (
    <Box sx={{ display: 'flex', gap: 4, alignItems: 'flex-start' }}>
      {/* ── Left column: pipeline timeline ─────────────────────────────── */}
      <Box sx={{ flex: '1 1 0', minWidth: 0 }}>
        {/* Header */}
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', mb: 4 }}>
          <Cpu size={20} color={theme.palette.primary.main} />
          <Box>
            <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 900, letterSpacing: 1, color: '#fff', fontSize: '1.1rem' }}>
              EXECUTION PIPELINE
            </Typography>
            <Typography sx={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.4)', fontWeight: 600 }}>
              SEQUENTIAL ORCHESTRATION OF CORE ENGINES AND PLUGIN EXTENSIONS
            </Typography>
          </Box>
        </Stack>

        <Box sx={{ position: 'relative', pl: 6 }}>
          {/* Vertical connector line */}
          <Box sx={{
            position: 'absolute', left: '24px', top: 0, bottom: 0, width: '2px',
            bgcolor: 'rgba(255,255,255,0.04)',
            '&::after': {
              content: '""', position: 'absolute', top: 0, bottom: 0, left: 0, right: 0,
              background: `linear-gradient(to bottom, ${theme.palette.primary.main} 0%, transparent 100%)`, opacity: 0.25,
            },
          }} />

          {PIPELINE_STAGES.map((stage, idx) => {
            const pluginsBefore = positionedPlugins
              .filter((p) => findStage(p)?.key === stage.key && p.runtime_position === 'BEFORE')
              .sort((a, b) => a.order_weight - b.order_weight);

            const pluginsAfter = positionedPlugins
              .filter((p) => findStage(p)?.key === stage.key && p.runtime_position === 'AFTER')
              .sort((a, b) => a.order_weight - b.order_weight);

            const hasPlugins = pluginsAfter.length > 0 || pluginsBefore.length > 0;

            return (
              <Box key={stage.key} sx={{ mb: 5, position: 'relative' }}>
                {/* Tier number */}
                <Box sx={{ position: 'absolute', left: '-56px', top: '2px', width: '28px', textAlign: 'right' }}>
                  <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 900, color: 'rgba(255,255,255,0.08)', fontSize: '1.4rem', lineHeight: 1 }}>
                    {(idx + 1).toString().padStart(2, '0')}
                  </Typography>
                </Box>

                {/* BEFORE plugins */}
                {pluginsBefore.length > 0 && (
                  <Box sx={{ mb: 1.5, ml: 1 }}>
                    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                      <SortableContext items={pluginsBefore.map((p) => p.slug)} strategy={verticalListSortingStrategy}>
                        {pluginsBefore.map((p) => <PositionedPluginCard key={p.slug} plugin={p} />)}
                      </SortableContext>
                    </DndContext>
                  </Box>
                )}

                {/* Core step node */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                  {/* Diamond node on line */}
                  <Box sx={{
                    width: 11, height: 11, borderRadius: 0,
                    bgcolor: hasPlugins ? theme.palette.primary.main : alpha(theme.palette.primary.main, 0.7),
                    boxShadow: `0 0 8px ${hasPlugins ? theme.palette.primary.main : alpha(theme.palette.primary.main, 0.7)}`,
                    position: 'absolute', left: '-28px', zIndex: 2, transform: 'rotate(45deg)',
                  }} />

                  <Paper sx={{
                    p: 2, flexGrow: 1,
                    bgcolor: alpha(theme.palette.primary.main, 0.025),
                    border: `1px solid ${alpha(theme.palette.primary.main, 0.08)}`,
                    borderLeft: `3px solid ${alpha(theme.palette.primary.main, 0.6)}`,
                    borderRadius: '2px',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    position: 'relative', overflow: 'hidden',
                  }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                      <Chip
                        label={`TIER ${stage.tier}`}
                        size="small"
                        sx={{
                          height: 16,
                          fontSize: '0.5rem',
                          fontFamily: 'Orbitron',
                          fontWeight: 900,
                          letterSpacing: 0.5,
                          bgcolor: alpha(theme.palette.primary.main, 0.1),
                          color: theme.palette.primary.main,
                          border: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
                          '& .MuiChip-label': { px: 0.75 },
                          mr: 1,
                          flexShrink: 0,
                        }}
                      />
                      <Box>
                        <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 900, letterSpacing: 1, color: '#fff', fontSize: '0.85rem' }}>
                          {stage.label.toUpperCase()}
                        </Typography>
                        <Typography sx={{ fontSize: '0.6rem', color: alpha(theme.palette.primary.main, 0.45), fontWeight: 700, letterSpacing: 0.4, mt: 0.25 }}>
                          {stage.description}
                        </Typography>
                      </Box>
                    </Box>
                    <Tooltip title="System Core Engine">
                      <Shield size={18} color={alpha(theme.palette.primary.main, 0.15)} />
                    </Tooltip>
                  </Paper>
                </Box>

                {/* AFTER plugins */}
                {pluginsAfter.length > 0 && (
                  <Box sx={{ mt: 1.5, ml: 1 }}>
                    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                      <SortableContext items={pluginsAfter.map((p) => p.slug)} strategy={verticalListSortingStrategy}>
                        {pluginsAfter.map((p) => <PositionedPluginCard key={p.slug} plugin={p} />)}
                      </SortableContext>
                    </DndContext>
                  </Box>
                )}
              </Box>
            );
          })}

          {/* Pipeline end marker */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, ml: 1, opacity: 0.4, mt: 1 }}>
            <ChevronRight size={14} color="#fff" style={{ marginLeft: -10 }} />
            <Typography sx={{ fontFamily: 'Orbitron', fontSize: '0.58rem', fontWeight: 900, letterSpacing: 2, color: 'rgba(255,255,255,0.3)' }}>
              PIPELINE TERMINATED
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* ── Right column: standalone + configurable ─────────────────────── */}
      {(standalonePlugins.length > 0 || configurablePlugins.length > 0) && (
        <Box
          sx={{
            width: 280,
            flexShrink: 0,
            position: 'sticky',
            top: 24,
            alignSelf: 'flex-start',
          }}
        >
          {/* Configurable plugins */}
          {configurablePlugins.length > 0 && (
            <>
              <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 1.5 }}>
                <Settings2 size={14} color={theme.palette.primary.main} />
                <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 900, fontSize: '0.62rem', letterSpacing: 1.5, color: alpha(theme.palette.primary.main, 0.7) }}>
                  CONFIGURABLE INJECTION
                </Typography>
              </Stack>
              <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 1.5, lineHeight: 1.5 }}>
                These plugins have no fixed pipeline position. Select a stage to inject them.
              </Typography>
              {configurablePlugins.map((p) => (
                <ConfigurablePluginCard key={p.slug} plugin={p} />
              ))}
              {standalonePlugins.length > 0 && (
                <Divider sx={{ my: 2.5, borderColor: 'rgba(255,255,255,0.06)' }} />
              )}
            </>
          )}

          {/* Standalone plugins */}
          {standalonePlugins.length > 0 && (
            <>
              <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 1.5 }}>
                <Layers size={14} color={theme.palette.secondary.main} />
                <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 900, fontSize: '0.62rem', letterSpacing: 1.5, color: alpha(theme.palette.secondary.main, 0.7) }}>
                  STANDALONE PLUGINS
                </Typography>
              </Stack>
              <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 1.5, lineHeight: 1.5 }}>
                These plugins run independently and are not injected into the scan pipeline.
              </Typography>
              {standalonePlugins.map((p) => (
                <StandalonePluginCard key={p.slug} plugin={p} />
              ))}
            </>
          )}
        </Box>
      )}
    </Box>
  );
};

export default PipelineBuilder;
