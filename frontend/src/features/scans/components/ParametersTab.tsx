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
  const [filterOpen, setFilterOpen] = useState(false);
  const [filterLocation, setFilterLocation] = useState<string>('');
  const [filterAuthRelated, setFilterAuthRelated] = useState<'all' | 'true' | 'false'>('all');
  const [filterJs, setFilterJs] = useState(false);
  const [filterOpenApi, setFilterOpenApi] = useState(false);
  const [filterGraphql, setFilterGraphql] = useState(false);
  const [filterConfidenceMin, setFilterConfidenceMin] = useState<number>(0);
  const [filterDataType, setFilterDataType] = useState<string>('');

  const { data, isLoading } = useParameters({
    scan_id: scanId,
    target_id: targetId,
    page,
    search: activeSearch,
    param_location: filterLocation || undefined,
    is_auth_related: filterAuthRelated !== 'all' ? filterAuthRelated === 'true' : undefined,
    observed_in_js: filterJs || undefined,
    observed_in_openapi: filterOpenApi || undefined,
    observed_in_graphql: filterGraphql || undefined,
    confidence_min: filterConfidenceMin > 0 ? filterConfidenceMin : undefined,
    data_type: filterDataType || undefined,
  });

  const activeFilterCount = [
    filterLocation,
    filterAuthRelated !== 'all' ? filterAuthRelated : '',
    filterJs ? 'js' : '',
    filterOpenApi ? 'openapi' : '',
    filterGraphql ? 'graphql' : '',
    filterConfidenceMin > 0 ? 'conf' : '',
    filterDataType,
  ].filter(Boolean).length;

  const clearFilters = () => {
    setFilterLocation('');
    setFilterAuthRelated('all');
    setFilterJs(false);
    setFilterOpenApi(false);
    setFilterGraphql(false);
    setFilterConfidenceMin(0);
    setFilterDataType('');
    setPage(1);
  };

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

      {/* Collapsible Filter Panel */}
      {filterOpen && (
        <Box sx={{
          mb: 2, p: 2,
          bgcolor: 'rgba(0,243,255,0.03)',
          border: '1px solid rgba(0,243,255,0.15)',
          borderRadius: 1,
          display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'flex-end'
        }}>
          {/* Location */}
          <Box sx={{ minWidth: 160 }}>
            <Typography sx={{ fontSize: '9px', fontWeight: 900, color: 'rgba(255,255,255,0.4)', letterSpacing: 1, mb: 0.5, fontFamily: 'Orbitron' }}>LOCATION</Typography>
            <select
              value={filterLocation}
              onChange={e => { setFilterLocation(e.target.value); setPage(1); }}
              style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(0,243,255,0.2)', color: '#fff', borderRadius: 4, padding: '4px 8px', fontSize: '11px', width: '100%' }}
            >
              <option value="">All</option>
              <option value="query_string">Query String</option>
              <option value="json_body">JSON Body</option>
              <option value="header">Header</option>
              <option value="form_data">Form Data</option>
              <option value="path">Path</option>
              <option value="graphql_var">GraphQL Var</option>
            </select>
          </Box>

          {/* Source type toggles */}
          <Box>
            <Typography sx={{ fontSize: '9px', fontWeight: 900, color: 'rgba(255,255,255,0.4)', letterSpacing: 1, mb: 0.5, fontFamily: 'Orbitron' }}>SOURCE</Typography>
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              {([['JS', filterJs, setFilterJs], ['OPENAPI', filterOpenApi, setFilterOpenApi], ['GRAPHQL', filterGraphql, setFilterGraphql]] as const).map(([label, active, setter]) => (
                <Chip
                  key={label}
                  label={label}
                  size="small"
                  onClick={() => { (setter as React.Dispatch<React.SetStateAction<boolean>>)((v: boolean) => !v); setPage(1); }}
                  sx={{
                    height: 22, fontSize: '9px', fontWeight: 900, cursor: 'pointer',
                    bgcolor: active ? 'rgba(112,0,255,0.2)' : 'rgba(255,255,255,0.05)',
                    color: active ? '#a855f7' : 'rgba(255,255,255,0.4)',
                    border: `1px solid ${active ? 'rgba(112,0,255,0.4)' : 'rgba(255,255,255,0.1)'}`,
                  }}
                />
              ))}
            </Box>
          </Box>

          {/* Auth-related */}
          <Box>
            <Typography sx={{ fontSize: '9px', fontWeight: 900, color: 'rgba(255,255,255,0.4)', letterSpacing: 1, mb: 0.5, fontFamily: 'Orbitron' }}>AUTH</Typography>
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              {(['all', 'true', 'false'] as const).map(v => (
                <Chip
                  key={v}
                  label={v === 'all' ? 'ALL' : v === 'true' ? 'AUTH ONLY' : 'NON-AUTH'}
                  size="small"
                  onClick={() => { setFilterAuthRelated(v); setPage(1); }}
                  sx={{
                    height: 22, fontSize: '9px', fontWeight: 900, cursor: 'pointer',
                    bgcolor: filterAuthRelated === v ? 'rgba(255,0,60,0.15)' : 'rgba(255,255,255,0.05)',
                    color: filterAuthRelated === v ? '#ff003c' : 'rgba(255,255,255,0.4)',
                    border: `1px solid ${filterAuthRelated === v ? 'rgba(255,0,60,0.3)' : 'rgba(255,255,255,0.1)'}`,
                  }}
                />
              ))}
            </Box>
          </Box>

          {/* Min Confidence */}
          <Box sx={{ minWidth: 120 }}>
            <Typography sx={{ fontSize: '9px', fontWeight: 900, color: 'rgba(255,255,255,0.4)', letterSpacing: 1, mb: 0.5, fontFamily: 'Orbitron' }}>
              MIN CONFIDENCE: <Box component="span" sx={{ color: '#00f3ff' }}>{filterConfidenceMin}%</Box>
            </Typography>
            <input
              type="range" min={0} max={100} step={5}
              value={filterConfidenceMin}
              onChange={e => { setFilterConfidenceMin(Number(e.target.value)); setPage(1); }}
              style={{ width: '100%', accentColor: '#00f3ff' }}
            />
          </Box>

          {/* Data Type */}
          <Box sx={{ minWidth: 120 }}>
            <Typography sx={{ fontSize: '9px', fontWeight: 900, color: 'rgba(255,255,255,0.4)', letterSpacing: 1, mb: 0.5, fontFamily: 'Orbitron' }}>DATA TYPE</Typography>
            <select
              value={filterDataType}
              onChange={e => { setFilterDataType(e.target.value); setPage(1); }}
              style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(0,243,255,0.2)', color: '#fff', borderRadius: 4, padding: '4px 8px', fontSize: '11px', width: '100%' }}
            >
              <option value="">All</option>
              <option value="string">string</option>
              <option value="number">number</option>
              <option value="boolean">boolean</option>
              <option value="object">object</option>
              <option value="array">array</option>
            </select>
          </Box>

          {/* Clear */}
          {activeFilterCount > 0 && (
            <Button
              onClick={clearFilters}
              size="small"
              sx={{ alignSelf: 'flex-end', color: '#ffae00', border: '1px solid rgba(255,174,0,0.3)', borderRadius: 1, fontSize: '9px', fontWeight: 900, fontFamily: 'Orbitron', px: 2, height: 28 }}
            >
              CLEAR FILTERS
            </Button>
          )}
        </Box>
      )}

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
            <Tooltip title="Toggle Filters">
              <IconButton
                size="small"
                onClick={() => setFilterOpen(o => !o)}
                sx={{
                  color: filterOpen || activeFilterCount > 0 ? '#00f3ff' : 'rgba(255,255,255,0.5)',
                  border: `1px solid ${filterOpen || activeFilterCount > 0 ? 'rgba(0,243,255,0.3)' : 'rgba(255,255,255,0.1)'}`,
                  borderRadius: 1,
                  position: 'relative'
                }}
              >
                <Filter size={16} />
                {activeFilterCount > 0 && (
                  <Box component="span" sx={{
                    position: 'absolute', top: -4, right: -4,
                    width: 14, height: 14, borderRadius: '50%',
                    bgcolor: '#ff003c', fontSize: '8px', fontWeight: 900,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff'
                  }}>
                    {activeFilterCount}
                  </Box>
                )}
              </IconButton>
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
                        }} component="a" href={/^https?:\/\//i.test(param.endpoint?.http_url ?? '') ? param.endpoint!.http_url : '#'} target="_blank">
                          {param.endpoint?.http_url}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={() => { const url = param.endpoint?.http_url; if (url) copyToClipboard(url); }}
                          sx={{ color: 'rgba(255,255,255,0.2)', p: 0.5, '&:hover': { color: '#00f3ff' } }}
                        >
                          <Copy size={12} />
                        </IconButton>
                      </Box>

                    </Box>
                  </td>
                  <td style={{ padding: '16px', verticalAlign: 'top' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography sx={{ fontSize: '13px', fontWeight: 700, color: '#00f3ff', fontFamily: 'monospace' }}>
                          {param.name}
                        </Typography>
                        {param.data_type && (
                          <Box sx={{ display: 'inline-flex', ml: 1 }}>
                            <Typography sx={{ fontSize: '9px', color: 'rgba(255,255,255,0.35)', bgcolor: 'rgba(255,255,255,0.05)', px: 0.75, py: 0.25, borderRadius: 0.5, border: '1px solid rgba(255,255,255,0.08)', fontFamily: 'monospace' }}>
                              {param.data_type}
                            </Typography>
                          </Box>
                        )}
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
                      {param.is_auth_related && (
                        <Chip label="AUTH KEY" size="small" sx={{ height: 18, fontSize: '9px', fontWeight: 900, bgcolor: 'rgba(255,0,60,0.1)', color: '#ff003c', border: '1px solid rgba(255,0,60,0.2)' }} />
                      )}
                      {param.param_location && (
                        <Chip label={param.param_location.replace('_', ' ').toUpperCase()} size="small" sx={{ height: 18, fontSize: '9px', fontWeight: 900, bgcolor: 'rgba(0,243,255,0.05)', color: '#00f3ff', border: '1px solid rgba(0,243,255,0.2)' }} />
                      )}
                      {param.observed_in_js && (
                        <Chip label="JS" size="small" sx={{ height: 18, fontSize: '9px', fontWeight: 900, bgcolor: 'rgba(112,0,255,0.1)', color: '#a855f7', border: '1px solid rgba(112,0,255,0.2)' }} />
                      )}
                      {param.observed_in_openapi && (
                        <Chip label="OPENAPI" size="small" sx={{ height: 18, fontSize: '9px', fontWeight: 900, bgcolor: 'rgba(59,130,246,0.1)', color: '#3b82f6', border: '1px solid rgba(59,130,246,0.2)' }} />
                      )}
                      {param.observed_in_graphql && (
                        <Chip label="GRAPHQL" size="small" sx={{ height: 18, fontSize: '9px', fontWeight: 900, bgcolor: 'rgba(20,184,166,0.1)', color: '#14b8a6', border: '1px solid rgba(20,184,166,0.2)' }} />
                      )}
                      {(!param.is_auth_related && !param.param_location && !param.observed_in_js && !param.observed_in_openapi && !param.observed_in_graphql) && (
                        <Typography sx={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)', fontStyle: 'italic' }}>Standard</Typography>
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
                        {(param.sources || []).map((source) => (
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
