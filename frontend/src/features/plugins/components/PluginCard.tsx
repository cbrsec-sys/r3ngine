import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  Switch, 
  IconButton, 
  Chip,
  Avatar
} from '@mui/material';
import { Settings as SettingsIcon, Delete as DeleteIcon } from '@mui/icons-material';
import type { Plugin } from '../api/pluginsApi';
import { useTogglePlugin, useDeletePlugin } from '../api/pluginsApi';

interface Props {
  plugin: Plugin;
}

const PluginCard: React.FC<Props> = ({ plugin }) => {
  const toggleMutation = useTogglePlugin();
  const deleteMutation = useDeletePlugin();

  const handleToggle = () => {
    toggleMutation.mutate({ slug: plugin.slug, is_enabled: !plugin.is_enabled });
  };

  const handleDelete = () => {
    if (window.confirm(`Are you sure you want to delete the plugin "${plugin.name}"? This will remove all associated files.`)) {
      deleteMutation.mutate(plugin.slug);
    }
  };

  return (
    <Card sx={{ 
      borderRadius: '16px', 
      background: 'rgba(20, 20, 20, 0.4)', 
      border: '1px solid rgba(255, 255, 255, 0.1)',
      transition: '0.3s',
      '&:hover': {
        borderColor: '#0076FF',
        boxShadow: '0 0 20px rgba(0, 118, 255, 0.2)'
      }
    }}>
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Avatar 
              variant="rounded" 
              sx={{ bgcolor: '#0076FF', width: 48, height: 48 }}
            >
              {plugin.name[0]}
            </Avatar>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: "bold" }}>{plugin.name}</Typography>
              <Typography variant="caption" color="text.secondary">v{plugin.version}</Typography>
            </Box>
          </Box>
          <Switch 
            checked={plugin.is_enabled} 
            onChange={handleToggle}
            color="primary" 
            disabled={toggleMutation.isPending}
          />
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ 
          height: '40px', 
          overflow: 'hidden', 
          textOverflow: 'ellipsis',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          mb: 2
        }}>
          {plugin.description || 'No description provided.'}
        </Typography>

        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Chip 
            label={plugin.anchor_step} 
            size="small" 
            variant="outlined" 
            sx={{ borderColor: 'rgba(255, 255, 255, 0.2)', color: 'text.secondary' }} 
          />
          <Box>
            <IconButton size="small" sx={{ color: 'text.secondary' }}>
              <SettingsIcon fontSize="small" />
            </IconButton>
            <IconButton 
              size="small" 
              sx={{ color: 'error.main' }}
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

export default PluginCard;
