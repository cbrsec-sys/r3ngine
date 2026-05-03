import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Grid, 
  Button, 
  Card,
  CardContent,
  CardActions,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  Avatar,
  ButtonGroup,
  Menu,
  MenuItem,
  Divider,
  Alert,
  Snackbar,
  LinearProgress
} from '@mui/material';
import { 
  MoreVertical, 
  RefreshCw, 
  Download, 
  Trash2, 
  ExternalLink, 
  Hammer, 
  Wrench,
  Shield,
  Zap,
  Cpu,
  Plus
} from 'lucide-react';
import { TacticalPanel } from '../../../components/TacticalPanel';
import { 
  useToolArsenal, 
  useToolVersion, 
  useUpdateTool, 
  useUninstallTool 
} from '../api';
import { useParams, Link } from '@tanstack/react-router';

export const ToolArsenalPage: React.FC = () => {
  const { projectSlug } = useParams({ from: '/$projectSlug/settings/tool-arsenal' });
  const [filter, setFilter] = useState<'all' | 'default' | 'custom'>('all');
  const [toolVersions, setToolVersions] = useState<Record<number, string>>({});
  const [anchorEl, setAnchorEl] = useState<{ [key: number]: HTMLElement | null }>({});
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'info' }>({
    open: false,
    message: '',
    severity: 'info'
  });

  const [modal, setModal] = useState<{ open: boolean; tool?: InstalledTool }>({
    open: false
  });

  const { data: arsenal, isLoading } = useToolArsenal(projectSlug);
  const fetchVersion = useToolVersion();
  const updateTool = useUpdateTool();
  const uninstallTool = useUninstallTool(projectSlug);
  const addTool = useAddTool(projectSlug);
  const modifyTool = useModifyTool(projectSlug);

  const filteredTools = arsenal?.tools.filter(tool => {
    if (filter === 'default') return tool.is_default;
    if (filter === 'custom') return !tool.is_default;
    return true;
  }) || [];

  // Fetch current versions on mount
  useEffect(() => {
    if (arsenal?.tools) {
      arsenal.tools.forEach(tool => {
        handleFetchVersion(tool.id, 'current');
      });
    }
  }, [arsenal?.tools]);

  const handleFetchVersion = (toolId: number, type: 'current' | 'latest') => {
    fetchVersion.mutate({ toolId, type }, {
      onSuccess: (data) => {
        if (data.status) {
          const version = data.version_number || data.name || 'Unknown';
          setToolVersions(prev => ({ ...prev, [toolId]: version }));
          if (type === 'latest') {
             setSnackbar({ open: true, message: `Latest version for tool is ${version}`, severity: 'info' });
          }
        } else {
           setToolVersions(prev => ({ ...prev, [toolId]: data.message || 'Error' }));
        }
      }
    });
  };

  const handleUpdate = (toolId: number, toolName: string) => {
    setSnackbar({ open: true, message: `Updating ${toolName}...`, severity: 'info' });
    updateTool.mutate(toolId, {
      onSuccess: (data) => {
        setSnackbar({ open: true, message: data.message || `${toolName} updated successfully`, severity: 'success' });
        handleFetchVersion(toolId, 'current');
      },
      onError: () => {
        setSnackbar({ open: true, message: `Failed to update ${toolName}`, severity: 'error' });
      }
    });
  };

  const handleUninstall = (toolId: number, toolName: string) => {
    if (window.confirm(`Are you sure you want to uninstall ${toolName}?`)) {
      uninstallTool.mutate(toolId, {
        onSuccess: () => {
          setSnackbar({ open: true, message: `${toolName} uninstalled`, severity: 'success' });
        }
      });
    }
  };

  const handleFormSubmit = (formData: FormData) => {
    if (modal.tool) {
      modifyTool.mutate({ toolId: modal.tool.id, formData }, {
        onSuccess: (data) => {
          setSnackbar({ open: true, message: data.message || 'Tool updated successfully', severity: 'success' });
          setModal({ open: false });
        },
        onError: (error: any) => {
          setSnackbar({ open: true, message: error.response?.data?.message || 'Failed to update tool', severity: 'error' });
        }
      });
    } else {
      addTool.mutate(formData, {
        onSuccess: (data) => {
          setSnackbar({ open: true, message: data.message || 'Tool added successfully', severity: 'success' });
          setModal({ open: false });
        },
        onError: (error: any) => {
          setSnackbar({ open: true, message: error.response?.data?.message || 'Failed to add tool', severity: 'error' });
        }
      });
    }
  };

  const handleMenuOpen = (id: number, event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl({ ...anchorEl, [id]: event.currentTarget });
  };

  const handleMenuClose = (id: number) => {
    setAnchorEl({ ...anchorEl, [id]: null });
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 10 }}>
        <CircularProgress sx={{ color: '#00f3ff' }} />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <Box>
          <Typography variant="h4" sx={{ fontFamily: 'Orbitron', fontWeight: 900, color: '#fff', mb: 1 }}>
            TOOL_ARSENAL
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>
            Manage and update external security tools.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <ButtonGroup variant="outlined" size="small">
            <Button 
              onClick={() => setFilter('all')}
              sx={{ 
                bgcolor: filter === 'all' ? 'rgba(0,243,255,0.1)' : 'transparent',
                color: filter === 'all' ? '#00f3ff' : 'rgba(255,255,255,0.5)',
                borderColor: 'rgba(0,243,255,0.3)'
              }}
            >
              ALL
            </Button>
            <Button 
              onClick={() => setFilter('default')}
              sx={{ 
                bgcolor: filter === 'default' ? 'rgba(0,243,255,0.1)' : 'transparent',
                color: filter === 'default' ? '#00f3ff' : 'rgba(255,255,255,0.5)',
                borderColor: 'rgba(0,243,255,0.3)'
              }}
            >
              DEFAULT
            </Button>
            <Button 
              onClick={() => setFilter('custom')}
              sx={{ 
                bgcolor: filter === 'custom' ? 'rgba(0,243,255,0.1)' : 'transparent',
                color: filter === 'custom' ? '#00f3ff' : 'rgba(255,255,255,0.5)',
                borderColor: 'rgba(0,243,255,0.3)'
              }}
            >
              CUSTOM
            </Button>
          </ButtonGroup>
          <Button
            component={Link}
            to={`/${projectSlug}/settings/tool-arsenal/add`}
            variant="contained"
            startIcon={<Plus size={18} />}
            sx={{ bgcolor: '#00f3ff', color: '#000', fontWeight: 'bold', '&:hover': { bgcolor: '#00d8e4' } }}
          >
            ADD TOOL
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {filteredTools.map((tool) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={tool.id}>
            <Card sx={{ 
              bgcolor: 'rgba(0,0,0,0.3)', 
              border: `1px solid ${tool.is_default ? 'rgba(0,243,255,0.2)' : 'rgba(255,0,60,0.2)'}`,
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              position: 'relative',
              '&:hover': {
                borderColor: tool.is_default ? '#00f3ff' : '#ff003c',
                boxShadow: `0 0 15px ${tool.is_default ? 'rgba(0,243,255,0.1)' : 'rgba(255,0,60,0.1)'}`
              }
            }}>
              <Box sx={{ 
                position: 'absolute', 
                top: 10, 
                left: 10,
                zIndex: 1
              }}>
                <Chip 
                  label={tool.is_default ? "DEFAULT" : "CUSTOM"} 
                  size="small"
                  sx={{ 
                    height: 16, 
                    fontSize: '8px', 
                    fontFamily: 'Orbitron',
                    bgcolor: tool.is_default ? 'rgba(0,243,255,0.1)' : 'rgba(255,0,60,0.1)',
                    color: tool.is_default ? '#00f3ff' : '#ff003c',
                    border: `1px solid ${tool.is_default ? '#00f3ff' : '#ff003c'}`
                  }}
                />
              </Box>

              {!tool.is_default && (
                <Box sx={{ position: 'absolute', top: 5, right: 5, zIndex: 1 }}>
                  <IconButton size="small" onClick={(e) => handleMenuOpen(tool.id, e)} sx={{ color: 'rgba(255,255,255,0.5)' }}>
                    <MoreVertical size={16} />
                  </IconButton>
                  <Menu
                    anchorEl={anchorEl[tool.id]}
                    open={Boolean(anchorEl[tool.id])}
                    onClose={() => handleMenuClose(tool.id)}
                    PaperProps={{
                      sx: { bgcolor: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }
                    }}
                  >
                    <MenuItem onClick={() => {
                      handleMenuClose(tool.id);
                      // Navigate to edit
                    }}>
                      <Wrench size={14} style={{ marginRight: 8 }} /> Modify
                    </MenuItem>
                    <Divider sx={{ bgcolor: 'rgba(255,255,255,0.1)' }} />
                    <MenuItem onClick={() => {
                      handleMenuClose(tool.id);
                      handleUninstall(tool.id, tool.name);
                    }} sx={{ color: '#ff003c' }}>
                      <Trash2 size={14} style={{ marginRight: 8 }} /> Uninstall
                    </MenuItem>
                  </Menu>
                </Box>
              )}

              <CardContent sx={{ textAlign: 'center', pt: 4, flexGrow: 1 }}>
                <Avatar 
                  src={tool.logo_url || undefined}
                  sx={{ 
                    width: 50, 
                    height: 50, 
                    mx: 'auto', 
                    mb: 2, 
                    bgcolor: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)'
                  }}
                >
                  {!tool.logo_url && <Cpu size={24} color="rgba(255,255,255,0.3)" />}
                </Avatar>
                <Typography variant="h6" sx={{ fontFamily: 'Orbitron', fontSize: '16px', color: '#fff', mb: 1 }}>
                  {tool.name}
                </Typography>
                
                <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 0.5, mb: 2 }}>
                  {tool.is_subdomain_gathering && (
                    <Chip label="SUBDOMAIN" size="small" sx={{ height: 18, fontSize: '9px', bgcolor: 'rgba(0,243,255,0.05)', color: '#00f3ff' }} />
                  )}
                  <Box sx={{ display: 'flex', alignItems: 'center', ml: 1 }}>
                     <Link from={`/${projectSlug}/settings/tool-arsenal`} to={tool.github_url} target="_blank" style={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px', textDecoration: 'none', display: 'flex', alignItems: 'center' }}>
                      GITHUB <ExternalLink size={10} style={{ marginLeft: 2 }} />
                    </Link>
                  </Box>
                </Box>

                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '12px', mb: 2, minHeight: 40, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {tool.description}
                </Typography>

                <Box sx={{ mt: 'auto', p: 1, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: 1 }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', display: 'block', mb: 0.5 }}>
                    CURRENT VERSION
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#00f3ff', fontFamily: 'monospace', fontWeight: 'bold' }}>
                    {toolVersions[tool.id] || (fetchVersion.isPending ? '...' : '---')}
                  </Typography>
                </Box>
              </CardContent>

              <CardActions sx={{ p: 2, pt: 0 }}>
                <Button 
                  fullWidth 
                  size="small"
                  variant="outlined"
                  startIcon={<RefreshCw size={14} className={fetchVersion.isPending ? 'animate-spin' : ''} />}
                  onClick={() => handleFetchVersion(tool.id, 'latest')}
                  sx={{ 
                    borderColor: 'rgba(0,243,255,0.3)', 
                    color: '#00f3ff',
                    fontSize: '11px',
                    '&:hover': { borderColor: '#00f3ff', bgcolor: 'rgba(0,243,255,0.05)' }
                  }}
                >
                  CHECK UPDATE
                </Button>
                <Tooltip title="Force Update">
                  <IconButton 
                    size="small" 
                    onClick={() => handleUpdate(tool.id, tool.name)}
                    sx={{ color: 'rgba(255,255,255,0.3)', '&:hover': { color: '#00f3ff' } }}
                  >
                    <Download size={14} />
                  </IconButton>
                </Tooltip>
              </CardActions>
              {updateTool.isPending && <LinearProgress sx={{ height: 2, bgcolor: 'transparent', '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff' } }} />}
            </Card>
          </Grid>
        ))}
      </Grid>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity as any}
          sx={{ 
            width: '100%', 
            bgcolor: snackbar.severity === 'success' ? '#1b5e20' : snackbar.severity === 'error' ? '#d32f2f' : '#01579b', 
            color: '#fff' 
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>

      <style>
        {`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          .animate-spin {
            animation: spin 2s linear infinite;
          }
        `}
      </style>
    </Box>
  );
};
