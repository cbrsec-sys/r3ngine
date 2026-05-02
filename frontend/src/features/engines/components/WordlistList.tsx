import React from 'react';
import { 
  Box, 
  Card, 
  Typography, 
  IconButton,
  Button,
  LinearProgress,
  Tooltip,
  TextField,
  InputAdornment,
  Divider,
  Paper
} from '@mui/material';
import { 
  Search, 
  Plus, 
  FileText, 
  Trash2, 
  Eye,
  List,
  ChevronRight,
  Database
} from 'lucide-react';
import { useWordlists, useDeleteWordlist } from '../api';
import { ViewWordlistModal } from './ViewWordlistModal';

export const WordlistList: React.FC = () => {
  const { data: wordlists, isLoading } = useWordlists();
  const deleteWordlist = useDeleteWordlist();
  const [viewModalOpen, setViewModalOpen] = React.useState(false);
  const [selectedWordlistId, setSelectedWordlistId] = React.useState<number | null>(null);

  const handleView = (id: number) => {
    setSelectedWordlistId(id);
    setViewModalOpen(true);
  };

  if (isLoading) return <LinearProgress sx={{ bgcolor: 'rgba(0, 243, 255, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff' } }} />;

  return (
    <Box>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {wordlists?.map((wordlist) => (
          <Card key={wordlist.id} sx={{ 
            bgcolor: 'rgba(10, 10, 20, 0.4)', 
            backdropFilter: 'blur(10px)', 
            border: '1px solid rgba(255, 255, 255, 0.05)',
            borderRadius: 1,
            transition: 'all 0.2s ease',
            '&:hover': {
              bgcolor: 'rgba(20, 10, 30, 0.6)',
              border: '1px solid rgba(255, 0, 255, 0.2)',
              transform: 'translateX(4px)',
              '& .action-btns': { opacity: 1 }
            }
          }}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              minHeight: 64, 
              p: { xs: 2, md: 1.5 }, 
              pr: 2,
              flexWrap: { xs: 'wrap', md: 'nowrap' },
              gap: { xs: 2, md: 0 }
            }}>
              {/* Left: Identity */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: { xs: '100%', md: 300 }, pl: 1, flexShrink: 0 }}>
                <Paper sx={{ 
                  p: 0.8, 
                  bgcolor: 'rgba(255, 0, 255, 0.05)', 
                  borderRadius: 1,
                  border: '1px solid rgba(255, 0, 255, 0.1)'
                }}>
                  <FileText size={16} style={{ color: '#ff00ff' }} />
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
                    {wordlist.name}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.55rem', fontFamily: 'monospace' }}>
                    {wordlist.short_name}
                  </Typography>
                </Box>
              </Box>

              <Divider orientation="vertical" flexItem sx={{ mx: 3, display: { xs: 'none', md: 'block' }, borderColor: 'rgba(255,255,255,0.05)' }} />

              {/* Center: Count (Left-aligned in center area) */}
              <Box sx={{ flexGrow: 1, display: 'flex', justifyContent: 'flex-start', minWidth: { xs: '100%', md: 0 }, px: { md: 2 } }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography sx={{ color: '#ff00ff', fontWeight: 900, fontFamily: 'Orbitron', fontSize: '1rem' }}>
                    {wordlist.count.toLocaleString()}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', letterSpacing: 1 }}>
                    ENTRIES_DETECTED
                  </Typography>
                </Box>
              </Box>

              <Divider orientation="vertical" flexItem sx={{ mx: 3, display: { xs: 'none', md: 'block' }, borderColor: 'rgba(255,255,255,0.05)' }} />

              {/* Right: Actions */}
              <Box className="action-btns" sx={{ 
                display: 'flex', 
                gap: 1, 
                opacity: { xs: 1, md: 0.4 }, 
                transition: 'opacity 0.2s',
                width: { xs: '100%', md: 150 },
                justifyContent: { xs: 'center', md: 'flex-end' },
                flexShrink: 0
              }}>
                <Tooltip title="View Content">
                  <IconButton 
                    size="small" 
                    onClick={() => handleView(wordlist.id)}
                    sx={{ color: 'rgba(255,255,255,0.5)', '&:hover': { color: '#ff00ff', bgcolor: 'rgba(255,0,255,0.1)' } }}
                  >
                    <Eye size={16} />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Purge Payload">
                  <IconButton 
                    size="small" 
                    disabled={deleteWordlist.isPending}
                    onClick={() => {
                      if (window.confirm(`Purge wordlist "${wordlist.name}"?`)) {
                        deleteWordlist.mutate(wordlist.id);
                      }
                    }}
                    sx={{ color: 'rgba(255,255,255,0.5)', '&:hover': { color: '#ff003c', bgcolor: 'rgba(255,0,60,0.1)' } }}
                  >
                    <Trash2 size={16} />
                  </IconButton>
                </Tooltip>
                <IconButton 
                  size="small" 
                  sx={{ color: 'rgba(255,255,255,0.3)' }}
                  onClick={() => handleView(wordlist.id)}
                >
                  <ChevronRight size={18} />
                </IconButton>
              </Box>
            </Box>
          </Card>
        ))}
        {(!wordlists || wordlists.length === 0) && (
          <Box sx={{ py: 8, textAlign: 'center', bgcolor: 'rgba(255,255,255,0.02)', borderRadius: 2, border: '1px dashed rgba(255,255,255,0.05)' }}>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.3)', fontFamily: 'Orbitron' }}>
              VAULT_EMPTY_NO_PAYLOADS_DETECTED
            </Typography>
          </Box>
        )}
      </Box>

      <ViewWordlistModal 
        open={viewModalOpen} 
        onClose={() => setViewModalOpen(false)} 
        wordlistId={selectedWordlistId}
      />
    </Box>
  );
};
