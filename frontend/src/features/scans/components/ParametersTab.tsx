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
  Chip
} from '@mui/material';
import {
  Search,
  Copy,
  Download,
  Filter,
  LayoutGrid
} from 'lucide-react';

import { useParameters } from '../api';
import { TacticalPanel } from '../../../components/TacticalPanel';
import { copyToClipboard } from '../../endpoints/utils/copy';

interface ParametersTabProps {
  scanId?: number;
  targetId?: number;
}

export const ParametersTab: React.FC<ParametersTabProps> = ({ scanId, targetId }) => {
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSearch, setActiveSearch] = useState('');

  const { data, isLoading } = useParameters({
    scan_id: scanId,
    target_id: targetId,
    page,
    search: activeSearch,
  });

  const handleSearch = () => {
    setPage(1);
    setActiveSearch(searchQuery);
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return '#00ff62';
    if (confidence >= 50) return '#00f3ff';
    if (confidence >= 20) return '#ffae00';
    return '#888';
  };

  return (
    <Box>
      {/* High-Fidelity Search Bar */}
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
            placeholder={"Search Parameters..."}
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
      </Box>

      {/* Main Tactical Panel */}
      <TacticalPanel title={"DISCOVERED PARAMETERS"} icon={<LayoutGrid size={14} />}>
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

        {/* Responsive Parameters Table */}
        <Box sx={{
          overflowX: 'auto',
          width: '100%',
          '&::-webkit-scrollbar': { height: '6px' },
          '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(0, 243, 255, 0.2)', borderRadius: '3px' }
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'auto' }}>
            <thead>
              <tr style={{
                textAlign: 'left',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                backgroundColor: 'rgba(255,255,255,0.02)'
              }}>
                <th style={{ padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>ENDPOINT URL</th>
                <th style={{ padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>PARAMETER / VALUE</th>
                <th style={{ padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>INTELLIGENCE</th>
                <th style={{ padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>SOURCES / CONFIDENCE</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={4} style={{ padding: '40px', textAlign: 'center' }}>
                    <CircularProgress size={24} sx={{ color: '#00f3ff' }} />
                  </td>
                </tr>
              ) : data?.results.map((param) => (
                <tr key={param.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', transition: 'background 0.2s' }}>
                  <td style={{ padding: '16px', verticalAlign: 'top', maxWidth: '300px' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                        <Typography sx={{
                          fontSize: '12px',
                          fontWeight: 500,
                          color: '#fff',
                          textDecoration: 'none',
                          wordBreak: 'break-all',
                          '&:hover': { color: '#00f3ff' }
                        }} component="a" href={param.endpoint?.http_url} target="_blank">
                          {param.endpoint?.http_url}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={() => copyToClipboard(param.endpoint?.http_url)}
                          sx={{ color: 'rgba(255,255,255,0.2)', p: 0.5, '&:hover': { color: '#00f3ff' } }}
                        >
                          <Copy size={12} />
                        </IconButton>
                      </Box>
                      <Box sx={{ display: 'inline-flex' }}>
                         <Typography sx={{ fontSize: '10px', fontWeight: 900, color: '#ffae00', fontFamily: 'monospace' }}>
                           {param.method}
                         </Typography>
                      </Box>
                    </Box>
                  </td>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography sx={{ fontSize: '13px', fontWeight: 700, color: '#00f3ff', fontFamily: 'monospace' }}>
                          {param.name}
                        </Typography>
                      </Box>
                      {param.value && (
                        <Box sx={{ px: 1, py: 0.5, bgcolor: 'rgba(255,255,255,0.05)', borderRadius: 1, border: '1px solid rgba(255,255,255,0.1)' }}>
                          <Typography sx={{ fontSize: '11px', color: 'rgba(255,255,255,0.7)', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                            = {param.value}
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  </td>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {param.is_reflected && (
                        <Chip label="REFLECTED" size="small" sx={{ height: 18, fontSize: '9px', fontWeight: 900, bgcolor: 'rgba(0, 255, 98, 0.1)', color: '#00ff62', border: '1px solid rgba(0, 255, 98, 0.2)' }} />
                      )}
                      {param.is_source && (
                        <Chip label="SOURCE" size="small" sx={{ height: 18, fontSize: '9px', fontWeight: 900, bgcolor: 'rgba(255, 174, 0, 0.1)', color: '#ffae00', border: '1px solid rgba(255, 174, 0, 0.2)' }} />
                      )}
                      {param.is_sink && (
                        <Chip label="SINK" size="small" sx={{ height: 18, fontSize: '9px', fontWeight: 900, bgcolor: 'rgba(255, 0, 60, 0.1)', color: '#ff003c', border: '1px solid rgba(255, 0, 60, 0.2)' }} />
                      )}
                      {(!param.is_reflected && !param.is_source && !param.is_sink) && (
                        <Typography sx={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)', fontStyle: 'italic' }}>
                          Standard
                        </Typography>
                      )}
                    </Box>
                  </td>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Stack spacing={1}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography sx={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)', fontFamily: 'Orbitron' }}>CONFIDENCE:</Typography>
                        <Typography sx={{ fontSize: '11px', fontWeight: 900, color: getConfidenceColor(param.confidence) }}>
                          {param.confidence}%
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {param.sources && param.sources.split(',').map((source) => (
                          <Chip
                            key={source}
                            label={source.trim().toUpperCase()}
                            size="small"
                            sx={{
                              height: 16,
                              fontSize: '8px',
                              fontWeight: 900,
                              bgcolor: 'rgba(112, 0, 255, 0.1)',
                              color: '#7000ff',
                              border: '1px solid rgba(112, 0, 255, 0.3)',
                              borderRadius: 0.5
                            }}
                          />
                        ))}
                      </Box>
                    </Stack>
                  </td>
                </tr>
              ))}
              {(!isLoading && data?.results.length === 0) && (
                <tr>
                  <td colSpan={4} style={{ padding: '60px', textAlign: 'center' }}>
                    <Typography sx={{ color: 'rgba(255,255,255,0.2)', fontFamily: 'Orbitron', fontSize: '0.8rem' }}>ZERO PARAMETERS DETECTED</Typography>
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
