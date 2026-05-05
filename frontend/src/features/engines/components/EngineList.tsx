import React from 'react';
import { 
  Box, 
  Card, 
  Typography, 
  Grid,
  Chip,
  IconButton,
  Button,
  LinearProgress,
  Tooltip,
  Paper,
  Divider
} from '@mui/material';
import { 
  Plus, 
  Settings, 
  Trash2, 
  Cpu,
  Zap,
  ChevronRight,
  Shield,
  Search,
  Code
} from 'lucide-react';
import { useEngines, useDeleteEngine } from '../api';
import { EditEngineModal } from './EditEngineModal';

export const EngineList: React.FC = () => {
  const { data: engines, isLoading } = useEngines();
  const deleteEngine = useDeleteEngine();
  const [editModalOpen, setEditModalOpen] = React.useState(false);
  const [selectedEngineId, setSelectedEngineId] = React.useState<number | null>(null);

  const handleEdit = (id: number) => {
    setSelectedEngineId(id);
    setEditModalOpen(true);
  };

  if (isLoading) return <LinearProgress sx={{ bgcolor: 'rgba(0, 243, 255, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff' } }} />;

  return (
    <Box>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {engines?.map((engine) => (
          <Card 
            key={engine.id} 
            onClick={() => handleEdit(engine.id)}
            sx={{ 
              width: '100%',
              bgcolor: 'rgba(10, 10, 20, 0.4)', 
              backdropFilter: 'blur(10px)', 
              border: '1px solid rgba(255, 255, 255, 0.05)',
              borderRadius: 1,
              transition: 'all 0.2s ease',
              position: 'relative',
              overflow: 'hidden',
              cursor: 'pointer',
              '&:hover': {
                bgcolor: 'rgba(15, 15, 30, 0.6)',
                border: '1px solid rgba(0, 243, 255, 0.2)',
                transform: 'translateX(4px)',
                '& .action-btns': { opacity: 1 }
              }
            }}
          >
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              minHeight: 64,
              p: { xs: 2, md: 1 },
              pr: 2,
              flexWrap: { xs: 'wrap', md: 'nowrap' },
              gap: { xs: 2, md: 0 },
              borderLeft: engine.default_engine ? '3px solid #7000ff' : '3px solid rgba(255,255,255,0.1)'
            }}>
              {/* Left: Engine Identity */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: { xs: '100%', md: 260 }, pl: 1, flexShrink: 0 }}>
                <Paper sx={{ 
                  p: 0.8, 
                  bgcolor: engine.default_engine ? 'rgba(112, 0, 255, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                  borderRadius: 1,
                  border: engine.default_engine ? '1px solid rgba(112, 0, 255, 0.3)' : '1px solid rgba(255,255,255,0.05)'
                }}>
                  <Shield size={16} style={{ color: engine.default_engine ? '#7000ff' : 'rgba(255,255,255,0.3)' }} />
                </Paper>
                <Box sx={{ overflow: 'hidden' }}>
                  <Typography variant="body2" sx={{ 
                    fontFamily: 'Orbitron', 
                    fontWeight: 800, 
                    color: '#fff',
                    fontSize: '0.8rem',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {engine.engine_name}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.55rem', letterSpacing: 1 }}>
                      ID: {engine.id}
                    </Typography>
                    {engine.default_engine && (
                      <Typography variant="caption" sx={{ color: '#7000ff', fontSize: '0.55rem', fontWeight: 900, letterSpacing: 1 }}>
                        [PRIMARY]
                      </Typography>
                    )}
                  </Box>
                </Box>
              </Box>

              <Divider orientation="vertical" flexItem sx={{ mx: 2, display: { xs: 'none', md: 'block' }, borderColor: 'rgba(255,255,255,0.05)' }} />

              {/* Center: Task Steps (Left-aligned in center area) */}
              <Box sx={{ 
                flexGrow: 1, 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'flex-start',
                gap: 1.5,
                minWidth: { xs: '100%', md: 0 },
                px: { md: 2 }
              }}>
                <Zap size={12} style={{ color: '#00f3ff', opacity: 0.5, flexShrink: 0 }} />
                <Box sx={{ 
                  display: 'flex', 
                  gap: 0.8, 
                  flexWrap: 'wrap',
                  justifyContent: 'flex-start',
                  py: 1
                }}>
                  {engine.tasks?.map((task) => (
                    <Chip 
                      key={task}
                      label={task.replace(/_/g, ' ')}
                      size="small"
                      sx={{ 
                        height: 22,
                        fontSize: '0.65rem',
                        fontWeight: 900,
                        bgcolor: 'rgba(0, 243, 255, 0.05)',
                        color: 'rgba(0, 243, 255, 0.9)',
                        border: '1px solid rgba(0, 243, 255, 0.2)',
                        borderRadius: 0.5,
                        textTransform: 'uppercase',
                        letterSpacing: 1,
                        '&:hover': {
                          bgcolor: 'rgba(0, 243, 255, 0.15)',
                          borderColor: '#00f3ff',
                          color: '#fff',
                          boxShadow: '0 0 15px rgba(0, 243, 255, 0.2)'
                        }
                      }}
                    />
                  ))}
                </Box>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.2)', fontSize: '0.6rem', ml: 1, flexShrink: 0, fontFamily: 'monospace', display: { xs: 'none', lg: 'block' } }}>
                  [{String(engine.tasks?.length || 0).padStart(2, '0')}_STEPS]
                </Typography>
              </Box>

              <Divider orientation="vertical" flexItem sx={{ mx: 2, display: { xs: 'none', md: 'block' }, borderColor: 'rgba(255,255,255,0.05)' }} />

              {/* Right: Actions */}
              <Box className="action-btns" sx={{ 
                display: 'flex', 
                gap: 1, 
                opacity: { xs: 1, md: 0.4 }, 
                transition: 'opacity 0.2s',
                width: { xs: '100%', md: 100 },
                justifyContent: { xs: 'center', md: 'flex-end' },
                flexShrink: 0
              }}>
                <Tooltip title="Configure YAML">
                  <IconButton 
                    size="small" 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleEdit(engine.id);
                    }}
                    sx={{ color: 'rgba(255,255,255,0.5)', '&:hover': { color: '#00f3ff', bgcolor: 'rgba(0,243,255,0.1)' } }}
                  >
                    <Code size={16} />
                  </IconButton>
                </Tooltip>
                {!engine.default_engine && (
                  <Tooltip title="Purge Engine">
                    <IconButton 
                      size="small" 
                      disabled={deleteEngine.isPending}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm(`Purge engine "${engine.engine_name}"?`)) {
                          deleteEngine.mutate(engine.id);
                        }
                      }}
                      sx={{ color: 'rgba(255,255,255,0.5)', '&:hover': { color: '#ff003c', bgcolor: 'rgba(255,0,60,0.1)' } }}
                    >
                      <Trash2 size={16} />
                    </IconButton>
                  </Tooltip>
                )}
              </Box>
            </Box>
          </Card>
        ))}
      </Box>

      <EditEngineModal 
        open={editModalOpen} 
        onClose={() => setEditModalOpen(false)} 
        engineId={selectedEngineId}
      />
    </Box>
  );
};
