import React, { useState } from 'react';
import {
  Box,
  Typography,
  InputBase,
  Button,
  IconButton,
  CircularProgress,
  Pagination,
  Stack,
  Tooltip,
  Menu,
  MenuItem,
  Chip
} from '@mui/material';
import {
  Search,
  Copy,
  Download,
  Filter,
  LayoutGrid,
  ChevronDown
} from 'lucide-react';

import { useEndpoints } from '../../endpoints/api';
import { TacticalPanel } from '../../../components/TacticalPanel';
import { copyToClipboard } from '../../endpoints/utils/copy';
import { useThemeTokens } from '../../../theme/useThemeTokens';

interface EndpointsTabProps {
  projectSlug: string;
  scanId?: number;
  matchedGfCounts?: Array<{ matched_gf_patterns: string; count: number }>;
  targetId?: number;
}

export const EndpointsTab: React.FC<EndpointsTabProps> = ({ projectSlug, scanId, matchedGfCounts, targetId }) => {
  const { tokens, isLight } = useThemeTokens();
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSearch, setActiveSearch] = useState('');
  const [selectedGfPattern, setSelectedGfPattern] = useState<string | undefined>(undefined);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const { data, isLoading } = useEndpoints(projectSlug, page, activeSearch, scanId, selectedGfPattern, targetId);

  const handleSearch = () => {
    setPage(1);
    setActiveSearch(searchQuery);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleSelectPattern = (pattern: string | undefined) => {
    setPage(1);
    setSelectedGfPattern(pattern);
    handleMenuClose();
  };

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return isLight ? tokens.accent.success : '#00ff62';
    if (status >= 300 && status < 400) return tokens.accent.primary;
    if (status >= 400 && status < 500) return isLight ? tokens.accent.warning : '#ffae00';
    if (status >= 500) return isLight ? tokens.accent.error : '#ff003c';
    return isLight ? tokens.text.secondary : 'rgba(255,255,255,0.4)';
  };

  return (
    <Box>
      {/* High-Fidelity Search Bar and Pattern Dropdown */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <Box sx={{
          display: 'flex',
          bgcolor: isLight ? 'rgba(0,0,0,0.02)' : 'rgba(255,255,255,0.03)',
          borderRadius: '4px',
          overflow: 'hidden',
          flex: 1,
          border: `1px solid ${isLight ? 'rgba(0,0,0,0.1)' : `${tokens.accent.primary}33`}`,
          boxShadow: `0 0 20px ${tokens.accent.primary}0D`
        }}>
          <InputBase
            placeholder={selectedGfPattern ? `Search within ${selectedGfPattern.toUpperCase()} endpoints...` : "Filter Endpoints..."}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            sx={{
              flex: 1,
              px: 3,
              py: 1.5,
              fontSize: '0.9rem',
              color: 'text.primary',
              '&::placeholder': { color: 'text.disabled', opacity: 1 }
            }}
          />
          <Button
            onClick={handleSearch}
            startIcon={<Search size={18} />}
            sx={{
              bgcolor: `${tokens.accent.primary}15`,
              color: tokens.accent.primary,
              px: 4,
              borderRadius: 0,
              fontWeight: 800,
              letterSpacing: 2,
              fontFamily: 'Orbitron',
              borderLeft: `1px solid ${isLight ? 'rgba(0,0,0,0.1)' : `${tokens.accent.primary}33`}`,
              '&:hover': { bgcolor: `${tokens.accent.primary}33` }
            }}
          >
            SEARCH
          </Button>
        </Box>

        {/* Pattern Dropdown */}
        {matchedGfCounts && matchedGfCounts.length > 0 && (
          <Box>
            <Button
              variant="outlined"
              onClick={handleMenuOpen}
              endIcon={<ChevronDown size={14} />}
              sx={{
                height: '100%',
                px: 2,
                borderColor: isLight ? 'divider' : `${tokens.accent.primary}33`,
                color: selectedGfPattern ? 'error.main' : 'text.primary',
                bgcolor: selectedGfPattern ? (isLight ? 'rgba(239, 68, 68, 0.05)' : 'rgba(255, 0, 60, 0.05)') : (isLight ? 'rgba(0,0,0,0.02)' : 'rgba(255,255,255,0.03)'),
                fontWeight: 800,
                fontSize: '0.75rem',
                letterSpacing: 1,
                '&:hover': { borderColor: tokens.accent.primary, bgcolor: `${tokens.accent.primary}0D` }
              }}
            >
              {selectedGfPattern ? `PATTERN: ${selectedGfPattern.toUpperCase()}` : 'QUERY SPECIFIC ENDPOINTS'}
            </Button>
            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleMenuClose}
              slotProps={{
                paper: {
                  sx: {
                    bgcolor: 'background.paper',
                    border: `1px solid ${isLight ? 'rgba(0,0,0,0.08)' : `${tokens.accent.primary}33`}`,
                    boxShadow: isLight ? '0 4px 20px rgba(0,0,0,0.05)' : '0 0 30px rgba(0,0,0,0.5)',
                    mt: 1,
                    '& .MuiMenuItem-root': {
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: 'text.primary',
                      px: 3,
                      py: 1,
                      '&:hover': { bgcolor: `${tokens.accent.primary}15`, color: tokens.accent.primary }
                    }
                  }
                }
              }}
            >
              <MenuItem onClick={() => handleSelectPattern(undefined)}>ALL ENDPOINTS</MenuItem>
              {matchedGfCounts.map((pattern) => (
                <MenuItem key={pattern.matched_gf_patterns} onClick={() => handleSelectPattern(pattern.matched_gf_patterns)}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', gap: 4 }}>
                    <span>{pattern.matched_gf_patterns.toUpperCase()}</span>
                    <Box component="span" sx={{ color: 'error.main', opacity: 0.8 }}>{pattern.count}</Box>
                  </Box>
                </MenuItem>
              ))}
            </Menu>
          </Box>
        )}
      </Box>

      {/* Main Tactical Panel */}
      <TacticalPanel title={selectedGfPattern ? `ENDPOINTS: ${selectedGfPattern.toUpperCase()}` : "ALL ENDPOINTS"} icon={<LayoutGrid size={14} />}>
        {/* Table Controls */}
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography sx={{ fontSize: '11px', fontWeight: 700, color: 'text.secondary', letterSpacing: 1 }}>
              RESULTS : <Box component="span" sx={{ color: tokens.accent.primary }}>{data?.count || 0}</Box>
            </Typography>
            <Box sx={{ px: 2, py: 0.5, bgcolor: `${tokens.accent.primary}0D`, borderRadius: 0.5, border: `1px solid ${tokens.accent.primary}15` }}>
              <Typography sx={{ fontSize: '10px', fontWeight: 800, color: tokens.accent.primary, fontFamily: 'Orbitron' }}>
                PAGE {page} OF {Math.ceil((data?.count || 0) / 100) || 1}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Refresh">
              <IconButton size="small" sx={{ color: 'text.secondary', border: '1px solid', borderColor: 'divider', borderRadius: 1 }}><Filter size={16} /></IconButton>
            </Tooltip>
            <Tooltip title="Export Data">
              <IconButton size="small" sx={{ color: tokens.accent.primary, bgcolor: `${tokens.accent.primary}15`, border: `1px solid ${tokens.accent.primary}33`, borderRadius: 1 }}><Download size={16} /></IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Responsive Endpoints Table */}
        <Box sx={{
          overflowX: 'auto',
          width: '100%',
          '&::-webkit-scrollbar': { height: '6px' },
          '&::-webkit-scrollbar-thumb': { bgcolor: `${tokens.accent.primary}33`, borderRadius: '3px' }
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'auto' }}>
            <thead>
              <tr style={{
                textAlign: 'left',
                borderBottom: `1px solid ${isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.1)'}`,
                backgroundColor: isLight ? 'rgba(0,0,0,0.02)' : 'rgba(255,255,255,0.02)'
              }}>
                <th style={{ padding: '12px 16px', color: tokens.accent.primary, fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>HTTP URL</th>
                <th style={{ padding: '12px 16px', color: tokens.accent.primary, fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>STATUS</th>
                <Box component="th" sx={{ display: { xs: 'none', md: 'table-cell' }, padding: '12px 16px', color: tokens.accent.primary, fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>PAGE TITLE</Box>
                <Box component="th" sx={{ display: { xs: 'none', sm: 'table-cell' }, padding: '12px 16px', color: tokens.accent.primary, fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>TAGS</Box>
                <Box component="th" sx={{ display: { xs: 'none', lg: 'table-cell' }, padding: '12px 16px', color: tokens.accent.primary, fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>INFO</Box>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} style={{ padding: '40px', textAlign: 'center' }}>
                    <CircularProgress size={24} sx={{ color: tokens.accent.primary }} />
                  </td>
                </tr>
              ) : data?.results.map((endpoint) => (
                <tr key={endpoint.id} style={{ borderBottom: 1, borderColor: 'divider', transition: 'background 0.2s' }}>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography sx={{
                          fontSize: '12px',
                          fontWeight: 500,
                          color: 'text.primary',
                          textDecoration: 'none',
                          wordBreak: 'break-all',
                          '&:hover': { color: tokens.accent.primary }
                        }} component="a" href={endpoint.http_url} target="_blank">
                          {endpoint.http_url}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={() => copyToClipboard(endpoint.http_url)}
                          sx={{ color: 'text.disabled', p: 0.5, '&:hover': { color: tokens.accent.primary } }}
                        >
                          <Copy size={12} />
                        </IconButton>
                      </Box>

                      {/* Tech Badges */}
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {endpoint.webserver && (
                          <Box sx={{ px: 0.8, py: 0.2, bgcolor: isLight ? 'rgba(112, 0, 255, 0.08)' : 'rgba(112, 0, 255, 0.1)', border: `1px solid ${isLight ? 'rgba(112, 0, 255, 0.2)' : 'rgba(112, 0, 255, 0.3)'}`, borderRadius: 0.5 }}>
                            <Typography sx={{ fontSize: '9px', fontWeight: 800, color: isLight ? '#7c3aed' : '#7000ff' }}>{endpoint.webserver}</Typography>
                          </Box>
                        )}
                        {endpoint.techs?.map(tech => (
                          <Box key={tech.id} sx={{ px: 0.8, py: 0.2, bgcolor: `${tokens.accent.primary}15`, border: `1px solid ${tokens.accent.primary}4D`, borderRadius: 0.5 }}>
                            <Typography sx={{ fontSize: '9px', fontWeight: 800, color: tokens.accent.primary }}>{tech.name}</Typography>
                          </Box>
                        ))}
                      </Box>
                    </Box>
                  </td>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Box sx={{
                      display: 'inline-flex',
                      px: 1.2,
                      py: 0.4,
                      borderRadius: 0.5,
                      bgcolor: `${getStatusColor(endpoint.http_status)}15`,
                      border: `1px solid ${getStatusColor(endpoint.http_status)}44`
                    }}>
                      <Typography sx={{ fontSize: '10px', fontWeight: 900, color: getStatusColor(endpoint.http_status), fontFamily: 'monospace' }}>
                        {endpoint.http_status}
                      </Typography>
                    </Box>
                  </td>
                  <Box component="td" sx={{ display: { xs: 'none', md: 'table-cell' }, padding: '16px', verticalAlign: 'top' }}>
                    <Typography sx={{ fontSize: '11px', color: 'text.secondary', fontWeight: 500, fontStyle: endpoint.page_title ? 'normal' : 'italic' }}>
                      {endpoint.page_title || 'No Title Available'}
                    </Typography>
                  </Box>
                  <Box component="td" sx={{ display: { xs: 'none', sm: 'table-cell' }, padding: '16px', verticalAlign: 'top' }}>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {endpoint.matched_gf_patterns && endpoint.matched_gf_patterns.split(',').map((tag) => (
                        <Chip
                          key={tag}
                          label={tag.toUpperCase()}
                          size="small"
                          sx={{
                            height: 16,
                            fontSize: '8px',
                            fontWeight: 900,
                            bgcolor: `${tokens.accent.primary}15`,
                            color: tokens.accent.primary,
                            border: `1px solid ${tokens.accent.primary}33`,
                            borderRadius: 0.5
                          }}
                        />
                      ))}
                    </Box>
                  </Box>
                  <Box component="td" sx={{ display: { xs: 'none', lg: 'table-cell' }, padding: '16px', verticalAlign: 'top' }}>
                    <Stack spacing={0.5}>
                      <Typography sx={{ fontSize: '10px', color: 'text.secondary', fontFamily: 'monospace' }}>
                        TIME: {endpoint.response_time ? `${endpoint.response_time.toFixed(3)}s` : 'N/A'}
                      </Typography>
                    </Stack>
                  </Box>

                </tr>
              ))}
              {(!isLoading && data?.results.length === 0) && (
                <tr>
                  <td colSpan={5} style={{ padding: '60px', textAlign: 'center' }}>
                    <Typography sx={{ color: 'text.disabled', fontFamily: 'Orbitron', fontSize: '0.8rem' }}>ZERO ENDPOINTS DETECTED</Typography>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Box>

        {/* Tactical Pagination */}
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'center', borderTop: '1px solid', borderColor: 'divider' }}>
          <Pagination
            count={Math.ceil((data?.count || 0) / 100)}
            page={page}
            onChange={(_, v) => setPage(v)}
            size="small"
            sx={{
              '& .MuiPaginationItem-root': {
                color: 'text.secondary',
                borderColor: 'divider',
                fontFamily: 'Orbitron',
                fontSize: '10px',
                '&.Mui-selected': {
                  bgcolor: `${tokens.accent.primary}15`,
                  color: tokens.accent.primary,
                  borderColor: tokens.accent.primary
                },
                '&:hover': {
                  bgcolor: 'action.hover'
                }
              }
            }}
          />
        </Box>
      </TacticalPanel>
    </Box>
  );
};
