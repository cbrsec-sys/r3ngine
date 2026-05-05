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
  Chip,
  IconButton,
  LinearProgress,
  Tooltip,
  TextField,
  InputAdornment,
  Button
} from '@mui/material';
import { 
  Search, 
  Activity, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  Play,
  StopCircle,
  MoreVertical,
  RefreshCw,
  Eye
} from 'lucide-react';
import { useScans } from '../api';
import { useAppContext } from '../../../context/AppContext';
import { useParams } from '@tanstack/react-router';
import { StartScanModal } from './StartScanModal';

export const ScanList: React.FC = () => {
  const { projectSlug = 'default' } = useParams({ strict: false }) as any;
  const { data: scans, isLoading } = useScans(projectSlug);
  const [isStartScanModalOpen, setIsStartScanModalOpen] = React.useState(false);

  const getStatusChip = (status: number) => {
    switch (status) {
      case 2: // Success
        return <Chip label="SUCCESS" size="small" sx={{ bgcolor: 'rgba(0, 255, 98, 0.1)', color: '#00ff62', border: '1px solid rgba(0, 255, 98, 0.2)', fontSize: '0.6rem', fontWeight: 900, fontFamily: 'Orbitron' }} icon={<CheckCircle2 size={12} />} />;
      case 1: // Running
        return <Chip label="RUNNING" size="small" sx={{ bgcolor: 'rgba(0, 243, 255, 0.1)', color: '#00f3ff', border: '1px solid rgba(0, 243, 255, 0.2)', fontSize: '0.6rem', fontWeight: 900, fontFamily: 'Orbitron' }} icon={<RefreshCw size={12} className="spin" />} />;
      case -1: // Error
        return <Chip label="FAILED" size="small" sx={{ bgcolor: 'rgba(255, 0, 60, 0.1)', color: '#ff003c', border: '1px solid rgba(255, 0, 60, 0.2)', fontSize: '0.6rem', fontWeight: 900, fontFamily: 'Orbitron' }} icon={<XCircle size={12} />} />;
      default:
        return <Chip label="PENDING" size="small" sx={{ bgcolor: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.4)', border: '1px solid rgba(255,255,255,0.1)', fontSize: '0.6rem', fontWeight: 900, fontFamily: 'Orbitron' }} />;
    }
  };

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
            SCAN OPERATIONS
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', letterSpacing: 1 }}>
            HISTORICAL MISSION LOGS & ACTIVE DEPLOYMENTS
          </Typography>
        </Box>
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
            placeholder="Filter operations..."
            variant="outlined"
            size="small"
            sx={{ 
              maxWidth: 400,
              flex: 1,
              '& .MuiOutlinedInput-root': {
                color: '#fff',
                bgcolor: 'rgba(255,255,255,0.03)',
                '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                '&:hover fieldset': { borderColor: 'rgba(0, 243, 255, 0.3)' },
                '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
              }
            }}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <Search size={16} style={{ color: 'rgba(255,255,255,0.3)' }} />
                  </InputAdornment>
                ),
              }
            }}
          />
        </Box>
        <TableContainer>
          <Table>
            <TableHead sx={{ bgcolor: 'rgba(0, 243, 255, 0.03)' }}>
              <TableRow>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.75rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>TARGET / ENGINE</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.75rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>PROGRESS</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.75rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>RESULTS</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.75rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>STATUS</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.75rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>TIMELINE</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.75rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)', textAlign: 'right' }}>ACTIONS</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {scans?.map((scan) => (
                <TableRow key={scan.id} sx={{ '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' }, transition: 'all 0.2s' }}>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Typography variant="body2" sx={{ fontWeight: 700, color: '#fff' }}>{scan.domain?.name || 'N/A'}</Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(0, 243, 255, 0.6)', fontWeight: 600 }}>{scan.scan_type?.engine_name || 'Standard'}</Typography>
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', minWidth: 150 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <LinearProgress 
                        variant="determinate" 
                        value={scan.current_progress || 0} 
                        sx={{ 
                          flexGrow: 1, 
                          height: 4, 
                          borderRadius: 2,
                          bgcolor: 'rgba(255,255,255,0.05)',
                          '& .MuiLinearProgress-bar': {
                            bgcolor: scan.scan_status === -1 ? '#ff003c' : '#00f3ff',
                            boxShadow: `0 0 10px ${scan.scan_status === -1 ? 'rgba(255, 0, 60, 0.5)' : 'rgba(0, 243, 255, 0.5)'}`
                          }
                        }} 
                      />
                      <Typography variant="caption" sx={{ fontWeight: 900, color: scan.scan_status === -1 ? '#ff003c' : '#00f3ff', width: 35 }}>
                        {Math.round(scan.current_progress || 0)}%
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Box sx={{ display: 'flex', gap: 1.5 }}>
                      <Tooltip title="Subdomains Found">
                        <Box sx={{ textAlign: 'center' }}>
                          <Typography variant="caption" sx={{ display: 'block', color: 'rgba(255,255,255,0.4)', fontWeight: 800 }}>SUB</Typography>
                          <Typography variant="body2" sx={{ fontWeight: 900, color: '#fff' }}>{scan.subdomain_count || 0}</Typography>
                        </Box>
                      </Tooltip>
                      <Tooltip title="Vulnerabilities Detected">
                        <Box sx={{ textAlign: 'center' }}>
                          <Typography variant="caption" sx={{ display: 'block', color: 'rgba(255,255,255,0.4)', fontWeight: 800 }}>VUL</Typography>
                          <Typography variant="body2" sx={{ fontWeight: 900, color: (scan.vulnerability_count || 0) > 0 ? '#ff003c' : '#fff' }}>
                            {scan.vulnerability_count || 0}
                          </Typography>
                        </Box>
                      </Tooltip>
                    </Box>
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {getStatusChip(scan.scan_status)}
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <Clock size={12} style={{ color: 'rgba(255,255,255,0.4)' }} />
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>{scan.completed_ago || (scan.scan_status === 1 ? 'Active' : 'N/A')}</Typography>
                    </Box>
                    <Typography variant="caption" sx={{ display: 'block', color: 'rgba(255,255,255,0.3)', fontSize: '0.65rem' }}>
                      Time: {scan.elapsed_time || '0s'}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', textAlign: 'right' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                      <Tooltip title="View Detailed Report">
                        <IconButton 
                          size="small" 
                          component="a"
                          href={`/scan/detail/${scan.id}`}
                          target="_blank"
                          sx={{ color: '#00f3ff', '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.1)' } }}
                        >
                          <Eye size={16} />
                        </IconButton>
                      </Tooltip>
                      {scan.scan_status === 1 && (
                        <Tooltip title="Stop Scan">
                          <IconButton size="small" sx={{ color: '#ff003c', '&:hover': { bgcolor: 'rgba(255, 0, 60, 0.1)' } }}>
                            <StopCircle size={16} />
                          </IconButton>
                        </Tooltip>
                      )}
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
