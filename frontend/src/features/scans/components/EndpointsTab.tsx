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
  MenuItem
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

interface EndpointsTabProps {
  projectSlug: string;
  scanId?: number;
  matchedGfCounts?: Array<{ matched_gf_patterns: string; count: number }>;
  targetId?: number;
}

export const EndpointsTab: React.FC<EndpointsTabProps> = ({ projectSlug, scanId, matchedGfCounts, targetId }) => {
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
    if (status >= 200 && status < 300) return '#00ff62';
    if (status >= 300 && status < 400) return '#00f3ff';
    if (status >= 400 && status < 500) return '#ffae00';
    if (status >= 500) return '#ff003c';
    return '#888';
  };

  return (
    <Box>
      {/* High-Fidelity Search Bar and Pattern Dropdown */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <Box sx={{
          display: 'flex',
          bgcolor: 'rgba(255,255,255,0.03)',
          borderRadius: '4px',
          overflow: 'hidden',
          flex: 1,
          border: '1px solid rgba(0, 243, 255, 0.2)',
          boxShadow: '0 0 20px rgba(0, 243, 255, 0.05)'
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
              color: '#fff',
              '&::placeholder': { color: 'rgba(255,255,255,0.3)', opacity: 1 }
            }}
          />
          <Button
            onClick={handleSearch}
            startIcon={<Search size={18} />}
            sx={{
              bgcolor: 'rgba(0, 243, 255, 0.1)',
              color: '#00f3ff',
              px: 4,
              borderRadius: 0,
              fontWeight: 800,
              letterSpacing: 2,
              fontFamily: 'Orbitron',
              borderLeft: '1px solid rgba(0, 243, 255, 0.2)',
              '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)' }
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
                borderColor: 'rgba(0, 243, 255, 0.2)',
                color: selectedGfPattern ? '#ff003c' : '#fff',
                bgcolor: selectedGfPattern ? 'rgba(255, 0, 60, 0.05)' : 'rgba(255,255,255,0.03)',
                fontWeight: 800,
                fontSize: '0.75rem',
                letterSpacing: 1,
                '&:hover': { borderColor: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.05)' }
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
                    bgcolor: '#0a0a0f',
                    border: '1px solid rgba(0, 243, 255, 0.2)',
                    boxShadow: '0 0 30px rgba(0,0,0,0.5)',
                    mt: 1,
                    '& .MuiMenuItem-root': {
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: 'rgba(255,255,255,0.7)',
                      px: 3,
                      py: 1,
                      '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.1)', color: '#00f3ff' }
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
                    <Box component="span" sx={{ color: '#ff003c', opacity: 0.8 }}>{pattern.count}</Box>
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
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography sx={{ fontSize: '11px', fontWeight: 700, color: 'rgba(255,255,255,0.5)', letterSpacing: 1 }}>
              RESULTS : <Box component="span" sx={{ color: '#00f3ff' }}>{data?.count || 0}</Box>
            </Typography>
            <Box sx={{ px: 2, py: 0.5, bgcolor: 'rgba(0, 243, 255, 0.05)', borderRadius: 0.5, border: '1px solid rgba(0, 243, 255, 0.1)' }}>
              <Typography sx={{ fontSize: '10px', fontWeight: 800, color: '#00f3ff', fontFamily: 'Orbitron' }}>
                PAGE {page} OF {Math.ceil((data?.count || 0) / 100) || 1}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Refresh">
              <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.5)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 1 }}><Filter size={16} /></IconButton>
            </Tooltip>
            <Tooltip title="Export Data">
              <IconButton size="small" sx={{ color: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.1)', border: '1px solid rgba(0, 243, 255, 0.2)', borderRadius: 1 }}><Download size={16} /></IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Responsive Endpoints Table */}
        <Box sx={{
          overflowX: 'auto',
          width: '100%',
          '&::-webkit-scrollbar': { height: '6px' },
          '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(0, 243, 255, 0.2)', borderRadius: '3px' }
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '1000px' }}>
            <thead>
              <tr style={{
                textAlign: 'left',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                backgroundColor: 'rgba(255,255,255,0.02)'
              }}>
                <th style={{ width: '40%', padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>HTTP URL</th>
                <th style={{ width: '10%', padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>STATUS</th>
                <th style={{ width: '25%', padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>PAGE TITLE</th>
                <th style={{ width: '15%', padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>TAGS</th>
                <th style={{ width: '10%', padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>INFO</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} style={{ padding: '40px', textAlign: 'center' }}>
                    <CircularProgress size={24} sx={{ color: '#00f3ff' }} />
                  </td>
                </tr>
              ) : data?.results.map((endpoint) => (
                <tr key={endpoint.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', transition: 'background 0.2s' }}>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography sx={{
                          fontSize: '12px',
                          fontWeight: 500,
                          color: '#fff',
                          textDecoration: 'none',
                          wordBreak: 'break-all',
                          '&:hover': { color: '#00f3ff' }
                        }} component="a" href={endpoint.http_url} target="_blank">
                          {endpoint.http_url}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={() => copyToClipboard(endpoint.http_url)}
                          sx={{ color: 'rgba(255,255,255,0.2)', p: 0.5, '&:hover': { color: '#00f3ff' } }}
                        >
                          <Copy size={12} />
                        </IconButton>
                      </Box>

                      {/* Tech Badges */}
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {endpoint.webserver && (
                          <Box sx={{ px: 0.8, py: 0.2, bgcolor: 'rgba(112, 0, 255, 0.1)', border: '1px solid rgba(112, 0, 255, 0.3)', borderRadius: 0.5 }}>
                            <Typography sx={{ fontSize: '9px', fontWeight: 800, color: '#7000ff' }}>{endpoint.webserver}</Typography>
                          </Box>
                        )}
                        {endpoint.techs?.map(tech => (
                          <Box key={tech.id} sx={{ px: 0.8, py: 0.2, bgcolor: 'rgba(0, 243, 255, 0.1)', border: '1px solid rgba(0, 243, 255, 0.3)', borderRadius: 0.5 }}>
                            <Typography sx={{ fontSize: '9px', fontWeight: 800, color: '#00f3ff' }}>{tech.name}</Typography>
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
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Typography sx={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)', fontWeight: 500, fontStyle: endpoint.page_title ? 'normal' : 'italic' }}>
                      {endpoint.page_title || 'No Title'}
                    </Typography>
                  </td>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      {endpoint.matched_gf_patterns?.split(',').map((tag, idx) => (
                        <Box key={idx} sx={{
                          px: 1,
                          py: 0.2,
                          bgcolor: 'rgba(255, 0, 60, 0.1)',
                          border: '1px solid rgba(255, 0, 60, 0.3)',
                          borderRadius: 0.5,
                          display: 'inline-block',
                          width: 'fit-content'
                        }}>
                          <Typography sx={{ fontSize: '9px', fontWeight: 900, color: '#ff003c', letterSpacing: 0.5 }}>{tag.trim().toUpperCase()}</Typography>
                        </Box>
                      ))}
                    </Box>
                  </td>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Stack spacing={0.5}>
                      <Typography sx={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
                        TYPE: {endpoint.content_type?.split(';')[0] || 'N/A'}
                      </Typography>
                      <Typography sx={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
                        SIZE: {(endpoint.content_length / 1024).toFixed(2)} KB
                      </Typography>
                      <Typography sx={{ fontSize: '10px', color: '#00f3ff', fontWeight: 700, fontFamily: 'monospace', mt: 1 }}>
                        {endpoint.response_time ? `${endpoint.response_time.toFixed(3)}s` : ''}
                      </Typography>
                    </Stack>
                  </td>
                </tr>
              ))}
              {(!isLoading && data?.results.length === 0) && (
                <tr>
                  <td colSpan={5} style={{ padding: '60px', textAlign: 'center' }}>
                    <Typography sx={{ color: 'rgba(255,255,255,0.2)', fontFamily: 'Orbitron', fontSize: '0.8rem' }}>ZERO ENDPOINTS DETECTED</Typography>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Box>

        {/* Tactical Pagination */}
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'center', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <Pagination
            count={Math.ceil((data?.count || 0) / 100)}
            page={page}
            onChange={(_, v) => setPage(v)}
            size="small"
            sx={{
              '& .MuiPaginationItem-root': {
                color: 'rgba(255,255,255,0.4)',
                borderColor: 'rgba(255,255,255,0.1)',
                fontFamily: 'Orbitron',
                fontSize: '10px',
                '&.Mui-selected': {
                  bgcolor: 'rgba(0, 243, 255, 0.1)',
                  color: '#00f3ff',
                  borderColor: '#00f3ff'
                },
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.05)'
                }
              }
            }}
          />
        </Box>
      </TacticalPanel>
    </Box>
  );
};
