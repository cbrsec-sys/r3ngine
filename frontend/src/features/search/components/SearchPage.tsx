import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  InputAdornment,
  Tabs,
  Tab,
  Stack,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Alert,
  Link
} from '@mui/material';
import {
  Search,
  Globe,
  Link as LinkIcon,
  ShieldAlert,
  ChevronRight,
  History,
  Clock,
  ExternalLink,
  Target,
  FileCode,
  AlertTriangle
} from 'lucide-react';
import { useSearch, useSearchHistory } from '../api';
import { useParams, useNavigate, useSearch as useUrlSearch } from '@tanstack/react-router';

const SEVERITY_COLORS: Record<number, string> = {
  4: '#ff1744', // Critical
  3: '#ff5722', // High
  2: '#ffc107', // Medium
  1: '#4caf50', // Low
  0: '#2196f3', // Info
  [-1]: '#9e9e9e' // Unknown
};

const TAB_STYLE = {
  fontFamily: 'Orbitron',
  fontWeight: 700,
  fontSize: '0.75rem',
  letterSpacing: 1,
  '&.Mui-selected': { color: '#00f3ff' }
};

export const SearchPage: React.FC = () => {
  const { projectSlug } = useParams({ strict: false });
  const urlSearch = useUrlSearch({ strict: false }) as { query?: string };
  const navigate = useNavigate();
  const [query, setQuery] = useState(urlSearch.query || '');
  const [activeTab, setActiveTab] = useState(0);

  const { data: searchResults, isLoading, error } = useSearch(urlSearch.query || '');
  const { data: searchHistory } = useSearchHistory();

  const handleSearch = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (query.trim()) {
      navigate({ search: { query } as any });
    }
  };

  const highlightText = (text: string, highlight: string) => {
    if (!highlight.trim()) return text;
    const parts = text.split(new RegExp(`(${highlight})`, 'gi'));
    return (
      <span>
        {parts.map((part, i) => 
          part.toLowerCase() === highlight.toLowerCase() ? (
            <span key={i} style={{ color: '#00f3ff', textShadow: '0 0 10px rgba(0, 243, 255, 0.5)', fontWeight: 700 }}>{part}</span>
          ) : (
            part
          )
        )}
      </span>
    );
  };

  return (
    <Box sx={{ p: 4, bgcolor: '#0a0a0a', minHeight: '100vh' }}>
      {/* Search Header */}
      <Box sx={{ maxWidth: 900, mx: 'auto', mb: 6 }}>
        <Typography variant="h4" sx={{ 
          fontFamily: 'Orbitron', 
          fontWeight: 900, 
          color: '#fff',
          textAlign: 'center',
          mb: 4,
          textShadow: '0 0 20px rgba(0, 243, 255, 0.3)'
        }}>
          UNIVERSAL_SEARCH
        </Typography>

        <form onSubmit={handleSearch}>
          <TextField
            fullWidth
            placeholder="Type target, subdomain, or vulnerability..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <Search size={24} style={{ color: '#00f3ff', marginRight: 8 }} />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => handleSearch()} sx={{ color: '#00f3ff' }}>
                      <ChevronRight size={24} />
                    </IconButton>
                  </InputAdornment>
                )
              }
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(0, 243, 255, 0.2)',
                borderRadius: '12px',
                fontSize: '1.2rem',
                color: '#fff',
                '&:hover': {
                  borderColor: 'rgba(0, 243, 255, 0.5)',
                  boxShadow: '0 0 15px rgba(0, 243, 255, 0.1)'
                },
                '&.Mui-focused': {
                  borderColor: '#00f3ff',
                  boxShadow: '0 0 20px rgba(0, 243, 255, 0.2)'
                }
              }
            }}
          />
        </form>

        {/* Search History Chips */}
        {searchHistory?.status && searchHistory.results.length > 0 && !urlSearch.query && (
          <Stack direction="row" spacing={1} sx={{ mt: 3, flexWrap: 'wrap', gap: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'rgba(255,255,255,0.4)', mr: 1 }}>
              <History size={16} />
              <Typography variant="caption">RECENT:</Typography>
            </Box>
            {searchHistory.results.slice(0, 5).map((item, idx) => (
              <Chip
                key={idx}
                label={item.query}
                onClick={() => {
                  setQuery(item.query);
                  navigate({ search: { query: item.query } as any });
                }}
                sx={{ 
                  bgcolor: 'rgba(255,255,255,0.05)', 
                  color: 'rgba(255,255,255,0.6)',
                  '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.1)', color: '#00f3ff' }
                }}
              />
            ))}
          </Stack>
        )}
      </Box>

      {/* Results Section */}
      <Box sx={{ maxWidth: 1100, mx: 'auto' }}>
        {isLoading ? (
          <Box sx={{ textAlign: 'center', py: 10 }}>
            <CircularProgress sx={{ color: '#00f3ff' }} />
            <Typography variant="body2" sx={{ mt: 2, color: 'rgba(255,255,255,0.4)', letterSpacing: 2 }}>
              SCANNING_DATABASES...
            </Typography>
          </Box>
        ) : error ? (
          <Alert severity="error" sx={{ bgcolor: 'rgba(211, 47, 47, 0.1)', color: '#ff5252' }}>
            An error occurred during search. Please try again.
          </Alert>
        ) : searchResults?.results ? (
          <>
            <Tabs 
              value={activeTab} 
              onChange={(_, v) => setActiveTab(v)}
              sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', mb: 4 }}
            >
              <Tab label={`SUBDOMAINS (${searchResults.results.subdomains.length})`} sx={TAB_STYLE} />
              <Tab label={`ENDPOINTS (${searchResults.results.endpoints.length})`} sx={TAB_STYLE} />
              <Tab label={`VULNERABILITIES (${searchResults.results.vulnerabilities.length})`} sx={TAB_STYLE} />
              <Tab label={`OTHERS (${searchResults.results.others.length})`} sx={TAB_STYLE} />
            </Tabs>

            <Box sx={{ minHeight: 400 }}>
              {activeTab === 0 && (
                <Stack spacing={2}>
                  {searchResults.results.subdomains.length > 0 ? (
                    searchResults.results.subdomains.map((s, idx) => (
                      <Card key={idx} sx={{ bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                        <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Stack direction="row" spacing={3} sx={{ alignItems: "center" }}>
                            <Box sx={{ color: '#00f3ff' }}><Globe size={20} /></Box>
                            <Box>
                              <Typography variant="subtitle1" sx={{ color: '#fff', fontWeight: 600 }}>
                                {highlightText(s.name, urlSearch.query || '')}
                                <Chip 
                                  label={s.http_status} 
                                  size="small" 
                                  sx={{ 
                                    ml: 2, height: 18, fontSize: '0.65rem', 
                                    bgcolor: s.http_status === 200 ? 'rgba(0, 255, 0, 0.1)' : 'rgba(255, 0, 0, 0.1)',
                                    color: s.http_status === 200 ? '#00ff00' : '#ff5252'
                                  }} 
                                />
                              </Typography>
                              {s.page_title && (
                                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                                  {highlightText(s.page_title, urlSearch.query || '')}
                                </Typography>
                              )}
                              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)' }}>
                                {s.http_url}
                              </Typography>
                            </Box>
                          </Stack>
                          <IconButton component={Link} href={s.http_url} target="_blank" sx={{ color: 'rgba(255,255,255,0.3)' }}>
                            <ExternalLink size={18} />
                          </IconButton>
                        </CardContent>
                      </Card>
                    ))
                  ) : (
                    <EmptyState message="NO_SUBDOMAINS_FOUND" />
                  )}
                </Stack>
              )}

              {activeTab === 1 && (
                <Stack spacing={2}>
                  {searchResults.results.endpoints.length > 0 ? (
                    searchResults.results.endpoints.map((e, idx) => (
                      <Card key={idx} sx={{ bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                        <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Stack direction="row" spacing={3} sx={{ alignItems: "center" }}>
                            <Box sx={{ color: '#ffd600' }}><LinkIcon size={20} /></Box>
                            <Box>
                              <Typography variant="body2" sx={{ color: '#fff', wordBreak: 'break-all' }}>
                                {highlightText(e.http_url, urlSearch.query || '')}
                              </Typography>
                              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', display: 'flex', alignItems: 'center', gap: 1 }}>
                                STATUS: {e.http_status}
                                {e.page_title && ` | TITLE: ${e.page_title}`}
                              </Typography>
                            </Box>
                          </Stack>
                          <IconButton component={Link} href={e.http_url} target="_blank" sx={{ color: 'rgba(255,255,255,0.3)' }}>
                            <ExternalLink size={18} />
                          </IconButton>
                        </CardContent>
                      </Card>
                    ))
                  ) : (
                    <EmptyState message="NO_ENDPOINTS_FOUND" />
                  )}
                </Stack>
              )}

              {activeTab === 2 && (
                <Stack spacing={2}>
                  {searchResults.results.vulnerabilities.length > 0 ? (
                    searchResults.results.vulnerabilities.map((v, idx) => (
                      <Card key={idx} sx={{ bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                        <CardContent>
                          <Stack direction="row" spacing={3} sx={{ alignItems: "flex-start" }}>
                            <Box sx={{ color: SEVERITY_COLORS[v.severity] || '#fff', mt: 0.5 }}><ShieldAlert size={20} /></Box>
                            <Box sx={{ flexGrow: 1 }}>
                              <Typography variant="subtitle1" sx={{ color: '#fff', fontWeight: 600 }}>
                                {highlightText(v.name, urlSearch.query || '')}
                                <Chip 
                                  label={getSeverityName(v.severity)} 
                                  size="small" 
                                  sx={{ 
                                    ml: 2, height: 18, fontSize: '0.6rem', fontWeight: 900,
                                    bgcolor: SEVERITY_COLORS[v.severity] + '22',
                                    color: SEVERITY_COLORS[v.severity],
                                    border: `1px solid ${SEVERITY_COLORS[v.severity]}44`
                                  }} 
                                />
                              </Typography>
                              {v.http_url && (
                                <Typography variant="caption" sx={{ color: 'rgba(0, 243, 255, 0.7)', display: 'block', mb: 1 }}>
                                  {v.http_url}
                                </Typography>
                              )}
                              {v.description && (
                                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', mt: 1 }}>
                                  {highlightText(v.description, urlSearch.query || '')}
                                </Typography>
                              )}
                            </Box>
                          </Stack>
                        </CardContent>
                      </Card>
                    ))
                  ) : (
                    <EmptyState message="NO_VULNERABILITIES_FOUND" />
                  )}
                </Stack>
              )}

              {activeTab === 3 && (
                <EmptyState message="ADDITIONAL_SEARCH_OBJECTS_NOT_IMPLEMENTED" icon={<AlertTriangle size={40} />} />
              )}
            </Box>
          </>
        ) : (
          <Box sx={{ textAlign: 'center', py: 10, opacity: 0.3 }}>
            <Target size={60} style={{ marginBottom: 16 }} />
            <Typography variant="h6" sx={{ fontFamily: 'Orbitron', letterSpacing: 2 }}>
              AWAITING_INPUT
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};

const EmptyState = ({ message, icon }: { message: string; icon?: React.ReactNode }) => (
  <Box sx={{ textAlign: 'center', py: 8, bgcolor: 'rgba(255,255,255,0.01)', borderRadius: 2, border: '1px dashed rgba(255,255,255,0.05)' }}>
    <Box sx={{ color: 'rgba(255,255,255,0.2)', mb: 2 }}>{icon || <FileCode size={40} />}</Box>
    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.3)', letterSpacing: 2, fontFamily: 'Orbitron' }}>
      {message}
    </Typography>
  </Box>
);

const getSeverityName = (severity: number) => {
  const names: Record<number, string> = {
    4: 'CRITICAL',
    3: 'HIGH',
    2: 'MEDIUM',
    1: 'LOW',
    0: 'INFO',
    [-1]: 'UNKNOWN'
  };
  return names[severity] || 'UNKNOWN';
};
