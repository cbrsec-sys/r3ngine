import React, { useState } from 'react';
import { useParams } from '@tanstack/react-router';
import {
  Box,
  Container,
  Typography,
  Grid,
  InputBase,
  Button,
  IconButton,
  Tooltip,
  CircularProgress,
  Pagination,
  Stack,
  Chip
} from '@mui/material';
import {
  Search,
  Copy,
  Download,
  Filter,
  LayoutGrid,
  ExternalLink,
  ChevronRight,
  Clock,
  Globe,
  Database
} from 'lucide-react';

import { useEndpoints } from './api';
import { TacticalPanel } from '../../components/TacticalPanel';
import { copyToClipboard } from './utils/copy';

export const EndpointsPage: React.FC = () => {
  const { projectSlug } = useParams({ from: '/$projectSlug/endpoints' });
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSearch, setActiveSearch] = useState('');

  const { data, isLoading } = useEndpoints(projectSlug, page, activeSearch);

  const handleSearch = () => {
    setPage(1);
    setActiveSearch(searchQuery);
  };

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return '#00ffaa';
    if (status >= 300 && status < 400) return '#00f3ff';
    if (status >= 400 && status < 500) return '#ffae00';
    if (status >= 500) return '#ff003c';
    return '#888';
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Tactical Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 4 }}>
        <Box>
          <Typography variant="h5" sx={{
            fontWeight: 900,
            fontFamily: 'Orbitron',
            letterSpacing: 3,
            color: '#fff',
            textTransform: 'uppercase'
          }}>
            Endpoint Discovery
          </Typography>
          <Typography sx={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', mt: 0.5, letterSpacing: 1 }}>
            V3.0 ENDPOINT INVENTORY ACTIVE
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography sx={{ fontSize: '10px', fontWeight: 800, color: 'text.secondary', letterSpacing: 2 }}>DASHBOARD</Typography>
          <ChevronRight size={12} style={{ color: '#ff00f7' }} />
          <Typography sx={{ fontSize: '10px', fontWeight: 800, color: '#fff', letterSpacing: 2 }}>ENDPOINTS</Typography>
        </Box>
      </Box>

      {/* High-Fidelity Search Bar (Image 12 Style) */}
      <Box sx={{
        display: 'flex',
        bgcolor: '#f5f5f5',
        borderRadius: '4px',
        overflow: 'hidden',
        mb: 4,
        boxShadow: '0 0 20px rgba(0, 243, 255, 0.1)'
      }}>
        <InputBase
          placeholder="Filter Endpoints"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          sx={{
            flex: 1,
            px: 3,
            py: 1.5,
            fontSize: '1rem',
            color: '#333',
            '&::placeholder': { color: '#999', opacity: 1 }
          }}
        />
        <Button
          onClick={handleSearch}
          startIcon={<Search size={18} />}
          sx={{
            bgcolor: '#002e3c',
            color: '#00f3ff',
            px: 4,
            borderRadius: 0,
            fontWeight: 800,
            letterSpacing: 2,
            borderLeft: '1px solid rgba(0, 243, 255, 0.2)',
            '&:hover': { bgcolor: '#003d50' }
          }}
        >
          SEARCH
        </Button>
      </Box>

      {/* Main Tactical Panel */}
      <TacticalPanel>
        {/* Table Controls */}
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography sx={{ fontSize: '12px', fontWeight: 700, color: 'rgba(255,255,255,0.6)' }}>
              RESULTS : 100
            </Typography>
            <Box sx={{ px: 2, py: 0.5, bgcolor: 'rgba(255,255,255,0.05)', borderRadius: 1, border: '1px solid rgba(255,255,255,0.1)' }}>
              <Typography sx={{ fontSize: '11px', fontWeight: 700, color: '#00f3ff' }}>
                Showing page {page} of {Math.ceil((data?.count || 0) / 100) || 1}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.5)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 1 }}><LayoutGrid size={16} /></IconButton>
            <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.5)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 1 }}><Filter size={16} /></IconButton>
            <IconButton size="small" sx={{ color: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.1)', border: '1px solid rgba(0, 243, 255, 0.2)', borderRadius: 1 }}><Download size={16} /></IconButton>
          </Box>
        </Box>

        {/* Responsive Endpoints Table */}
        <Box sx={{
          overflowX: 'auto',
          width: '100%',
          '&::-webkit-scrollbar': { height: '6px' },
          '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(0, 243, 255, 0.2)', borderRadius: '3px' }
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '1200px', tableLayout: 'fixed' }}>
            <thead>
              <tr style={{
                textAlign: 'left',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                backgroundColor: 'rgba(255,255,255,0.02)'
              }}>
                <th style={{ width: '400px', padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>HTTP URL</th>
                <th style={{ width: '100px', padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>STATUS</th>
                <th style={{ width: '250px', padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>PAGE TITLE</th>
                <th style={{ width: '150px', padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>TAGS</th>
                <th style={{ width: '150px', padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>CONTENT</th>
                <th style={{ width: '150px', padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>INFO</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} style={{ padding: '40px', textAlign: 'center' }}>
                    <CircularProgress size={24} sx={{ color: '#00f3ff' }} />
                  </td>
                </tr>
              ) : data?.results.map((endpoint) => (
                <tr key={endpoint.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', transition: 'background 0.2s', backgroundColor: 'transparent' }}>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography sx={{
                          fontSize: '13px',
                          fontWeight: 500,
                          color: '#00f3ff',
                          textDecoration: 'none',
                          wordBreak: 'break-all',
                          maxWidth: '400px',
                          '&:hover': { textDecoration: 'underline' }
                        }} component="a" href={endpoint.http_url} target="_blank">
                          {endpoint.http_url}
                        </Typography>
                      </Box>

                      {/* Tech Badges (Image 12 Style) */}
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 0.5 }}>
                        {endpoint.webserver && (
                          <Box sx={{
                            px: 1,
                            py: 0.2,
                            bgcolor: 'rgba(112, 0, 255, 0.1)',
                            border: '1px solid rgba(112, 0, 255, 0.3)',
                            borderRadius: 1
                          }}>
                            <Typography sx={{ fontSize: '9px', fontWeight: 800, color: '#7000ff' }}>{endpoint.webserver}</Typography>
                          </Box>
                        )}
                        {endpoint.techs?.map(tech => (
                          <Box key={tech.id} sx={{
                            px: 1,
                            py: 0.2,
                            bgcolor: 'rgba(0, 243, 255, 0.1)',
                            border: '1px solid rgba(0, 243, 255, 0.3)',
                            borderRadius: 1
                          }}>
                            <Typography sx={{ fontSize: '9px', fontWeight: 800, color: '#00f3ff' }}>{tech.name}</Typography>
                          </Box>
                        ))}
                      </Box>

                      <IconButton
                        size="small"
                        onClick={() => copyToClipboard(endpoint.http_url)}
                        sx={{ alignSelf: 'flex-start', color: 'rgba(0, 243, 255, 0.5)', p: 0.5, '&:hover': { color: '#00f3ff' } }}
                      >
                        <Copy size={12} />
                      </IconButton>
                    </Box>
                  </td>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Box sx={{
                      display: 'inline-flex',
                      px: 1.5,
                      py: 0.5,
                      borderRadius: 1,
                      bgcolor: `${getStatusColor(endpoint.http_status)}15`,
                      border: `1px solid ${getStatusColor(endpoint.http_status)}44`,
                      boxShadow: `0 0 10px ${getStatusColor(endpoint.http_status)}22`
                    }}>
                      <Typography sx={{ fontSize: '11px', fontWeight: 800, color: getStatusColor(endpoint.http_status) }}>
                        {endpoint.http_status}
                      </Typography>
                    </Box>
                  </td>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Typography sx={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)', fontWeight: 500 }}>
                      {endpoint.page_title || 'null'}
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
                          borderRadius: 1,
                          display: 'inline-block',
                          width: 'fit-content'
                        }}>
                          <Typography sx={{ fontSize: '9px', fontWeight: 800, color: '#ff003c' }}>{tag.trim()}</Typography>
                        </Box>
                      ))}
                    </Box>
                  </td>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Typography sx={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', letterSpacing: 0.5 }}>
                        TYPE: {endpoint.content_type || 'N/A'}
                      </Typography>
                      <Typography sx={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', letterSpacing: 0.5 }}>
                        LEN: {endpoint.content_length}
                      </Typography>
                    </Box>
                  </td>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Typography sx={{ fontSize: '11px', color: '#ff003c', fontWeight: 700, fontFamily: 'monospace' }}>
                      {endpoint.response_time ? `${endpoint.response_time.toFixed(4)}s` : 'N/A'}
                    </Typography>
                    <Typography sx={{ fontSize: '9px', color: 'rgba(255,255,255,0.3)', mt: 1 }}>
                      {new Date(endpoint.discovered_date).toLocaleDateString()}
                    </Typography>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Box>

        {/* Tactical Pagination */}
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'center', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <Stack spacing={2}>
            <Pagination
              count={Math.ceil((data?.count || 0) / 100)}
              page={page}
              onChange={(_, v) => setPage(v)}
              size="small"
              sx={{
                '& .MuiPaginationItem-root': {
                  color: 'rgba(255,255,255,0.5)',
                  borderColor: 'rgba(255,255,255,0.1)',
                  fontFamily: 'Orbitron',
                  fontSize: '10px',
                  '&.Mui-selected': {
                    bgcolor: 'rgba(0, 243, 255, 0.1)',
                    color: '#00f3ff',
                    borderColor: '#00f3ff'
                  }
                }
              }}
            />
          </Stack>
        </Box>
      </TacticalPanel>
    </Container>
  );
};
