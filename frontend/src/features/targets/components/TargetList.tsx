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
  Button,
  LinearProgress,
  Tooltip,
  TextField,
  InputAdornment,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Checkbox,
  Select,
  FormControl,
  TablePagination
} from '@mui/material';
import { 
  Search, 
  MoreVertical, 
  Activity, 
  ShieldAlert, 
  ExternalLink, 
  Play, 
  Settings,
  Plus,
  Trash2,
  Filter,
  Eye,
  ChevronRight,
  Target
} from 'lucide-react';
import { useDomains, useDeleteTargets } from '../api';
import { useParams, Link } from '@tanstack/react-router';
import { AddTargetModal } from './AddTargetModal';
import { StartScanModal } from '../../scans/components/StartScanModal';

export const TargetList: React.FC = () => {
  const { projectSlug = 'default' } = useParams({ strict: false }) as any;
  const { data: domains, isLoading, error } = useDomains(projectSlug);
  const { mutate: deleteTargets } = useDeleteTargets(projectSlug);
  
  const [isAddModalOpen, setIsAddModalOpen] = React.useState(false);
  const [startScanTargets, setStartScanTargets] = React.useState<{ ids: number[]; names: string[] } | null>(null);
  const [selectedIds, setSelectedIds] = React.useState<number[]>([]);
  const [resultsPerPage, setResultsPerPage] = React.useState(20);
  const [page, setPage] = React.useState(0);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [activeTarget, setActiveTarget] = React.useState<{ id: number; name: string } | null>(null);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, target: { id: number; name: string }) => {
    setAnchorEl(event.currentTarget);
    setActiveTarget(target);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setActiveTarget(null);
  };

  const sortedDomains = React.useMemo(() => {
    if (!domains) return [];
    return [...domains].sort((a, b) => (b.id || 0) - (a.id || 0));
  }, [domains]);

  const filteredDomains = React.useMemo(() => {
    return sortedDomains.filter(domain =>
      domain.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      domain.description?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [sortedDomains, searchQuery]);

  const paginatedDomains = React.useMemo(() => {
    return filteredDomains.slice(page * resultsPerPage, page * resultsPerPage + resultsPerPage);
  }, [filteredDomains, page, resultsPerPage]);

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked && filteredDomains) {
      setSelectedIds(filteredDomains.map(d => d.id!));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectOne = (id: number) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleDeleteMultiple = () => {
    if (selectedIds.length > 0) {
      if (window.confirm(`Are you sure you want to delete ${selectedIds.length} targets?`)) {
        deleteTargets(selectedIds);
        setSelectedIds([]);
      }
    }
  };

  if (isLoading) return <LinearProgress sx={{ bgcolor: 'rgba(0, 243, 255, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff' } }} />;

  return (
    <Box sx={{ p: 3 }}>
      {/* Top Breadcrumb Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontFamily: 'Orbitron', fontWeight: 900, color: '#fff', letterSpacing: 1 }}>
          TARGETS
        </Typography>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontFamily: 'Orbitron' }}>
          Targets {'>'} <span style={{ color: 'rgba(255,255,255,0.7)' }}>All Targets</span>
        </Typography>
      </Box>

      {/* Action Bar */}
      <Card sx={{ 
        bgcolor: 'rgba(20, 20, 35, 0.4)', 
        border: '1px solid rgba(255,255,255,0.05)',
        borderRadius: 2,
        p: 1.5,
        mb: 3,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <Button
          variant="outlined"
          startIcon={<Filter size={18} />}
          sx={{
            borderColor: '#00f3ff',
            color: '#00f3ff',
            fontFamily: 'Orbitron',
            fontWeight: 800,
            px: 3,
            '&:hover': { borderColor: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.05)' }
          }}
        >
          FILTER
        </Button>

        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <Button
            variant="contained"
            onClick={() => setIsAddModalOpen(true)}
            sx={{
              bgcolor: 'rgba(0, 243, 255, 0.1)',
              color: '#00f3ff',
              fontFamily: 'Orbitron',
              fontWeight: 700,
              fontSize: '0.75rem',
              '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)' }
            }}
          >
            Add Targets
          </Button>
          <Button
            variant="contained"
            disabled={selectedIds.length === 0}
            onClick={() => {
              const selectedDomains = domains?.filter(d => selectedIds.includes(d.id!)) || [];
              setStartScanTargets({
                ids: selectedIds,
                names: selectedDomains.map(d => d.name)
              });
            }}
            sx={{
              bgcolor: 'rgba(0, 243, 255, 0.1)',
              color: '#00f3ff',
              fontFamily: 'Orbitron',
              fontWeight: 700,
              fontSize: '0.75rem',
              '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)' },
              '&.Mui-disabled': { bgcolor: 'rgba(255,255,255,0.02)', color: 'rgba(255,255,255,0.1)' }
            }}
          >
            Scan Multiple Targets
          </Button>
          <Button
            variant="contained"
            onClick={handleDeleteMultiple}
            disabled={selectedIds.length === 0}
            sx={{
              bgcolor: 'rgba(255, 0, 60, 0.1)',
              color: '#ff003c',
              fontFamily: 'Orbitron',
              fontWeight: 700,
              fontSize: '0.75rem',
              '&:hover': { bgcolor: 'rgba(255, 0, 60, 0.2)' },
              '&.Mui-disabled': { bgcolor: 'rgba(255,255,255,0.02)', color: 'rgba(255,255,255,0.1)' }
            }}
          >
            Delete Multiple Targets
          </Button>
        </Box>
      </Card>

      {/* Main Content Card */}
      <Card sx={{ 
        bgcolor: 'rgba(10, 10, 25, 0.8)', 
        backdropFilter: 'blur(10px)', 
        border: '1px solid rgba(255,255,255,0.05)',
        borderRadius: 3,
        overflow: 'hidden'
      }}>
        {/* Table Controls */}
        <Box sx={{ p: 2.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center', bgcolor: 'rgba(255,255,255,0.02)' }}>
          <TextField 
            placeholder="Search..."
            variant="outlined"
            size="small"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(0);
            }}
            sx={{ 
              width: 280,
              '& .MuiOutlinedInput-root': {
                color: '#fff',
                bgcolor: 'rgba(255,255,255,0.05)',
                '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
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
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', fontFamily: 'Orbitron' }}>Results :</Typography>
            <Select
              value={resultsPerPage}
              onChange={(e) => {
                setResultsPerPage(Number(e.target.value));
                setPage(0);
              }}
              size="small"
              sx={{ 
                color: '#fff',
                bgcolor: 'rgba(255,255,255,0.05)',
                height: 32,
                fontSize: '0.75rem',
                fontFamily: 'Orbitron',
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1)' }
              }}
            >
              <MenuItem value={10}>10</MenuItem>
              <MenuItem value={20}>20</MenuItem>
              <MenuItem value={50}>50</MenuItem>
              <MenuItem value={100}>100</MenuItem>
            </Select>
          </Box>
        </Box>

        <TableContainer>
          <Table>
            <TableHead sx={{ bgcolor: 'rgba(50, 20, 80, 0.3)' }}>
              <TableRow>
                <TableCell padding="checkbox" sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <Checkbox 
                    indeterminate={selectedIds.length > 0 && selectedIds.length < (domains?.length || 0)}
                    checked={selectedIds.length > 0 && selectedIds.length === (domains?.length || 0)}
                    onChange={handleSelectAll}
                    sx={{ color: 'rgba(255,255,255,0.3)', '&.Mui-checked': { color: '#00f3ff' } }} 
                  />
                </TableCell>
                <TableCell sx={headerStyles}>TARGET</TableCell>
                <TableCell sx={headerStyles}>DESCRIPTION</TableCell>
                <TableCell sx={headerStyles}>ADDED ON</TableCell>
                <TableCell sx={headerStyles}>LAST SCANNED</TableCell>
                <TableCell sx={{ ...headerStyles, textAlign: 'center' }}>ACTION</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedDomains.map((domain) => (
                <TableRow 
                  key={domain.id!} 
                  selected={selectedIds.includes(domain.id!)}
                  sx={{ 
                    '&:hover': { bgcolor: 'rgba(255,255,255,0.03)' }, 
                    '&.Mui-selected': { bgcolor: 'rgba(0, 243, 255, 0.05)' },
                    transition: 'all 0.2s' 
                  }}
                >
                  <TableCell padding="checkbox" sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Checkbox 
                      checked={selectedIds.includes(domain.id!)}
                      onChange={() => handleSelectOne(domain.id!)}
                      sx={{ color: 'rgba(255,255,255,0.3)', '&.Mui-checked': { color: '#00f3ff' } }} 
                    />
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 800, color: '#fff' }}>{domain.name}</Typography>
                      {domain.most_recent_scan ? (
                        <Typography 
                          variant="caption" 
                          component="a"
                          href={`/${projectSlug}/detail/${domain.most_recent_scan}`}
                          target="_blank"
                          sx={{ 
                            color: '#00aaff', 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: 0.5, 
                            cursor: 'pointer', 
                            mt: 0.5,
                            textDecoration: 'none',
                            '&:hover': { textDecoration: 'underline' }
                          }}
                        >
                          Recent Scan <ExternalLink size={10} />
                        </Typography>
                      ) : (
                        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.2)', mt: 0.5 }}>
                          No Recent Scans
                        </Typography>
                      )}
                    </Box>
                  </Box>
                </TableCell>
                <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                      {domain.organization || 'No Organization'}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Chip 
                      label={domain.insert_date_humanized} 
                      size="small"
                      sx={{ 
                        bgcolor: 'rgba(0, 170, 255, 0.15)', 
                        color: '#00aaff', 
                        fontWeight: 700,
                        fontSize: '0.65rem',
                        borderRadius: 1,
                        height: 24,
                        border: '1px solid rgba(0, 170, 255, 0.3)'
                      }}
                    />
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Chip 
                      label={domain.start_scan_date_humanized || 'Never scanned'} 
                      size="small"
                      sx={{ 
                        bgcolor: 'rgba(0, 170, 255, 0.1)', 
                        color: '#00aaff', 
                        fontWeight: 700,
                        fontSize: '0.65rem',
                        borderRadius: 1,
                        height: 24,
                        border: '1px solid rgba(0, 170, 255, 0.2)'
                      }}
                    />
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', textAlign: 'right' }}>
                    <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                      <Button
                        size="small"
                        component={Link}
                        to={`/${projectSlug}/target/${domain.id!}/summary`}
                        startIcon={<Target size={14} />}
                        sx={{
                          bgcolor: 'rgba(0, 170, 255, 0.05)',
                          color: '#00aaff',
                          fontFamily: 'Orbitron',
                          fontSize: '0.65rem',
                          fontWeight: 700,
                          border: '1px solid rgba(0, 170, 255, 0.1)',
                          '&:hover': { bgcolor: 'rgba(0, 170, 255, 0.15)' },
                        }}
                      >
                        Target Summary
                      </Button>
                      <Button
                        size="small"
                        startIcon={<Play size={14} />}
                        onClick={() => setStartScanTargets({ ids: [domain.id!], names: [domain.name] })}
                        sx={{
                          bgcolor: 'rgba(0, 170, 255, 0.05)',
                          color: '#00aaff',
                          fontFamily: 'Orbitron',
                          fontSize: '0.65rem',
                          fontWeight: 700,
                          border: '1px solid rgba(0, 170, 255, 0.1)',
                          '&:hover': { bgcolor: 'rgba(0, 170, 255, 0.15)' }
                        }}
                      >
                        Initiate Scan
                      </Button>
                      <IconButton 
                        size="small" 
                        onClick={(e) => handleMenuOpen(e, { id: domain.id!, name: domain.name })}
                        sx={{ color: 'rgba(0, 170, 255, 0.5)', bgcolor: 'rgba(0, 170, 255, 0.05)', borderRadius: 1 }}
                      >
                        <MoreVertical size={18} />
                      </IconButton>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={filteredDomains.length}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={resultsPerPage}
          onRowsPerPageChange={(e) => {
            setResultsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          sx={{
            color: 'rgba(255,255,255,0.4)',
            borderTop: '1px solid rgba(255,255,255,0.05)',
            '.MuiTablePagination-selectIcon': { color: 'rgba(255,255,255,0.4)' },
            '.MuiTablePagination-actions': { color: 'rgba(255,255,255,0.4)' },
            '.MuiTablePagination-toolbar': { minHeight: 48 }
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
              border: '1px solid rgba(0, 170, 255, 0.2)',
              borderRadius: 0,
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
              minWidth: 180,
              '& .MuiMenuItem-root': {
                fontFamily: 'Orbitron',
                fontSize: '0.7rem',
                fontWeight: 700,
                color: 'rgba(255,255,255,0.8)',
                gap: 1.5,
                py: 1.2,
                '&:hover': { bgcolor: 'rgba(0, 170, 255, 0.05)', color: '#00f3ff' },
                '& svg': { color: 'rgba(0, 170, 255, 0.5)' }
              }
            }
          }
        }}
      >
        <MenuItem onClick={() => {
          if (activeTarget) {
            setStartScanTargets({ ids: [activeTarget.id], names: [activeTarget.name] });
          }
          handleMenuClose();
        }}>
          <Play size={14} /> INITIATE SCAN
        </MenuItem>
        <MenuItem onClick={() => {
          if (activeTarget) {
            if (window.confirm(`Are you sure you want to delete target ${activeTarget.name}?`)) {
              deleteTargets([activeTarget.id]);
            }
          }
          handleMenuClose();
        }} sx={{ color: '#ff003c !important', '& svg': { color: '#ff003c !important' } }}>
          <Trash2 size={14} /> DELETE TARGET
        </MenuItem>
      </Menu>

      <AddTargetModal 
        open={isAddModalOpen} 
        onClose={() => setIsAddModalOpen(false)} 
        projectSlug={projectSlug} 
      />

      {startScanTargets && (
        <StartScanModal 
          open={!!startScanTargets}
          onClose={() => setStartScanTargets(null)}
          domainIds={startScanTargets.ids}
          domainNames={startScanTargets.names}
          projectSlug={projectSlug}
        />
      )}
    </Box>
  );
};

const headerStyles = {
  color: '#fff',
  fontWeight: 800,
  fontFamily: 'Orbitron',
  fontSize: '0.75rem',
  letterSpacing: 1,
  borderBottom: '1px solid rgba(255,255,255,0.05)',
  py: 1.5
};
