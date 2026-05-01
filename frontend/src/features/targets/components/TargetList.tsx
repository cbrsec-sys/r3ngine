import React from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow,
  Paper,
  Chip,
  IconButton,
  Button,
  LinearProgress,
  Tooltip,
  TextField,
  InputAdornment
} from '@mui/material';
import { 
  Search, 
  MoreVertical, 
  Activity, 
  ShieldAlert, 
  ExternalLink, 
  Play, 
  Settings,
  Plus
} from 'lucide-react';
import { useDomains } from '../api';
import { useAppContext } from '../../../context/AppContext';

export const TargetList: React.FC = () => {
  const { projectName } = useAppContext();
  const { data: domains, isLoading, error } = useDomains(projectName || 'default');

  if (isLoading) return <LinearProgress sx={{ bgcolor: 'rgba(0, 243, 255, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff' } }} />;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ 
            fontFamily: 'Orbitron', 
            fontWeight: 900, 
            letterSpacing: 2, 
            color: '#fff',
            textShadow: '0 0 20px rgba(0, 243, 255, 0.5)',
            mb: 1
          }}>
            TARGET DOMAINS
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', letterSpacing: 1 }}>
            ACTIVE RECONNAISSANCE PERIMETER
          </Typography>
        </Box>
        <Button 
          variant="contained" 
          startIcon={<Plus size={18} />}
          sx={{ 
            bgcolor: '#7000ff',
            '&:hover': { bgcolor: '#8a2be2' },
            fontFamily: 'Orbitron',
            fontWeight: 800,
            px: 3
          }}
        >
          Add Target
        </Button>
      </Box>

      <Card sx={{ 
        bgcolor: 'rgba(10, 10, 20, 0.6)', 
        backdropFilter: 'blur(10px)', 
        border: '1px solid rgba(0, 243, 255, 0.1)',
        borderRadius: 4,
        overflow: 'hidden'
      }}>
        <Box sx={{ p: 2, borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', gap: 2 }}>
          <TextField 
            placeholder="Search domains..."
            variant="outlined"
            size="small"
            sx={{ 
              maxWidth: 300,
              '& .MuiOutlinedInput-root': {
                color: '#fff',
                bgcolor: 'rgba(255,255,255,0.03)',
                '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                '&:hover fieldset': { borderColor: 'rgba(0, 243, 255, 0.3)' },
                '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
              }
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search size={16} style={{ color: 'rgba(255,255,255,0.3)' }} />
                </InputAdornment>
              ),
            }}
          />
        </Box>
        <TableContainer>
          <Table>
            <TableHead sx={{ bgcolor: 'rgba(0, 243, 255, 0.03)' }}>
              <TableRow>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.75rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>DOMAIN</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.75rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>ORGANIZATION</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.75rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>VULNS</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.75rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>LAST SCAN</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.75rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>STATUS</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.75rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)', textAlign: 'right' }}>ACTIONS</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {domains?.map((domain) => (
                <TableRow key={domain.id} sx={{ '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' }, transition: 'all 0.2s' }}>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Typography variant="body2" sx={{ fontWeight: 700, color: '#e6f1ff' }}>{domain.name}</Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>Added {domain.insert_date_humanized}</Typography>
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {domain.organization?.map(org => (
                      <Chip 
                        key={org} 
                        label={org} 
                        size="small" 
                        sx={{ 
                          bgcolor: 'rgba(112, 0, 255, 0.1)', 
                          color: '#7000ff', 
                          border: '1px solid rgba(112, 0, 255, 0.2)',
                          fontSize: '0.65rem',
                          fontWeight: 700
                        }} 
                      />
                    ))}
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <ShieldAlert size={14} style={{ color: domain.vuln_count ? '#ff003c' : 'rgba(255,255,255,0.2)' }} />
                      <Typography sx={{ fontWeight: 800, color: domain.vuln_count ? '#ff003c' : 'rgba(255,255,255,0.4)' }}>
                        {domain.vuln_count || 0}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Activity size={12} style={{ color: '#00f3ff' }} />
                      {domain.start_scan_date_humanized || 'Never scanned'}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Chip 
                      label={domain.is_monitored ? 'MONITORED' : 'INACTIVE'} 
                      size="small"
                      sx={{ 
                        height: 20,
                        fontSize: '0.6rem',
                        fontWeight: 900,
                        bgcolor: domain.is_monitored ? 'rgba(0, 255, 98, 0.1)' : 'rgba(255, 255, 255, 0.05)',
                        color: domain.is_monitored ? '#00ff62' : 'rgba(255,255,255,0.4)',
                        border: domain.is_monitored ? '1px solid rgba(0, 255, 98, 0.2)' : '1px solid rgba(255,255,255,0.1)'
                      }}
                    />
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', textAlign: 'right' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                      <Tooltip title="Start Scan">
                        <IconButton size="small" sx={{ color: '#00ff62', '&:hover': { bgcolor: 'rgba(0, 255, 98, 0.1)' } }}>
                          <Play size={16} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Configure">
                        <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                          <Settings size={16} />
                        </IconButton>
                      </Tooltip>
                      <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.3)' }}>
                        <MoreVertical size={16} />
                      </IconButton>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
    </Box>
  );
};
