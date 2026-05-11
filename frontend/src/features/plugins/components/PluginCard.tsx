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
  CircularProgress
} from '@mui/material';
import { 
  Settings as SettingsIcon, 
  Delete as DeleteIcon,
  Download as InstallIcon,
  Check as InstalledIcon
} from '@mui/icons-material';
import type { Plugin, MarketplacePlugin } from '../api/pluginsApi';
import { useTogglePlugin, useDeletePlugin, useInstallMarketplacePlugin } from '../api/pluginsApi';
import { ConfirmDialog } from '../../../components/ConfirmDialog';

interface Props {
  plugin?: Plugin;
  marketplacePlugin?: MarketplacePlugin;
}

const PluginCard: React.FC<Props> = ({ plugin, marketplacePlugin }) => {
  const toggleMutation = useTogglePlugin();
  const deleteMutation = useDeletePlugin();
  const installMutation = useInstallMarketplacePlugin();
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = React.useState(false);

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
                <Typography variant="h6" sx={{ fontWeight: "bold", color: '#fff' }}>{data.name}</Typography>
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
              <Box>
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
    </>
  );
};

export default PluginCard;
