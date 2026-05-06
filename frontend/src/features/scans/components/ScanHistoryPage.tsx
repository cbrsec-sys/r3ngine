import React from 'react';
import {
  Box,
  Card,
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
  Button,
  Menu,
  MenuItem,
  Checkbox,
  TablePagination,
  Paper,
  CircularProgress,
  Snackbar,
  Alert
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
  Eye,
  Settings,
  Share2,
  Trash2,
  FileText,
  AlertTriangle,
  Download,
  Terminal,
  Shield,
  Bug,
  Layers,
  ChevronRight,
  Globe,
  AlertCircle
} from 'lucide-react';
import {
  useScansHistory,
  useStopScan,
  useDeleteScan,
  useBulkScanAction,
  useDomains
} from '../api';
import { useParams, Link as RouterLink, useNavigate } from '@tanstack/react-router';
import { ScanReportModal } from './ScanReportModal';
import { StartScanModal } from './StartScanModal';

import { timeout } from 'd3';

export const ScanHistoryPage: React.FC = () => {
  const { projectSlug = 'default' } = useParams({ strict: false }) as any;
  const navigate = useNavigate();
  const { data: scans, isLoading } = useScansHistory(projectSlug);
  const stopScanMutation = useStopScan(projectSlug);
  const deleteScanMutation = useDeleteScan(projectSlug);
  const bulkActionMutation = useBulkScanAction(projectSlug);
  const { data: domains } = useDomains(projectSlug);

  const [searchQuery, setSearchQuery] = React.useState('');
  const [page, setPage] = React.useState(0);
  const [rowsPerPage, setRowsPerPage] = React.useState(10);
  const [selected, setSelected] = React.useState<number[]>([]);
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [activeScanId, setActiveScanId] = React.useState<number | null>(null);
  const [reportScanId, setReportScanId] = React.useState<number | null>(null);
  const [reportModalOpen, setReportModalOpen] = React.useState(false);
  //const [rescanModalOpen, setRescanModalOpen] = React.useState(false);
  //const [rescanTarget, setRescanTarget] = React.useState<{ ids: number[]; names: string[] } | null>(null);
  const [snackbar, setSnackbar] = React.useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'info' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const [activeTarget, setActiveTarget] = React.useState<{ id: number; name: string } | null>(null);
  const [startScanTargets, setStartScanTargets] = React.useState<{ ids: number[]; names: string[] } | null>(null);

  const handleCloseSnackbar = () => setSnackbar(prev => ({ ...prev, open: false }));

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, _id: number, domainName: string) => {
    setAnchorEl(event.currentTarget);
    setActiveScanId(_id);
    setActiveTarget({ id: _id, name: domainName });
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setActiveScanId(null);
  };

  const handleSelectAllClick = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked && scans) {
      const newSelecteds = scans.map((n) => n.id);
      setSelected(newSelecteds);
      return;
    }
    setSelected([]);
  };

  const handleClick = (id: number) => {
    const selectedIndex = selected.indexOf(id);
    let newSelected: number[] = [];

    if (selectedIndex === -1) {
      newSelected = newSelected.concat(selected, id);
    } else if (selectedIndex === 0) {
      newSelected = newSelected.concat(selected.slice(1));
    } else if (selectedIndex === selected.length - 1) {
      newSelected = newSelected.concat(selected.slice(0, -1));
    } else if (selectedIndex > 0) {
      newSelected = newSelected.concat(
        selected.slice(0, selectedIndex),
        selected.slice(selectedIndex + 1)
      );
    }
    setSelected(newSelected);
  };

  const isSelected = (id: number) => selected.indexOf(id) !== -1;

  const filteredScans = scans?.filter(scan =>
    scan.domain?.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    scan.engine_name?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const paginatedScans = filteredScans.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  const getStatusChip = (status: number) => {
    switch (status) {
      case 2: // Success
        return <Chip label="SUCCESS" size="small" sx={{ bgcolor: 'rgba(0, 255, 98, 0.1)', color: '#00ff62', border: '1px solid rgba(0, 255, 98, 0.2)', fontSize: '0.65rem', fontWeight: 900, fontFamily: 'Orbitron' }} icon={<CheckCircle2 size={12} />} />;
      case 1: // Running
        return <Chip label="PENDING" size="small" sx={{ bgcolor: 'rgba(0, 243, 255, 0.1)', color: '#00f3ff', border: '1px solid rgba(0, 243, 255, 0.2)', fontSize: '0.65rem', fontWeight: 900, fontFamily: 'Orbitron' }} icon={<RefreshCw size={12} className="spin" />} />;
      case -1: // Pending
        return <Chip label="PENDING" size="small" sx={{ bgcolor: 'rgba(255, 171, 0, 0.1)', color: '#ffab00', border: '1px solid rgba(255, 171, 0, 0.2)', fontSize: '0.65rem', fontWeight: 900, fontFamily: 'Orbitron' }} icon={<Clock size={12} />} />;
      case 3: // Aborted
        return <Chip label="ABORTED" size="small" sx={{ bgcolor: 'rgba(255, 0, 60, 0.1)', color: '#ff003c', border: '1px solid rgba(255, 0, 60, 0.2)', fontSize: '0.65rem', fontWeight: 900, fontFamily: 'Orbitron' }} icon={<AlertTriangle size={12} />} />;
      case 0: // Failed
        return <Chip label="FAILED" size="small" sx={{ bgcolor: 'rgba(255, 0, 60, 0.1)', color: '#ff003c', border: '1px solid rgba(255, 0, 60, 0.2)', fontSize: '0.65rem', fontWeight: 900, fontFamily: 'Orbitron' }} icon={<XCircle size={12} />} />;
      default:
        return <Chip label="UNKNOWN" size="small" sx={{ bgcolor: 'rgba(255, 255, 255, 0.1)', color: '#fff', border: '1px solid rgba(255, 255, 255, 0.2)', fontSize: '0.65rem', fontWeight: 900, fontFamily: 'Orbitron' }} />;
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', mt: 10 }}>
        <CircularProgress sx={{ color: '#00f3ff' }} />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 900, fontFamily: 'Orbitron', color: '#fff', letterSpacing: 2 }}>SCAN HISTORY</Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', fontFamily: 'Orbitron', fontSize: '0.7rem' }}>
            MANAGE AND AUDIT PAST SECURITY OPERATIONS
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          {selected.length > 0 && (
            <>
              <Button
                variant="outlined"
                color="error"
                startIcon={<StopCircle size={18} />}
                onClick={() => bulkActionMutation.mutate({ action: 'bulk_stop', ids: selected })}
                sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem', fontWeight: 800, borderColor: '#ff003c', color: '#ff003c' }}
              >
                STOP SELECTED
              </Button>
              <Button
                variant="outlined"
                color="error"
                startIcon={<Trash2 size={18} />}
                onClick={() => bulkActionMutation.mutate({ action: 'bulk_delete', ids: selected })}
                sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem', fontWeight: 800, borderColor: '#ff003c', color: '#ff003c' }}
              >
                DELETE SELECTED
              </Button>
            </>
          )}
        </Box>
      </Box>

      <Card sx={{ bgcolor: 'rgba(13, 12, 20, 0.95)', border: '1px solid rgba(0, 243, 255, 0.1)', borderRadius: '0', position: 'relative', overflow: 'hidden' }}>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>
          <TextField
            placeholder="FILTER SCAN RECORDS..."
            size="small"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            sx={{
              width: 350,
              '& .MuiOutlinedInput-root': {
                color: '#fff',
                fontFamily: 'Orbitron',
                fontSize: '0.75rem',
                bgcolor: 'rgba(0, 243, 255, 0.03)',
                '& fieldset': { borderColor: 'rgba(0, 243, 255, 0.2)' },
                '&:hover fieldset': { borderColor: '#00f3ff' },
                '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
              }
            }}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <Search size={16} style={{ color: '#00f3ff' }} />
                  </InputAdornment>
                ),
              }
            }}
          />
        </Box>
        <TableContainer>
          <Table>
            <TableHead sx={{ bgcolor: 'rgba(0, 243, 255, 0.05)' }}>
              <TableRow>
                <TableCell padding="checkbox" sx={{ borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>
                  <Checkbox
                    indeterminate={selected.length > 0 && selected.length < (scans?.length || 0)}
                    checked={(scans?.length || 0) > 0 && selected.length === scans?.length}
                    onChange={handleSelectAllClick}
                    sx={{ color: 'rgba(0, 243, 255, 0.3)', '&.Mui-checked': { color: '#00f3ff' } }}
                  />
                </TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.7rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>DOMAIN / TARGET</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.7rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>SUMMARY</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.7rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>ENGINE</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.7rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>STATUS</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.7rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>PROGRESS</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.7rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>TIMELINE</TableCell>
                <TableCell sx={{ color: '#00f3ff', fontWeight: 800, fontFamily: 'Orbitron', fontSize: '0.7rem', borderBottom: '1px solid rgba(0, 243, 255, 0.1)', textAlign: 'left', width: 140 }}>ACTION</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedScans.map((scan) => {
                const isItemSelected = isSelected(scan.id);
                const displayProgress = (scan.scan_status === 2 || scan.scan_status === 0 || scan.scan_status === 3) ? 100 : (scan.current_progress || 0);
                return (
                  <TableRow
                    key={scan.id}
                    hover
                    onClick={() => handleClick(scan.id)}
                    role="checkbox"
                    aria-checked={isItemSelected}
                    selected={isItemSelected}
                    sx={{
                      '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.02) !important' },
                      '&.Mui-selected': { bgcolor: 'rgba(0, 243, 255, 0.05) !important' },
                      transition: 'all 0.2s',
                      cursor: 'pointer'
                    }}
                  >
                    <TableCell padding="checkbox" sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <Checkbox
                        checked={isItemSelected}
                        sx={{ color: 'rgba(255,255,255,0.2)', '&.Mui-checked': { color: '#00f3ff' } }}
                      />
                    </TableCell>
                    <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <Typography variant="body2" sx={{ fontWeight: 800, color: '#fff', fontFamily: 'Orbitron', fontSize: '0.8rem' }}>{scan.domain?.name}</Typography>
                      {scan.cfg_starting_point_path && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                          <Terminal size={10} style={{ color: 'rgba(255,255,255,0.3)' }} />
                          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.6rem' }}>{scan.cfg_starting_point_path}</Typography>
                        </Box>
                      )}
                    </TableCell>
                    <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Tooltip title="Subdomains Found">
                          <Box sx={{ bgcolor: 'rgba(0, 243, 255, 0.1)', color: '#00f3ff', px: 1, py: 0.5, borderRadius: '2px', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Globe size={12} />
                            <Typography variant="caption" sx={{ fontWeight: 900, fontFamily: 'Orbitron' }}>{scan.subdomain_count || 0}</Typography>
                          </Box>
                        </Tooltip>
                        <Tooltip title="Endpoints Discovered">
                          <Box sx={{ bgcolor: 'rgba(255, 171, 0, 0.1)', color: '#ffab00', px: 1, py: 0.5, borderRadius: '2px', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Layers size={12} />
                            <Typography variant="caption" sx={{ fontWeight: 900, fontFamily: 'Orbitron' }}>{scan.endpoint_count || 0}</Typography>
                          </Box>
                        </Tooltip>
                        <Tooltip title="Vulnerabilities Detected">
                          <Box sx={{ bgcolor: 'rgba(255, 0, 60, 0.1)', color: '#ff003c', px: 1, py: 0.5, borderRadius: '2px', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Bug size={12} />
                            <Typography variant="caption" sx={{ fontWeight: 900, fontFamily: 'Orbitron' }}>{scan.vulnerability_count || 0}</Typography>
                          </Box>
                        </Tooltip>
                      </Box>
                    </TableCell>
                    <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <Chip
                        label={scan.engine_name || scan.scan_type?.engine_name || 'STANDARD'}
                        size="small"
                        sx={{ bgcolor: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.7)', border: '1px solid rgba(255,255,255,0.1)', fontSize: '0.6rem', fontWeight: 800, fontFamily: 'Orbitron' }}
                      />
                    </TableCell>
                    <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      {getStatusChip(scan.scan_status)}
                    </TableCell>
                    <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', minWidth: 120 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={displayProgress}
                          sx={{
                            flexGrow: 1,
                            height: 4,
                            borderRadius: 0,
                            bgcolor: 'rgba(255,255,255,0.05)',
                            '& .MuiLinearProgress-bar': {
                              bgcolor: scan.scan_status === 0 || scan.scan_status === 3 ? '#ff003c' : '#00f3ff',
                              boxShadow: `0 0 10px ${scan.scan_status === 0 || scan.scan_status === 3 ? 'rgba(255, 0, 60, 0.5)' : 'rgba(0, 243, 255, 0.5)'}`
                            }
                          }}
                        />
                        <Typography variant="caption" sx={{ fontWeight: 900, color: '#fff', fontSize: '0.65rem', fontFamily: 'Orbitron', minWidth: 30 }}>
                          {Math.round(displayProgress)}%
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Clock size={12} style={{ color: 'rgba(0, 243, 255, 0.5)' }} />
                        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontWeight: 600, fontSize: '0.65rem' }}>
                          {scan.completed_ago || 'JUST NOW'}
                        </Typography>
                      </Box>
                      <Typography variant="caption" sx={{ display: 'block', color: 'rgba(255,255,255,0.3)', fontSize: '0.55rem', mt: 0.5 }}>
                        ELAPSED: {scan.elapsed_time || '0s'}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', textAlign: 'left' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1 }}>
                        <Button
                          variant="contained"
                          size="small"
                          component={RouterLink}
                          to={`/${projectSlug}/scan/detail/${scan.id}`}
                          sx={{
                            bgcolor: 'rgba(0, 243, 255, 0.1)',
                            color: '#00f3ff',
                            border: '1px solid rgba(0, 243, 255, 0.3)',
                            fontFamily: 'Orbitron',
                            fontSize: '0.6rem',
                            fontWeight: 900,
                            '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)' }
                          }}
                        >
                          RESULTS
                        </Button>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            const match = domains?.find(d => d.id === scan.domain.id);
                            if (!match) return;
                            setStartScanTargets({
                              ids: [match.id],
                              names: [match.name],
                            });
                          }}
                          sx={{ color: 'rgba(112, 206, 35, 0.63)', '&:hover': { color: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.1)' } }}
                        >
                          <RefreshCw size={16} />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleMenuOpen(e, scan.id, scan.domain?.name);
                          }}
                          sx={{ color: 'rgba(255,255,255,0.3)', '&:hover': { color: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.1)' } }}
                        >
                          <MoreVertical size={16} />
                        </IconButton>
                      </Box>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={filteredScans.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          sx={{
            color: 'rgba(255,255,255,0.5)',
            borderTop: '1px solid rgba(0, 243, 255, 0.1)',
            '& .MuiTablePagination-selectIcon': { color: 'rgba(255,255,255,0.5)' },
            '& .MuiTablePagination-actions': { color: '#00f3ff' }
          }}
        />
      </Card>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        slotProps={{
          paper: {
            sx: {
              bgcolor: '#0d0c14',
              border: '1px solid rgba(0, 243, 255, 0.2)',
              borderRadius: 0,
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
              minWidth: 200,
              '& .MuiMenuItem-root': {
                fontFamily: 'Orbitron',
                fontSize: '0.7rem',
                fontWeight: 700,
                color: 'rgba(255,255,255,0.8)',
                gap: 1.5,
                py: 1.2,
                '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.05)', color: '#00f3ff' },
                '& svg': { color: 'rgba(0, 243, 255, 0.5)' }
              }
            }
          }
        }}
      >
        <MenuItem onClick={handleMenuClose}>
          <Settings size={14} /> SHOW CONFIGS
        </MenuItem>
        <MenuItem onClick={() => {
          navigate({ to: `/${projectSlug}/attack_surface/${activeScanId}` });
          handleMenuClose();
        }}>
          <Share2 size={14} /> ATTACK SURFACE
        </MenuItem>
        {/* <MenuItem onClick={() => {
          if (!activeTarget) {
            setSnackbar({
              open: true,
              message: 'Failed to identify target for rescan.',
              severity: 'error'
            });

            setTimeout(() => {
              setSnackbar({ open: false, message: '', severity: 'info' });
              handleMenuClose();
            }, 3000);

            return;
          }

          setStartScanTargets({
            ids: [activeScanId || 0],
            names: [activeTarget?.name],
          });
          setTimeout(() => {
            handleMenuClose();
          }, 3000);
          //handleMenuClose();
        }}>
          <RefreshCw size={14} /> RESCAN
        </MenuItem> */}
        <MenuItem onClick={() => {
          if (activeScanId) {
            stopScanMutation.mutate(activeScanId);
            handleMenuClose();
          }
        }}>
          <StopCircle size={14} /> STOP SCAN
        </MenuItem>
        <MenuItem onClick={() => {
          if (activeScanId) {
            deleteScanMutation.mutate(activeScanId);
            handleMenuClose();
          }
        }} sx={{ color: '#ff003c !important', '& svg': { color: '#ff003c !important' } }}>
          <Trash2 size={14} /> DELETE SCAN
        </MenuItem>
        <MenuItem onClick={() => {
          if (activeScanId) {
            setReportScanId(activeScanId);
            setReportModalOpen(true);
          }
          handleMenuClose();
        }}>
          <FileText size={14} /> SCAN REPORT
        </MenuItem>
      </Menu>

      {reportScanId && (
        <ScanReportModal
          open={reportModalOpen}
          onClose={() => {
            setReportModalOpen(false);
            setReportScanId(null);
          }}
          scanId={reportScanId}
        />
      )}

      {startScanTargets && (
        <StartScanModal
          open={!!startScanTargets}
          onClose={() => setStartScanTargets(null)}
          domainIds={startScanTargets.ids}
          domainNames={startScanTargets.names}
          projectSlug={projectSlug}
        />
      )}
      {/* {rescanTarget && ( 
        <StartScanModal
          open={rescanModalOpen}
          onClose={() => {
            setRescanTarget(null)
            setRescanModalOpen(false)
          }}
          domainIds={rescanTarget.ids}
          domainNames={rescanTarget.names}
          projectSlug={projectSlug}
        />
      )*/}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={5000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          variant="filled"
          sx={{
            fontFamily: 'Orbitron',
            fontSize: '0.8rem',
            fontWeight: 700,
            bgcolor: snackbar.severity === 'success' ? 'rgba(0, 243, 255, 0.9)' :
              snackbar.severity === 'error' ? 'rgba(255, 0, 85, 0.9)' : 'rgba(0, 243, 255, 0.5)',
            color: '#000',
            border: '1px solid rgba(255,255,255,0.1)',
            '& .MuiAlert-icon': { color: '#000' }
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};
