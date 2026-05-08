import React, { useState, useMemo } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  TextField, 
  InputAdornment, 
  IconButton, 
  Tooltip,
  Switch,
  Chip,
  CircularProgress,
  TablePagination
} from '@mui/material';
import { 
  Search, 
  Trash2, 
  Clock, 
  Calendar, 
  Play, 
  CheckCircle2, 
  XCircle,
  AlertCircle,
  Zap
} from 'lucide-react';
import { ConfirmDialog } from '../../../components/ConfirmDialog';
import { useScheduledScans, useToggleScheduledScan, useBulkDeleteScheduledScans } from '../api';

export const ScheduledScansPage: React.FC = () => {
  const { data, isLoading, isError } = useScheduledScans();
  const toggleMutation = useToggleScheduledScan();
  const bulkDeleteMutation = useBulkDeleteScheduledScans();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  
  // Pagination State
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Confirmation state
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmConfig, setConfirmConfig] = useState<{
    title: string;
    message: string;
    onConfirm: () => void;
    type?: 'danger' | 'info' | 'warning';
  }>({
    title: '',
    message: '',
    onConfirm: () => {},
  });

  const filteredData = useMemo(() => {
    if (!data) return [];
    return data.filter(scan => 
      scan.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      scan.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [data, searchQuery]);

  const paginatedData = useMemo(() => {
    const startIndex = page * rowsPerPage;
    return filteredData.slice(startIndex, startIndex + rowsPerPage);
  }, [filteredData, page, rowsPerPage]);

  const handlePageChange = (_: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleRowsPerPageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedIds(filteredData.map(s => s.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectOne = (id: number) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleToggle = (id: number) => {
    toggleMutation.mutate(id);
  };

  const handleDeleteMultiple = () => {
    if (selectedIds.length === 0) return;
    setConfirmConfig({
      title: 'PURGE SCHEDULED OPERATIONS',
      message: `Are you sure you want to delete ${selectedIds.length} scheduled scans? This will terminate all future automated execution for these targets.`,
      type: 'danger',
      onConfirm: () => {
        bulkDeleteMutation.mutate(selectedIds, {
          onSuccess: () => setSelectedIds([])
        });
      }
    });
    setConfirmOpen(true);
  };

  if (isError) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', color: '#ff003c' }}>
        <AlertCircle size={48} />
        <Typography variant="h6" sx={{ mt: 2, fontFamily: 'Orbitron' }}>FAILED TO LOAD TACTICAL SCHEDULES</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header Section */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        mb: 4,
        background: 'linear-gradient(90deg, rgba(0, 243, 255, 0.05) 0%, transparent 100%)',
        p: 2,
        borderRadius: 1,
        borderLeft: '4px solid #00f3ff'
      }}>
        <Box>
          <Typography variant="h4" sx={{ 
            fontFamily: 'Orbitron', 
            fontWeight: 900, 
            letterSpacing: 4,
            textShadow: '0 0 15px rgba(0, 243, 255, 0.3)',
            display: 'flex',
            alignItems: 'center',
            gap: 2
          }}>
            <Clock size={32} color="#00f3ff" />
            SCHEDULED SCANS
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', letterSpacing: 2 }}>
            TACTICAL AUTOMATION REGISTRY
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', gap: 2 }}>
          {selectedIds.length > 0 && (
            <Button
              variant="contained"
              color="error"
              startIcon={<Trash2 size={18} />}
              onClick={handleDeleteMultiple}
              sx={{ 
                fontFamily: 'Orbitron',
                fontWeight: 700,
                bgcolor: 'rgba(255, 0, 60, 0.1)',
                border: '1px solid #ff003c',
                color: '#ff003c',
                '&:hover': { bgcolor: 'rgba(255, 0, 60, 0.2)' }
              }}
            >
              PURGE {selectedIds.length} TARGETS
            </Button>
          )}
        </Box>
      </Box>

      {/* Search and Filter Panel */}
      <Box sx={{ 
        mb: 3, 
        p: 2, 
        bgcolor: 'rgba(0,0,0,0.3)', 
        borderRadius: 1, 
        border: '1px solid rgba(255,255,255,0.05)',
        display: 'flex',
        gap: 2
      }}>
        <TextField
          placeholder="SEARCH TACTICAL LOGS..."
          variant="standard"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          sx={{ 
            width: 400,
            '& .MuiInputBase-root': {
              fontFamily: 'monospace',
              color: '#00f3ff',
              fontSize: '14px',
              '&:before, &:after': { borderBottomColor: 'rgba(0, 243, 255, 0.3)' }
            }
          }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <Search size={18} color="#00f3ff" />
                </InputAdornment>
              ),
            }
          }}
        />
      </Box>

      {/* Main Table */}
      <Box sx={{ 
        bgcolor: 'rgba(10, 15, 25, 0.7)', 
        borderRadius: 1, 
        border: '1px solid rgba(0, 243, 255, 0.1)',
        overflow: 'hidden',
        position: 'relative'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid rgba(0, 243, 255, 0.2)', background: 'rgba(0, 243, 255, 0.03)' }}>
              <th style={{ padding: '16px' }}>
                <input 
                  type="checkbox" 
                  checked={selectedIds.length === filteredData.length && filteredData.length > 0}
                  onChange={handleSelectAll}
                  style={{ accentColor: '#00f3ff' }}
                />
              </th>
              <th style={{ padding: '16px', color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '12px', letterSpacing: 2 }}>DESCRIPTION</th>
              <th style={{ padding: '16px', color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '12px', letterSpacing: 2 }}>FREQUENCY</th>
              <th style={{ padding: '16px', color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '12px', letterSpacing: 2 }}>LAST RUN</th>
              <th style={{ padding: '16px', color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '12px', letterSpacing: 2, textAlign: 'center' }}>RUNS</th>
              <th style={{ padding: '16px', color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '12px', letterSpacing: 2, textAlign: 'center' }}>ONE OFF</th>
              <th style={{ padding: '16px', color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '12px', letterSpacing: 2, textAlign: 'center' }}>ENABLED</th>
              <th style={{ padding: '16px', color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '12px', letterSpacing: 2, textAlign: 'center' }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={8} style={{ padding: '100px', textAlign: 'center' }}>
                  <CircularProgress size={40} sx={{ color: '#00f3ff' }} />
                  <Typography sx={{ mt: 2, fontFamily: 'monospace', color: '#00f3ff' }}>ACCESSING TACTICAL REGISTRY...</Typography>
                </td>
              </tr>
            ) : paginatedData.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: '60px', textAlign: 'center' }}>
                  <Typography sx={{ fontFamily: 'monospace', color: 'rgba(255,255,255,0.3)' }}>NO SCHEDULED OPERATIONS DETECTED</Typography>
                </td>
              </tr>
            ) : (
              paginatedData.map((scan) => (
                <tr 
                  key={scan.id} 
                  style={{ 
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                    transition: 'background 0.2s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(0, 243, 255, 0.02)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '12px 16px' }}>
                    <input 
                      type="checkbox" 
                      checked={selectedIds.includes(scan.id)}
                      onChange={() => handleSelectOne(scan.id)}
                      style={{ accentColor: '#00f3ff' }}
                    />
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <Typography sx={{ color: '#fff', fontWeight: 600, fontSize: '13px' }}>{scan.description}</Typography>
                    <Typography sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px', fontFamily: 'monospace' }}>ID: {scan.id}</Typography>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Calendar size={14} color="#00f3ff" />
                      <Typography sx={{ color: '#00f3ff', fontSize: '11px', fontWeight: 800 }}>{scan.frequency.toUpperCase()}</Typography>
                    </Box>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <Typography sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '12px', fontFamily: 'monospace' }}>
                      {scan.last_run_at ? new Date(scan.last_run_at).toLocaleString() : 'NEVER'}
                    </Typography>
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                    <Chip 
                      label={scan.total_run_count} 
                      size="small" 
                      sx={{ 
                        height: 18, 
                        fontSize: '10px', 
                        fontWeight: 900,
                        bgcolor: 'rgba(255,255,255,0.05)',
                        color: 'rgba(255,255,255,0.7)',
                        border: '1px solid rgba(255,255,255,0.1)'
                      }} 
                    />
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                    {scan.one_off ? (
                      <CheckCircle2 size={16} color="#00ff9d" />
                    ) : (
                      <XCircle size={16} color="rgba(255,255,255,0.2)" />
                    )}
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                    <Switch 
                      size="small"
                      checked={scan.enabled}
                      onChange={() => handleToggle(scan.id)}
                      sx={{
                        '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                        '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' },
                      }}
                    />
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1 }}>
                      <Tooltip title="RUN NOW">
                        <IconButton size="small" sx={{ color: '#00ff9d', '&:hover': { bgcolor: 'rgba(0, 255, 157, 0.1)' } }}>
                          <Play size={16} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="DELETE">
                        <IconButton 
                          size="small" 
                          onClick={() => { handleSelectOne(scan.id); handleDeleteMultiple(); }}
                          sx={{ color: '#ff003c', '&:hover': { bgcolor: 'rgba(255, 0, 60, 0.1)' } }}
                        >
                          <Trash2 size={16} />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination Section */}
        <TablePagination
          component="div"
          count={filteredData.length}
          page={page}
          onPageChange={handlePageChange}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleRowsPerPageChange}
          sx={{
            color: '#00f3ff',
            fontFamily: 'monospace',
            borderTop: '1px solid rgba(0, 243, 255, 0.1)',
            '& .MuiTablePagination-selectIcon': { color: '#00f3ff' },
            '& .MuiTablePagination-actions': { color: '#00f3ff' },
            '& .MuiTablePagination-select': { fontFamily: 'monospace' },
            '& .MuiTablePagination-displayedRows': { fontFamily: 'monospace' },
          }}
        />
      </Box>

      {/* Footer Info */}
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', px: 1 }}>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>
          TOTAL RECORDS: {filteredData.length}
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: '#00ff9d' }} />
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>ACTIVE TASKS</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: 'rgba(255,255,255,0.2)' }}>
              <Zap size={8} color="#fff" />
            </Box>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>ONE OFF OPS</Typography>
          </Box>
        </Box>
      </Box>

      {/* Confirmation Dialog */}
      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => {
          confirmConfig.onConfirm();
          setConfirmOpen(false);
        }}
        title={confirmConfig.title}
        message={confirmConfig.message}
        type={confirmConfig.type}
      />
    </Box>
  );
};
