import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Switch,
  IconButton,
  Chip,
  Avatar,
  Button,
  CircularProgress,
  Snackbar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  Divider,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Delete as DeleteIcon,
  Download as InstallIcon,
  Check as InstalledIcon,
  Close as CloseIcon,
  VerifiedUser as VerifiedIcon,
  GppMaybe as SignedUnknownIcon,
  GppBad as UnverifiedIcon,
} from '@mui/icons-material';
import type { Plugin, MarketplacePlugin } from '../api/pluginsApi';
import {
  useTogglePlugin,
  useDeletePlugin,
  useInstallMarketplacePlugin,
  useRestartOrchestrator
} from '../api/pluginsApi';
import { ConfirmDialog } from '../../../components/ConfirmDialog';

interface Props {
  plugin?: Plugin;
  marketplacePlugin?: MarketplacePlugin;
}

// ── Trust badge ───────────────────────────────────────────────────────────────

const TRUST_CONFIG = {
  official:       { label: 'VERIFIED',   color: '#00ff62', bg: 'rgba(0,255,98,0.1)',  border: 'rgba(0,255,98,0.25)',  Icon: VerifiedIcon },
  signed_unknown: { label: 'SIGNED',     color: '#ff9800', bg: 'rgba(255,152,0,0.1)', border: 'rgba(255,152,0,0.25)', Icon: SignedUnknownIcon },
  unsigned:       { label: 'UNVERIFIED', color: '#9e9e9e', bg: 'rgba(158,158,158,0.08)', border: 'rgba(158,158,158,0.2)', Icon: UnverifiedIcon },
  legacy:         { label: 'LEGACY',     color: '#9e9e9e', bg: 'rgba(158,158,158,0.08)', border: 'rgba(158,158,158,0.2)', Icon: UnverifiedIcon },
};

const TrustBadge: React.FC<{ trustLevel: Plugin['trust_level'] }> = ({ trustLevel }) => {
  const cfg = TRUST_CONFIG[trustLevel] ?? TRUST_CONFIG.unsigned;
  return (
    <Chip
      icon={<cfg.Icon sx={{ fontSize: '12px !important', color: `${cfg.color} !important` }} />}
      label={cfg.label}
      size="small"
      sx={{
        bgcolor: cfg.bg,
        color: cfg.color,
        border: `1px solid ${cfg.border}`,
        fontSize: '9px',
        fontWeight: 900,
        fontFamily: 'Orbitron',
        height: '20px',
      }}
    />
  );
};

// ── Details modal ─────────────────────────────────────────────────────────────

const SectionLabel: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Typography sx={{ fontFamily: 'Orbitron', fontSize: '0.6rem', fontWeight: 900, letterSpacing: 2, color: '#00f3ff', mb: 0.75, textTransform: 'uppercase' }}>
    {children}
  </Typography>
);

const KV: React.FC<{ label: string; value?: React.ReactNode }> = ({ label, value }) => (
  value != null && value !== '' ? (
    <Box sx={{ display: 'flex', gap: 1.5, mb: 0.5 }}>
      <Typography sx={{ fontFamily: 'monospace', fontSize: '0.68rem', color: 'rgba(255,255,255,0.35)', minWidth: 100, flexShrink: 0 }}>{label}</Typography>
      <Typography sx={{ fontFamily: 'monospace', fontSize: '0.68rem', color: 'rgba(255,255,255,0.75)', wordBreak: 'break-all' }}>{value}</Typography>
    </Box>
  ) : null
);

interface DetailsModalProps {
  open: boolean;
  onClose: () => void;
  plugin: Plugin;
}

const PluginDetailsModal: React.FC<DetailsModalProps> = ({ open, onClose, plugin }) => {
  const trustCfg = TRUST_CONFIG[plugin.trust_level] ?? TRUST_CONFIG.unsigned;
  const tools: Record<string, any> = plugin.tools_config ?? {};
  const manifest: Record<string, any> = plugin.manifest ?? {};
  const runtime = manifest.runtime ?? {};

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            background: 'linear-gradient(145deg, rgba(8,8,18,0.98) 0%, rgba(12,12,22,0.99) 100%)',
            border: '1px solid rgba(0,243,255,0.15)',
            borderRadius: '16px',
            color: '#fff',
          }
        }
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Avatar variant="rounded" sx={{ bgcolor: '#0076FF', width: 36, height: 36, fontSize: '1rem', color: '#000' }}>
              {plugin.name[0]}
            </Avatar>
            <Box>
              <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 900, fontSize: '0.85rem', color: '#fff' }}>
                {plugin.name}
              </Typography>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.35)', fontFamily: 'monospace' }}>
                v{plugin.version}{plugin.author ? ` · ${plugin.author}` : ''}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              label={trustCfg.label}
              size="small"
              sx={{ bgcolor: trustCfg.bg, color: trustCfg.color, border: `1px solid ${trustCfg.border}`, fontSize: '9px', fontWeight: 900, fontFamily: 'Orbitron' }}
            />
            <IconButton size="small" onClick={onClose} sx={{ color: 'rgba(255,255,255,0.4)' }}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent dividers sx={{ borderColor: 'rgba(255,255,255,0.07)', pt: 2 }}>
        {/* Plugin info */}
        <SectionLabel>Details</SectionLabel>
        <KV label="Slug" value={plugin.slug} />
        <KV label="Anchor step" value={plugin.anchor_step} />
        <KV label="Position" value={plugin.runtime_position} />
        <KV label="Installed" value={plugin.installed_at ? new Date(plugin.installed_at).toLocaleString() : undefined} />
        {plugin.description && (
          <Typography sx={{ fontFamily: 'monospace', fontSize: '0.68rem', color: 'rgba(255,255,255,0.55)', mt: 0.75, lineHeight: 1.6 }}>
            {plugin.description}
          </Typography>
        )}

        {/* Runtime */}
        {Object.keys(runtime).length > 0 && (
          <>
            <Divider sx={{ my: 2, borderColor: 'rgba(255,255,255,0.07)' }} />
            <SectionLabel>Runtime</SectionLabel>
            {Object.entries(runtime).map(([k, v]) => (
              <KV key={k} label={k} value={String(v)} />
            ))}
          </>
        )}

        {/* Tools */}
        {Object.keys(tools).length > 0 && (
          <>
            <Divider sx={{ my: 2, borderColor: 'rgba(255,255,255,0.07)' }} />
            <SectionLabel>Tools</SectionLabel>
            {Array.isArray(tools.tools) ? (
              tools.tools.map((t: any, i: number) => (
                <Box key={i} sx={{ mb: 1, p: 1, bgcolor: 'rgba(0,243,255,0.04)', border: '1px solid rgba(0,243,255,0.08)', borderRadius: 1 }}>
                  <Typography sx={{ fontFamily: 'monospace', fontSize: '0.68rem', fontWeight: 700, color: '#00f3ff' }}>
                    {t.name ?? `Tool ${i + 1}`}
                  </Typography>
                  {t.version && <KV label="version" value={t.version} />}
                  {t.source && <KV label="source" value={t.source} />}
                  {t.description && (
                    <Typography sx={{ fontFamily: 'monospace', fontSize: '0.62rem', color: 'rgba(255,255,255,0.45)', mt: 0.25 }}>
                      {t.description}
                    </Typography>
                  )}
                </Box>
              ))
            ) : (
              <Box
                component="pre"
                sx={{
                  fontFamily: 'monospace',
                  fontSize: '0.62rem',
                  color: 'rgba(255,255,255,0.55)',
                  bgcolor: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderRadius: 1,
                  p: 1.5,
                  m: 0,
                  overflowX: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                }}
              >
                {JSON.stringify(tools, null, 2)}
              </Box>
            )}
          </>
        )}

        {/* Full manifest */}
        <Divider sx={{ my: 2, borderColor: 'rgba(255,255,255,0.07)' }} />
        <SectionLabel>Manifest</SectionLabel>
        <Box
          component="pre"
          sx={{
            fontFamily: 'monospace',
            fontSize: '0.62rem',
            color: 'rgba(255,255,255,0.5)',
            bgcolor: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 1,
            p: 1.5,
            m: 0,
            overflowX: 'auto',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}
        >
          {JSON.stringify(manifest, null, 2)}
        </Box>
      </DialogContent>
    </Dialog>
  );
};

// ── Main card ─────────────────────────────────────────────────────────────────

const PluginCard: React.FC<Props> = ({ plugin, marketplacePlugin }) => {
  const toggleMutation = useTogglePlugin();
  const deleteMutation = useDeletePlugin();
  const installMutation = useInstallMarketplacePlugin();
  const restartMutation = useRestartOrchestrator();
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = React.useState(false);
  const [isRestartDialogOpen, setIsRestartDialogOpen] = React.useState(false);
  const [isDetailsOpen, setIsDetailsOpen] = React.useState(false);
  const [restartSnackbar, setRestartSnackbar] = React.useState(false);

  const handleRestart = () => {
    restartMutation.mutate(undefined, {
      onSuccess: () => {
        setIsRestartDialogOpen(false);
        setRestartSnackbar(true);
      }
    });
  };

  const data = plugin || marketplacePlugin;
  const isMarketplace = !!marketplacePlugin && !plugin;
  const isInstalled = !!plugin || (marketplacePlugin?.is_installed);

  if (!data) return null;

  const handleToggle = () => {
    if (plugin) {
      toggleMutation.mutate({ slug: plugin.slug, is_enabled: !plugin.is_enabled });
    }
  };

  const handleDelete = () => {
    if (plugin) {
      deleteMutation.mutate(plugin.slug, {
        onSuccess: () => setIsDeleteDialogOpen(false)
      });
    }
  };

  const handleInstall = () => {
    if (marketplacePlugin) {
      installMutation.mutate(marketplacePlugin.slug);
    }
  };

  return (
    <>
      <Card sx={{
        borderRadius: '16px',
        background: 'rgba(20, 20, 20, 0.4)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        transition: '0.3s',
        '&:hover': {
          borderColor: isMarketplace && !isInstalled ? '#00ffaa' : '#0076FF',
          boxShadow: `0 0 20px ${isMarketplace && !isInstalled ? 'rgba(0, 255, 170, 0.2)' : 'rgba(0, 118, 255, 0.2)'}`
        }
      }}>
        <CardContent>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 2 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <Avatar
                variant="rounded"
                sx={{ bgcolor: isMarketplace && !isInstalled ? '#00ffaa' : '#0076FF', width: 48, height: 48, color: '#000' }}
              >
                {data.name[0]}
              </Avatar>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: "bold", color: '#fff', minHeight: '3.1em', lineHeight: 1.235, display: 'flex', alignItems: 'flex-start' }}>{data.name}</Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flexWrap: 'wrap' }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>v{data.version}</Typography>
                  {data.author && (
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.62rem' }}>· {data.author}</Typography>
                  )}
                </Box>
              </Box>
            </Box>

            {isMarketplace ? (
              isInstalled ? (
                <Chip
                  icon={<InstalledIcon sx={{ fontSize: '14px !important' }} />}
                  label="INSTALLED"
                  size="small"
                  sx={{ bgcolor: 'rgba(0, 255, 170, 0.1)', color: '#00ffaa', border: '1px solid rgba(0, 255, 170, 0.2)', fontSize: '10px', fontWeight: 900, fontFamily: 'Orbitron' }}
                />
              ) : (
                <Button
                  size="small"
                  variant="contained"
                  startIcon={installMutation.isPending ? <CircularProgress size={12} color="inherit" /> : <InstallIcon />}
                  onClick={handleInstall}
                  disabled={installMutation.isPending}
                  sx={{
                    bgcolor: '#00ffaa',
                    color: '#000',
                    fontFamily: 'Orbitron',
                    fontWeight: 900,
                    fontSize: '10px',
                    '&:hover': { bgcolor: '#00d890' }
                  }}
                >
                  INSTALL
                </Button>
              )
            ) : (
              <Switch
                checked={plugin?.is_enabled}
                onChange={handleToggle}
                color="primary"
                disabled={toggleMutation.isPending}
              />
            )}
          </Box>

          <Typography variant="body2" sx={{
            color: 'rgba(255,255,255,0.6)',
            height: '40px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            mb: 2
          }}>
            {data.description || 'No description provided.'}
          </Typography>

          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flexWrap: 'wrap' }}>
              <Chip
                label={plugin?.anchor_step || marketplacePlugin?.category || 'General'}
                size="small"
                variant="outlined"
                sx={{ borderColor: 'rgba(255, 255, 255, 0.1)', color: 'rgba(255,255,255,0.4)', fontSize: '10px' }}
              />
              {plugin?.trust_level && (
                <TrustBadge trustLevel={plugin.trust_level} />
              )}
            </Box>

            {!isMarketplace && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {plugin?.needs_restart && plugin?.is_enabled && (
                  <Button
                    size="small"
                    variant="outlined"
                    color="warning"
                    onClick={() => setIsRestartDialogOpen(true)}
                    sx={{
                      fontSize: '10px',
                      fontFamily: 'Orbitron',
                      fontWeight: 900,
                      color: '#ff9800',
                      borderColor: 'rgba(255, 152, 0, 0.5)',
                      px: 1.5,
                      py: 0.5,
                      minWidth: 'auto',
                      height: '24px',
                      '&:hover': {
                        borderColor: '#ff9800',
                        bgcolor: 'rgba(255, 152, 0, 0.05)'
                      }
                    }}
                  >
                    RESTART
                  </Button>
                )}
                <IconButton
                  size="small"
                  sx={{ color: 'rgba(255,255,255,0.3)', '&:hover': { color: '#00f3ff' } }}
                  onClick={() => setIsDetailsOpen(true)}
                >
                  <SettingsIcon fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  sx={{ color: '#ff003c' }}
                  onClick={() => setIsDeleteDialogOpen(true)}
                  disabled={deleteMutation.isPending}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>

      {plugin && (
        <PluginDetailsModal
          open={isDetailsOpen}
          onClose={() => setIsDetailsOpen(false)}
          plugin={plugin}
        />
      )}

      <ConfirmDialog
        open={isDeleteDialogOpen}
        onClose={() => setIsDeleteDialogOpen(false)}
        onConfirm={handleDelete}
        title="Delete Plugin"
        message={`Are you sure you want to delete the plugin "${plugin?.name}"? This action is irreversible and will remove all associated files and UI components.`}
        confirmText="DELETE PLUGIN"
        isDestructive={true}
        isLoading={deleteMutation.isPending}
      />

      <ConfirmDialog
        open={isRestartDialogOpen}
        onClose={() => setIsRestartDialogOpen(false)}
        onConfirm={handleRestart}
        title="Restart Orchestrator"
        message={`The orchestrator container needs to be restarted to load and register the workflow/activity changes for "${plugin?.name}". You can restart it manually via your CLI, or click "RESTART NOW" to automatically restart the container now.`}
        confirmText="RESTART NOW"
        cancelText="RESTART LATER"
        isDestructive={false}
        type="warning"
        isLoading={restartMutation.isPending}
      />

      <Snackbar
        open={restartSnackbar}
        autoHideDuration={6000}
        onClose={() => setRestartSnackbar(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setRestartSnackbar(false)}
          severity="success"
          variant="filled"
          sx={{
            fontFamily: 'Orbitron',
            fontWeight: 800,
            bgcolor: '#00f3ff',
            color: '#000',
            borderRadius: 0
          }}
        >
          Orchestrator restart initiated. The container will reload in a few seconds.
        </Alert>
      </Snackbar>
    </>
  );
};

export default PluginCard;
