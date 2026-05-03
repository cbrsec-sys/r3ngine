import React, { useState } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Tabs,
  Tab,
  Stack,
  Chip,
  Button,
  CircularProgress,
  Divider,
  Paper
} from '@mui/material';
import {
  X,
  Clock,
  Play,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  StopCircle,
  RefreshCw,
  Search,
  Activity,
  Layers,
  Shield,
  Bug
} from 'lucide-react';
import { useScanStatus, useStopScanAction, useDeleteScanAction } from '../api';

interface ScanHistoryDrawerProps {
  open: boolean;
  onClose: () => void;
  projectSlug: string;
}

const getStatusColor = (status: number) => {
  switch (status) {
    case 0: return '#00f3ff'; // Completed
    case 1: return '#fffc00'; // Scanning
    case 2: return '#00f3ff'; // Success
    case 3: return '#ff003c'; // Aborted/Failed
    default: return 'rgba(255,255,255,0.5)';
  }
};

const getStatusText = (status: number) => {
  switch (status) {
    case 0: return 'Scan Completed';
    case 1: return 'In Progress';
    case 2: return 'Scan Completed';
    case 3: return 'Aborted';
    default: return 'Unknown';
  }
};

const ScanItem = ({ scan, onStop, onDelete }: { scan: any, onStop: (id: number) => void, onDelete: (id: number) => void }) => (
  <Paper sx={{
    p: 2,
    mb: 2,
    bgcolor: 'rgba(20, 20, 25, 0.5)',
    border: '1px solid rgba(255,255,255,0.05)',
    borderRadius: 2,
    position: 'relative',
    overflow: 'hidden',
    transition: 'all 0.2s',
    '&:hover': {
      bgcolor: 'rgba(255,255,255,0.08)',
      borderColor: 'rgba(0, 243, 255, 0.3)',
      transform: 'translateX(-4px)'
    }
  }}>
    {/* Decorative line */}
    <Box sx={{ position: 'absolute', top: 0, left: 0, bottom: 0, width: 3, bgcolor: getStatusColor(scan.scan_status) }} />

    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
      <Box>
        <Typography sx={{
          fontFamily: 'Orbitron',
          fontWeight: 900,
          fontSize: '0.75rem',
          color: getStatusColor(scan.scan_status),
          textTransform: 'uppercase',
          letterSpacing: 1
        }}>
          {scan.engine_name || scan.scan_type?.engine_name || 'GENERAL SCAN'} ON {scan.domain_name || 'UNKNOWN'}
        </Typography>
        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', mt: 0.5 }}>
          {scan.scan_status === 1 ? 'Running Since ' : 'Scan Completed '} {scan.completed_ago || 'just now'}
        </Typography>
      </Box>
      <Chip
        label={getStatusText(scan.scan_status)}
        size="small"
        sx={{
          height: 20,
          fontSize: '0.6rem',
          fontWeight: 900,
          bgcolor: `${getStatusColor(scan.scan_status)}22`,
          color: getStatusColor(scan.scan_status),
          border: `1px solid ${getStatusColor(scan.scan_status)}44`,
          fontFamily: 'Orbitron'
        }}
      />
    </Stack>

    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
      <Box sx={{ px: 1, py: 0.5, bgcolor: 'rgba(0, 243, 255, 0.1)', borderRadius: 1, border: '1px solid rgba(0, 243, 255, 0.2)' }}>
        <Typography sx={{ fontSize: '0.7rem', fontWeight: 900, color: '#00f3ff' }}>{scan.subdomain_count || 0}</Typography>
      </Box>
      <Box sx={{ px: 1, py: 0.5, bgcolor: 'rgba(112, 0, 255, 0.1)', borderRadius: 1, border: '1px solid rgba(112, 0, 255, 0.2)' }}>
        <Typography sx={{ fontSize: '0.7rem', fontWeight: 900, color: '#7000ff' }}>{scan.endpoint_count || 0}</Typography>
      </Box>
      <Box sx={{ px: 1, py: 0.5, bgcolor: 'rgba(255, 0, 60, 0.1)', borderRadius: 1, border: '1px solid rgba(255, 0, 60, 0.2)' }}>
        <Typography sx={{ fontSize: '0.7rem', fontWeight: 900, color: '#ff003c' }}>{scan.vulnerability_count || 0}</Typography>
      </Box>
    </Stack>

    <Stack direction="row" spacing={1} justifyContent="flex-end">
      {scan.scan_status === 1 && (
        <Button
          size="small"
          startIcon={<StopCircle size={14} />}
          onClick={() => onStop(scan.id)}
          sx={{ fontSize: '0.65rem', color: '#ff003c', '&:hover': { bgcolor: 'rgba(255,0,60,0.1)' } }}
        >
          STOP
        </Button>
      )}
      <IconButton
        size="small"
        onClick={() => onDelete(scan.id)}
        sx={{ color: 'rgba(255,255,255,0.3)', '&:hover': { color: '#ff003c' } }}
      >
        <Trash2 size={14} />
      </IconButton>
    </Stack>
  </Paper>
);

const TaskItem = ({ task, onStop }: { task: any, onStop?: (id: number) => void }) => (
  <Paper sx={{
    p: 2,
    mb: 2,
    bgcolor: 'rgba(20, 20, 25, 0.5)',
    border: '1px solid rgba(255,255,255,0.05)',
    borderRadius: 2,
    position: 'relative',
    transition: 'all 0.2s',
    '&:hover': {
      bgcolor: 'rgba(255,255,255,0.08)',
      borderColor: 'rgba(112, 0, 255, 0.3)',
      transform: 'translateX(-4px)'
    }
  }}>
    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
      <Box>
        <Typography sx={{
          fontFamily: 'Orbitron',
          fontWeight: 900,
          fontSize: '0.7rem',
          color: '#7000ff',
          letterSpacing: 0.5
        }}>
          {task.subdomain_name || 'UNKNOWN'} USING ENGINE {task.engine_name || task.engine?.engine_name || 'DEFAULT'}
        </Typography>
        <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', mt: 0.5 }}>
          Running Since {task.elapsed_time || 'just now'}
        </Typography>
      </Box>
      <Chip
        label="In Progress"
        size="small"
        sx={{
          height: 20,
          fontSize: '0.6rem',
          fontWeight: 900,
          bgcolor: 'rgba(0, 243, 255, 0.1)',
          color: '#00f3ff',
          border: '1px solid rgba(0, 243, 255, 0.3)',
          fontFamily: 'Orbitron'
        }}
      />
    </Stack>

    {onStop && (
      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          size="small"
          variant="outlined"
          startIcon={<AlertTriangle size={12} />}
          sx={{
            fontSize: '0.6rem',
            color: '#ff003c',
            borderColor: 'rgba(255,0,60,0.3)',
            '&:hover': { borderColor: '#ff003c', bgcolor: 'rgba(255,0,60,0.05)' }
          }}
        >
          Stop
        </Button>
      </Box>
    )}
  </Paper>
);

const SectionHeader = ({ title, count }: { title: string, count?: number }) => (
  <Box sx={{ mb: 2, mt: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
    <Typography sx={{
      fontFamily: 'Orbitron',
      fontSize: '0.65rem',
      fontWeight: 900,
      color: 'rgba(255,255,255,0.5)',
      letterSpacing: 2
    }}>
      {title}
    </Typography>
    {count !== undefined && count > 0 && (
      <Chip
        label={`${count} ACTIVE`}
        size="small"
        sx={{ height: 18, fontSize: '0.55rem', fontWeight: 900, bgcolor: '#00f3ff', color: '#000', fontFamily: 'Orbitron' }}
      />
    )}
  </Box>
);

export const ScanHistoryDrawer: React.FC<ScanHistoryDrawerProps> = ({ open, onClose, projectSlug }) => {
  const [activeTab, setActiveTab] = useState(0);
  const { data: status, isLoading, refetch } = useScanStatus(projectSlug);
  const stopScan = useStopScanAction(projectSlug);
  const deleteScan = useDeleteScanAction(projectSlug);

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      paperprops={{
        sx: {
          width: 450,
          bgcolor: 'rgba(5, 5, 10, 0.98)',
          backdropFilter: 'blur(25px)',
          borderLeft: '1px solid rgba(0, 243, 255, 0.2)',
          color: '#fff',
          boxShadow: '-10px 0 40px rgba(0,0,0,0.9)'
        }
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2.5, borderBottom: '1px solid rgba(0, 243, 255, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box sx={{
            width: 32,
            height: 32,
            borderRadius: 1,
            bgcolor: 'rgba(0, 243, 255, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid rgba(0, 243, 255, 0.2)'
          }}>
            <Activity size={18} color="#00f3ff" />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontFamily: 'Orbitron', fontSize: '0.9rem', fontWeight: 900, letterSpacing: 1 }}>
              SCAN CENTER
            </Typography>
            <Typography sx={{ fontSize: '0.6rem', color: 'rgba(0, 243, 255, 0.6)', fontWeight: 600, letterSpacing: 0.5 }}>
              REAL-TIME STATUS MONITOR
            </Typography>
          </Box>
        </Box>
        <Stack direction="row" spacing={1}>
          <IconButton size="small" onClick={() => refetch()} sx={{ color: 'rgba(255,255,255,0.4)', '&:hover': { color: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.1)' } }}>
            <RefreshCw size={16} />
          </IconButton>
          <IconButton size="small" onClick={onClose} sx={{ color: 'rgba(255,255,255,0.4)', '&:hover': { color: '#ff003c', bgcolor: 'rgba(255, 0, 60, 0.1)' } }}>
            <X size={20} />
          </IconButton>
        </Stack>
      </Box>

      {/* Tabs */}
      <Tabs
        value={activeTab}
        onChange={(_, v) => setActiveTab(v)}
        sx={{
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          px: 2,
          '& .MuiTab-root': {
            color: 'rgba(255,255,255,0.4)',
            fontFamily: 'Orbitron',
            fontSize: '0.65rem',
            fontWeight: 800,
            letterSpacing: 1.5,
            py: 2.5,
            minWidth: 120,
            transition: 'all 0.3s',
            '&.Mui-selected': { color: '#00f3ff', textShadow: '0 0 10px rgba(0, 243, 255, 0.5)' }
          },
          '& .MuiTabs-indicator': { bgcolor: '#00f3ff', height: 2, boxShadow: '0 0 10px #00f3ff' }
        }}
      >
        <Tab label="SCAN HISTORY" />
        <Tab label="TASKS" />
      </Tabs>

      {/* Content */}
      <Box sx={{ flexGrow: 1, overflow: 'auto', p: 3 }}>
        {isLoading ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 2, opacity: 0.5 }}>
            <CircularProgress size={24} sx={{ color: '#00f3ff' }} />
            <Typography sx={{ fontFamily: 'Orbitron', fontSize: '0.6rem', letterSpacing: 2 }}>SYNCING DATA...</Typography>
          </Box>
        ) : activeTab === 0 ? (
          <Box>
            {status?.scans?.scanning?.length > 0 && (
              <>
                <SectionHeader title="CURRENTLY SCANNING" count={status.scans.scanning.length} />
                {status.scans.scanning.map((scan: any) => (
                  <ScanItem key={scan.id} scan={scan} onStop={stopScan.mutate} onDelete={deleteScan.mutate} />
                ))}
              </>
            )}

            <SectionHeader title="RECENTLY COMPLETED" />
            {status?.scans?.completed?.length > 0 ? (
              status.scans.completed.map((scan: any) => (
                <ScanItem key={scan.id} scan={scan} onStop={stopScan.mutate} onDelete={deleteScan.mutate} />
              ))
            ) : (
              <Box sx={{ p: 4, textAlign: 'center', bgcolor: 'rgba(255,255,255,0.02)', borderRadius: 2, border: '1px dashed rgba(255,255,255,0.1)' }}>
                <Typography sx={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.3)' }}>No recent scans found.</Typography>
              </Box>
            )}
          </Box>
        ) : (
          <Box>
            {status?.tasks?.running?.length > 0 ? (
              <>
                <Box sx={{
                  mb: 3,
                  p: 1.5,
                  bgcolor: '#00f3ff22',
                  borderRadius: 1,
                  border: '1px solid #00f3ff44',
                  textAlign: 'center'
                }}>
                  <Typography sx={{ fontFamily: 'Orbitron', fontSize: '0.65rem', fontWeight: 900, color: '#00f3ff', letterSpacing: 1 }}>
                    {status.tasks.running.length} TASKS ARE CURRENTLY RUNNING
                  </Typography>
                </Box>
                <SectionHeader title="CURRENTLY RUNNING" />
                {status.tasks.running.map((task: any) => (
                  <TaskItem key={task.id} task={task} onStop={() => { }} />
                ))}
              </>
            ) : (
              <Box sx={{ p: 4, textAlign: 'center', bgcolor: 'rgba(255,255,255,0.02)', borderRadius: 2, border: '1px dashed rgba(255,255,255,0.1)' }}>
                <Typography sx={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.3)' }}>No active tasks.</Typography>
              </Box>
            )}

            {status?.tasks?.completed?.length > 0 && (
              <>
                <SectionHeader title="RECENTLY COMPLETED" />
                {status.tasks.completed.map((task: any) => (
                  <TaskItem key={task.id} task={task} />
                ))}
              </>
            )}
          </Box>
        )}
      </Box>
    </Drawer>
  );
};
