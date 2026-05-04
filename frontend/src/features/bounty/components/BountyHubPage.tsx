import React, { useState, useMemo } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Avatar,
  Chip,
  Stack,
  TextField,
  InputAdornment,
  IconButton,
  Button,
  FormControl,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  Tooltip,
  Divider,
  Alert
} from '@mui/material';
import {
  Search,
  Filter,
  ArrowUpDown,
  ExternalLink,
  Info,
  Bookmark,
  CheckCircle2,
  XCircle,
  DownloadCloud,
  Globe,
  PlusCircle,
  Folder,
  Zap,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  DollarSign,
  Flag
} from 'lucide-react';
import { useParams } from '@tanstack/react-router';
import { useBountyPrograms, useProgramDetails, useImportPrograms } from '../api';
import { HackerOneProgram } from '../types';

const PROGRAM_CARD_STYLE = {
  bgcolor: 'rgba(255, 255, 255, 0.02)',
  border: '1px solid rgba(255, 255, 255, 0.05)',
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  cursor: 'pointer',
  position: 'relative',
  overflow: 'hidden',
  height: '100%',
  '&:hover': {
    border: '1px solid rgba(0, 243, 255, 0.3)',
    boxShadow: '0 0 20px rgba(0, 243, 255, 0.1)',
    transform: 'translateY(-4px)'
  },
  '&.selected': {
    border: '1px solid #00f3ff',
    bgcolor: 'rgba(0, 243, 255, 0.05)',
    boxShadow: '0 0 25px rgba(0, 243, 255, 0.2)',
  }
};

export const BountyHubPage: React.FC = () => {
  const { projectSlug } = useParams({ strict: false });
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('All');
  const [showClosed, setShowClosed] = useState(false);
  const [showBookmarked, setShowBookmarked] = useState(false);
  const [sortBy, setSortBy] = useState('age-desc');
  const [selectedHandles, setSelectedHandles] = useState<string[]>([]);
  const [detailHandle, setDetailHandle] = useState<string | null>(null);

  const [sortKey, sortOrder] = sortBy.split('-');
  const { data: programs, isLoading, error } = useBountyPrograms({ 
    sort_by: sortKey, 
    sort_order: sortOrder,
    bookmarked: showBookmarked 
  });

  const { data: details, isLoading: isLoadingDetails } = useProgramDetails(detailHandle);
  const importMutation = useImportPrograms();

  const filteredPrograms = useMemo(() => {
    if (!programs) return [];
    return programs.filter(p => {
      const matchesSearch = p.attributes.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                           p.attributes.handle.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesFilter = filterType === 'All' || 
                           (filterType === 'Bounty Eligible' && p.attributes.offers_bounties) ||
                           (filterType === 'VDP' && !p.attributes.offers_bounties) ||
                           (filterType === 'Private Programs' && p.attributes.state === 'private_mode');
      
      const matchesClosed = showClosed || p.attributes.submission_state === 'open';

      return matchesSearch && matchesFilter && matchesClosed;
    });
  }, [programs, searchTerm, filterType, showClosed]);

  const toggleSelection = (handle: string) => {
    setSelectedHandles(prev => 
      prev.includes(handle) ? prev.filter(h => h !== handle) : [...prev, handle]
    );
  };

  const handleImport = async () => {
    if (selectedHandles.length === 0 || !projectSlug) return;
    try {
      await importMutation.mutateAsync({ handles: selectedHandles, projectSlug });
      setSelectedHandles([]);
      // Success alert logic here (e.g. using a global toast system)
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <Box sx={{ p: 4, bgcolor: '#0a0a0a', minHeight: '100vh' }}>
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ 
            fontFamily: 'Orbitron', 
            fontWeight: 900, 
            color: '#fff',
            textShadow: '0 0 15px rgba(0, 243, 255, 0.3)',
            mb: 1 
          }}>
            BOUNTY_HUB
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', letterSpacing: 1 }}>
            INTEGRATED_VULNERABILITY_RESOURCES_V3
          </Typography>
        </Box>

        <Stack direction="row" spacing={2}>
          {selectedHandles.length > 0 && (
            <Button
              variant="outlined"
              onClick={() => setSelectedHandles([])}
              sx={{ color: 'rgba(255,255,255,0.6)', borderColor: 'rgba(255,255,255,0.2)' }}
            >
              CLEAR_SELECTIONS ({selectedHandles.length})
            </Button>
          )}
          <Button
            variant="contained"
            disabled={selectedHandles.length === 0 || importMutation.isPending}
            onClick={handleImport}
            startIcon={<DownloadCloud size={18} />}
            sx={{
              bgcolor: '#00f3ff',
              color: '#000',
              fontFamily: 'Orbitron',
              fontWeight: 900,
              '&:hover': { bgcolor: '#00d8e4', boxShadow: '0 0 20px rgba(0, 243, 255, 0.4)' }
            }}
          >
            {importMutation.isPending ? 'IMPORTING...' : `IMPORT_PROGRAMS`}
          </Button>
        </Stack>
      </Stack>

      {/* Filters Bar */}
      <Box sx={{ 
        p: 2, 
        bgcolor: 'rgba(255,255,255,0.02)', 
        border: '1px solid rgba(255,255,255,0.05)',
        borderRadius: 2,
        mb: 4
      }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              placeholder="Search programs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: <Search size={18} style={{ color: 'rgba(255,255,255,0.3)', marginRight: 8 }} />
              }}
              sx={{ '& .MuiOutlinedInput-root': { bgcolor: 'rgba(255,255,255,0.01)' } }}
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <FormControl fullWidth size="small">
              <Select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                sx={{ color: '#fff', bgcolor: 'rgba(255,255,255,0.01)' }}
              >
                <MenuItem value="All">All Types</MenuItem>
                <MenuItem value="Bounty Eligible">Bounty Eligible</MenuItem>
                <MenuItem value="VDP">VDP Only</MenuItem>
                <MenuItem value="Private Programs">Private Only</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={2}>
            <FormControl fullWidth size="small">
              <Select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                sx={{ color: '#fff', bgcolor: 'rgba(255,255,255,0.01)' }}
              >
                <MenuItem value="age-desc">Newest First</MenuItem>
                <MenuItem value="age-asc">Oldest First</MenuItem>
                <MenuItem value="name-asc">Name (A-Z)</MenuItem>
                <MenuItem value="name-desc">Name (Z-A)</MenuItem>
                <MenuItem value="reports-desc">Most Reports</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <Stack direction="row" spacing={2} justifyContent="flex-end">
              <FormControlLabel
                control={<Checkbox checked={showClosed} onChange={(e) => setShowClosed(e.target.checked)} />}
                label={<Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>Show Closed</Typography>}
              />
              <FormControlLabel
                control={<Checkbox checked={showBookmarked} onChange={(e) => setShowBookmarked(e.target.checked)} />}
                label={<Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>Bookmarked</Typography>}
              />
            </Stack>
          </Grid>
        </Grid>
      </Box>

      {/* Grid */}
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
          <CircularProgress sx={{ color: '#00f3ff' }} />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ bgcolor: 'rgba(211, 47, 47, 0.1)', color: '#ff5252' }}>
          Failed to load programs. Ensure HackerOne API keys are configured.
        </Alert>
      ) : (
        <Grid container spacing={3}>
          {filteredPrograms.map((p) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={p.id}>
              <Card 
                className={selectedHandles.includes(p.attributes.handle) ? 'selected' : ''}
                sx={PROGRAM_CARD_STYLE}
                onClick={() => toggleSelection(p.attributes.handle)}
              >
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
                    <Avatar 
                      src={p.attributes.profile_picture} 
                      variant="rounded"
                      sx={{ width: 48, height: 48, border: '1px solid rgba(255,255,255,0.1)' }}
                    />
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="subtitle1" noWrap sx={{ color: '#fff', fontWeight: 600 }}>
                        {p.attributes.name}
                        {p.attributes.bookmarked && <Bookmark size={14} fill="#ffd600" color="#ffd600" style={{ marginLeft: 6 }} />}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(0, 243, 255, 0.7)', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        @{p.attributes.handle}
                        <ExternalLink size={10} />
                      </Typography>
                    </Box>
                  </Stack>

                  <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap', gap: 0.5 }}>
                    <Chip 
                      label={p.attributes.submission_state === 'open' ? 'OPEN' : 'CLOSED'} 
                      size="small"
                      sx={{ 
                        height: 18, fontSize: '0.65rem', fontWeight: 900,
                        bgcolor: p.attributes.submission_state === 'open' ? 'rgba(0, 255, 0, 0.1)' : 'rgba(255, 0, 0, 0.1)',
                        color: p.attributes.submission_state === 'open' ? '#00ff00' : '#ff5252',
                        border: `1px solid ${p.attributes.submission_state === 'open' ? 'rgba(0, 255, 0, 0.2)' : 'rgba(255, 0, 0, 0.2)'}`
                      }} 
                    />
                    <Chip 
                      label={p.attributes.state === 'public_mode' ? 'PUBLIC' : 'PRIVATE'} 
                      size="small"
                      sx={{ height: 18, fontSize: '0.65rem', fontWeight: 900, bgcolor: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.6)' }} 
                    />
                    {p.attributes.offers_bounties ? (
                      <Chip label="BOUNTY" size="small" sx={{ height: 18, fontSize: '0.65rem', fontWeight: 900, bgcolor: 'rgba(0, 243, 255, 0.1)', color: '#00f3ff' }} />
                    ) : (
                      <Chip label="VDP" size="small" sx={{ height: 18, fontSize: '0.65rem', fontWeight: 900, bgcolor: 'rgba(255, 152, 0, 0.1)', color: '#ff9800' }} />
                    )}
                  </Stack>

                  <Grid container spacing={1} sx={{ mb: 2 }}>
                    <Grid item xs={6}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Flag size={12} color="rgba(255,255,255,0.4)" />
                        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                          Reports: {p.attributes.number_of_reports_for_user}
                        </Typography>
                      </Stack>
                    </Grid>
                    <Grid item xs={6}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <DollarSign size={12} color="rgba(255,255,255,0.4)" />
                        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                          Earnings: ${p.attributes.bounty_earned_for_user.toFixed(0)}
                        </Typography>
                      </Stack>
                    </Grid>
                  </Grid>

                  <Divider sx={{ mb: 1.5, borderColor: 'rgba(255,255,255,0.05)' }} />

                  <Button
                    fullWidth
                    size="small"
                    startIcon={<Info size={14} />}
                    onClick={(e) => {
                      e.stopPropagation();
                      setDetailHandle(p.attributes.handle);
                    }}
                    sx={{ color: 'rgba(255,255,255,0.6)', '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' } }}
                  >
                    SEE_DETAILS
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Details Dialog */}
      <Dialog 
        open={!!detailHandle} 
        onClose={() => setDetailHandle(null)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: { bgcolor: '#0d0d0d', border: '1px solid rgba(255,255,255,0.1)', backgroundImage: 'none' }
        }}
      >
        {isLoadingDetails ? (
          <Box sx={{ p: 4, textAlign: 'center' }}><CircularProgress /></Box>
        ) : details && (
          <>
            <DialogTitle sx={{ p: 3, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <Stack direction="row" spacing={2} alignItems="center">
                <Avatar src={details.attributes.profile_picture} sx={{ width: 40, height: 40 }} />
                <Box>
                  <Typography variant="h6" sx={{ color: '#fff', fontFamily: 'Orbitron' }}>{details.attributes.name}</Typography>
                  <Typography variant="caption" sx={{ color: '#00f3ff' }}>@{details.attributes.handle}</Typography>
                </Box>
              </Stack>
            </DialogTitle>
            <DialogContent sx={{ p: 3 }}>
              <Grid container spacing={4}>
                <Grid item xs={12} md={7}>
                  <Typography variant="subtitle2" sx={{ color: 'rgba(0, 243, 255, 0.7)', mb: 2, letterSpacing: 1 }}>ASSETS_ON_SCOPE</Typography>
                  <Stack spacing={2}>
                    {details.relationships.structured_scopes.data.length > 0 ? (
                      details.relationships.structured_scopes.data.map((scope) => (
                        <Box key={scope.id} sx={{ 
                          p: 1.5, 
                          bgcolor: 'rgba(255,255,255,0.02)', 
                          border: '1px solid rgba(255,255,255,0.05)',
                          borderRadius: 1,
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}>
                          <Stack direction="row" spacing={1.5} alignItems="center">
                            <Box sx={{ color: 'rgba(255,255,255,0.3)' }}>
                              {scope.attributes.asset_type === 'DOMAIN' ? <Globe size={16} /> : <PlusCircle size={16} />}
                            </Box>
                            <Box>
                              <Typography variant="body2" sx={{ color: '#fff', fontWeight: 600 }}>{scope.attributes.asset_identifier}</Typography>
                              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>{scope.attributes.asset_type}</Typography>
                            </Box>
                          </Stack>
                          <Button size="small" variant="text" startIcon={<PlusCircle size={14} />} sx={{ color: '#00f3ff' }}>
                            ADD
                          </Button>
                        </Box>
                      ))
                    ) : (
                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.4)' }}>No structured scope found.</Typography>
                    )}
                  </Stack>
                </Grid>
                <Grid item xs={12} md={5}>
                  <Stack spacing={3}>
                    <Box>
                      <Typography variant="subtitle2" sx={{ color: 'rgba(0, 243, 255, 0.7)', mb: 1.5, letterSpacing: 1 }}>STATS</Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={6}>
                          <Box sx={{ p: 2, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: 1, textAlign: 'center' }}>
                            <Typography variant="h5" sx={{ color: '#fff', fontWeight: 900 }}>{details.attributes.number_of_reports_for_user || 0}</Typography>
                            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>REPORTS</Typography>
                          </Box>
                        </Grid>
                        <Grid item xs={6}>
                          <Box sx={{ p: 2, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: 1, textAlign: 'center' }}>
                            <Typography variant="h5" sx={{ color: '#fff', fontWeight: 900 }}>${(details.attributes.bounty_earned_for_user || 0).toFixed(0)}</Typography>
                            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>EARNED</Typography>
                          </Box>
                        </Grid>
                      </Grid>
                    </Box>
                    <Box>
                      <Typography variant="subtitle2" sx={{ color: 'rgba(0, 243, 255, 0.7)', mb: 1.5, letterSpacing: 1 }}>PROGRAM_INFO</Typography>
                      <Stack spacing={1}>
                        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)', display: 'flex', alignItems: 'center', gap: 1 }}>
                          <CheckCircle2 size={14} color="#00ff00" /> Active since {new Date(details.attributes.started_accepting_at).toLocaleDateString()}
                        </Typography>
                        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)', display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Zap size={14} color="#00f3ff" /> {details.attributes.currency.toUpperCase()} Currency
                        </Typography>
                      </Stack>
                    </Box>
                  </Stack>
                </Grid>
              </Grid>
            </DialogContent>
            <DialogActions sx={{ p: 3, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              <Button onClick={() => setDetailHandle(null)} sx={{ color: 'rgba(255,255,255,0.6)' }}>CLOSE</Button>
              <Button 
                variant="contained" 
                startIcon={<DownloadCloud size={16} />}
                onClick={() => {
                  toggleSelection(details.attributes.handle);
                  setDetailHandle(null);
                }}
                sx={{ bgcolor: '#00f3ff', color: '#000', fontWeight: 900, fontFamily: 'Orbitron' }}
              >
                SELECT_FOR_IMPORT
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};
