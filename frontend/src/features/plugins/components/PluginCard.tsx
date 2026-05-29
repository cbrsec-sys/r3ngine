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
  Alert
} from '@mui/material';
import { 
  Settings as SettingsIcon, 
  Delete as DeleteIcon,
  Download as InstallIcon,
  Check as InstalledIcon
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

const PluginCard: React.FC<Props> = ({ plugin, marketplacePlugin }) => {
  const toggleMutation = useTogglePlugin();
  const deleteMutation = useDeletePlugin();
  const installMutation = useInstallMarketplacePlugin();
  const restartMutation = useRestartOrchestrator();
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = React.useState(false);
  const [isRestartDialogOpen, setIsRestartDialogOpen] = React.useState(false);
  const [restartSnackbar, setRestartSnackbar] = React.useState(false);

  const handleRestart = () => {
    restartMutation.mutate(undefined, {
      onSuccess: () => {
        setIsRestartDialogOpen(false);
        setRestartSnackbar(true);
      }
    });
  };

  // If we have an installed plugin, use its data
  // Otherwise, if we have a marketplace plugin, use its data
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
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>v{data.version}</Typography>
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
            <Chip 
              label={plugin?.anchor_step || marketplacePlugin?.category || 'General'} 
              size="small" 
              variant="outlined" 
              sx={{ borderColor: 'rgba(255, 255, 255, 0.1)', color: 'rgba(255,255,255,0.4)', fontSize: '10px' }} 
            />
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
                <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.3)' }}>
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
