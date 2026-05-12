import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  IconButton, 
  Tooltip,
  CircularProgress,
  Pagination,
  Stack,
  Collapse,
  Button,
  Chip,
  InputBase,
  Modal,
  Backdrop,
  Fade
} from '@mui/material';
import { 
  Search, 
  ChevronRight, 
  ChevronDown,
  Folder,
  FolderPlus,
  ExternalLink,
  Copy,
  Zap,
  Eye,
  FileText,
  MoreHorizontal,
  Download,
  X,
  Camera
} from 'lucide-react';

import { useSubdomains } from '../../subdomains/api';
import { TacticalPanel } from '../../../components/TacticalPanel';
import type { DirectoryScan, DirectoryFile } from '../../subdomains/types';

interface DirectoriesTabProps {
  projectSlug: string;
  scanId?: number;
  targetId?: number;
}

export const DirectoriesTab: React.FC<DirectoriesTabProps> = ({ projectSlug, scanId, targetId }) => {
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSearch, setActiveSearch] = useState('');
  const [expandedSubdomains, setExpandedSubdomains] = useState<Record<number, boolean>>({});
  const [expandedScans, setExpandedScans] = useState<Record<string, boolean>>({});
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [lightboxLabel, setLightboxLabel] = useState<string>('');

  const { data, isLoading, error } = useSubdomains(projectSlug, page, activeSearch, scanId, true, targetId);

  console.log('DirectoriesTab:', { projectSlug, scanId, targetId, page, activeSearch });
  console.log('DirectoriesTab Data:', data);
  console.log('DirectoriesTab Loading:', isLoading);
  console.log('DirectoriesTab Error:', error);

  const handleSearch = () => {
    setPage(1);
    setActiveSearch(searchQuery);
  };

  const toggleSubdomain = (id: number) => {
    setExpandedSubdomains(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleScan = (id: string) => {
    setExpandedScans(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const openLightbox = (path: string, label: string) => {
    setLightboxSrc(`/media/${path}`);
    setLightboxLabel(label);
  };

  const closeLightbox = () => {
    setLightboxSrc(null);
    setLightboxLabel('');
  };

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return '#00ffaa';
    if (status >= 300 && status < 400) return '#00f3ff';
    if (status >= 400 && status < 500) return '#ffae00';
    if (status >= 500) return '#ff003c';
    return '#888';
  };

  const decodeBase64 = (str: string) => {
    try {
      return atob(str);
    } catch (e) {
      return str;
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Tactical Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 4, mt: 2 }}>
        <Box>
          <Typography variant="h5" sx={{ 
            fontWeight: 900, 
            fontFamily: 'Orbitron', 
            letterSpacing: 3, 
            color: '#fff',
            textTransform: 'uppercase'
          }}>
            Directory Fuzzing Results
          </Typography>
          <Typography sx={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', mt: 0.5, letterSpacing: 1 }}>
            V3.0 SCAN ASSETS DIRECTORY ENUM
          </Typography>
        </Box>
      </Box>

      {/* Enterprise-Grade Search Bar */}
      <Box sx={{ 
        display: 'flex', 
        bgcolor: 'rgba(255,255,255,0.03)', 
        borderRadius: '4px', 
        overflow: 'hidden',
        mb: 3,
        border: '1px solid rgba(0, 243, 255, 0.1)',
        '&:focus-within': {
          borderColor: 'rgba(0, 243, 255, 0.4)',
          boxShadow: '0 0 15px rgba(0, 243, 255, 0.1)'
        },
        transition: 'all 0.2s'
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', pl: 2, color: 'rgba(255,255,255,0.3)' }}>
          <Search size={18} />
        </Box>
        <InputBase 
          placeholder="Filter Directories (e.g. name=admin, status=200)"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          sx={{ 
            flex: 1, 
            px: 2, 
            py: 1, 
            fontSize: '0.9rem',
            color: '#fff',
            '&::placeholder': { color: 'rgba(255,255,255,0.2)', opacity: 1 }
          }}
        />
        <Button 
          onClick={handleSearch}
          sx={{ 
            bgcolor: 'rgba(0, 243, 255, 0.1)', 
            color: '#00f3ff', 
            px: 4,
            borderRadius: 0,
            fontWeight: 700,
            fontSize: '11px',
            letterSpacing: 1,
            borderLeft: '1px solid rgba(0, 243, 255, 0.1)',
            '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)' }
          }}
        >
          SEARCH
        </Button>
      </Box>

      {/* Tactical Panel */}
      <TacticalPanel>
        <Box sx={{ 
          p: 2, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between', 
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          bgcolor: 'rgba(255,255,255,0.01)'
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography sx={{ fontSize: '11px', fontWeight: 600, color: 'rgba(255,255,255,0.5)' }}>Results :</Typography>
              <Box sx={{ px: 1, py: 0.5, bgcolor: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 1 }}>
                <Typography sx={{ fontSize: '11px', color: '#fff', fontWeight: 700 }}>{data?.count || 0}</Typography>
              </Box>
            </Box>
            <Box sx={{ px: 3, py: 0.8, bgcolor: 'rgba(255,255,255,0.03)', borderRadius: 1, border: '1px solid rgba(255,255,255,0.1)' }}>
              <Typography sx={{ fontSize: '11px', fontWeight: 700, color: 'rgba(255,255,255,0.7)', letterSpacing: 0.5 }}>
                Showing page {page} of {Math.ceil((data?.count || 0) / 50) || 1}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton size="small" sx={{ color: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.05)', border: '1px solid rgba(0, 243, 255, 0.1)', borderRadius: 1 }}>
              <Download size={14} />
            </IconButton>
          </Box>
        </Box>

        <Box sx={{ overflowX: 'auto', width: '100%' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'auto' }}>
            <thead>
              <tr style={{ 
                textAlign: 'left', 
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                backgroundColor: 'rgba(255,255,255,0.02)'
              }}>
                <th style={{ width: '40px', padding: '12px 16px' }}></th>
                <Box component="th" sx={{ display: { xs: 'none', sm: 'table-cell' }, width: '80px', padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>VISUAL</Box>
                <th style={{ padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>SUBDOMAIN</th>
                <Box component="th" sx={{ display: { xs: 'none', md: 'table-cell' }, padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>STATUS</Box>
                <Box component="th" sx={{ display: { xs: 'none', lg: 'table-cell' }, padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>PAGE TITLE</Box>
                <th style={{ padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>DIRECTORIES DISCOVERED</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} style={{ padding: '80px', textAlign: 'center' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                      <CircularProgress size={32} sx={{ color: '#00f3ff', filter: 'drop-shadow(0 0 8px #00f3ff)' }} />
                      <Typography sx={{ fontSize: '10px', fontWeight: 900, color: 'rgba(0, 243, 255, 0.5)', fontFamily: 'Orbitron', letterSpacing: 2 }}>
                        FETCHING DIRECTORY DATA...
                      </Typography>
                    </Box>
                  </td>
                </tr>
              ) : data?.results.map((sub) => (
                <tr key={sub.id} style={{ 
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  backgroundColor: 'transparent'
                }}>
                  <td style={{ padding: '12px 16px', verticalAlign: 'top', textAlign: 'center' }}>
                    <IconButton size="small" onClick={() => toggleSubdomain(sub.id)} sx={{ color: 'rgba(255,255,255,0.3)' }}>
                      {expandedSubdomains[sub.id] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </IconButton>
                  </td>
                  <Box component="td" sx={{ display: { xs: 'none', sm: 'table-cell' }, padding: '12px 16px', verticalAlign: 'top', textAlign: 'center' }}>
                    {sub.screenshot_path ? (
                      <IconButton 
                        size="small" 
                        onClick={() => openLightbox(sub.screenshot_path!, sub.name)}
                        sx={{ 
                          color: '#00f3ff', 
                          bgcolor: 'rgba(0, 243, 255, 0.05)',
                          border: '1px solid rgba(0, 243, 255, 0.2)',
                          '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.1)', borderColor: '#00f3ff' }
                        }}
                      >
                        <Eye size={14} />
                      </IconButton>
                    ) : (
                      <Camera size={14} style={{ color: 'rgba(255,255,255,0.1)' }} />
                    )}
                  </Box>
                  <td style={{ padding: '12px 16px', verticalAlign: 'top' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography sx={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>{sub.name}</Typography>
                        {sub.http_url && (
                          <IconButton size="small" component="a" href={sub.http_url} target="_blank" sx={{ p: 0.2, color: '#00f3ff' }}>
                            <ExternalLink size={12} />
                          </IconButton>
                        )}
                        <IconButton size="small" sx={{ p: 0.2, color: 'rgba(255,255,255,0.3)' }}>
                          <Copy size={12} />
                        </IconButton>
                      </Box>
                      {sub.is_interesting && (
                        <Chip 
                          label="INTERESTING" 
                          size="small" 
                          sx={{ 
                            height: 16, 
                            fontSize: '8px', 
                            fontWeight: 900, 
                            bgcolor: 'rgba(255, 0, 60, 0.1)', 
                            color: '#ff003c', 
                            borderRadius: 0.5,
                            border: '1px solid rgba(255, 0, 60, 0.2)',
                            boxShadow: '0 0 5px rgba(255, 0, 60, 0.2)'
                          }} 
                        />
                      )}
                    </Box>
                  </td>
                  <Box component="td" sx={{ display: { xs: 'none', md: 'table-cell' }, padding: '12px 16px', verticalAlign: 'top' }}>
                    <Box sx={{ 
                      display: 'inline-flex',
                      px: 1.2, 
                      py: 0.4, 
                      borderRadius: 0.5, 
                      bgcolor: `${getStatusColor(sub.http_status)}20`,
                      border: `1px solid ${getStatusColor(sub.http_status)}40`,
                    }}>
                      <Typography sx={{ fontSize: '11px', fontWeight: 900, color: getStatusColor(sub.http_status) }}>
                        {sub.http_status}
                      </Typography>
                    </Box>
                  </Box>
                  <Box component="td" sx={{ display: { xs: 'none', lg: 'table-cell' }, padding: '12px 16px', verticalAlign: 'top' }}>
                    <Typography sx={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)' }}>
                      {sub.page_title || '-'}
                    </Typography>
                  </Box>
                  <td style={{ padding: '12px 16px', verticalAlign: 'top' }}>
                    {sub.directories && sub.directories.length > 0 ? (
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {sub.directories.length > 1 && (
                          <Typography sx={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', mb: 1 }}>
                            Directory Scan performed {sub.directories.length} times.
                          </Typography>
                        )}
                        <Stack spacing={1}>
                          {[...sub.directories].reverse().map((scan, idx) => (
                            <Box key={scan.id}>
                              <Box 
                                onClick={() => toggleScan(`${sub.id}-${scan.id}`)}
                                sx={{ 
                                  display: 'flex', 
                                  alignItems: 'center', 
                                  gap: 1, 
                                  cursor: 'pointer',
                                  '&:hover': { color: '#00f3ff' },
                                  color: 'rgba(255,255,255,0.8)',
                                  transition: 'color 0.2s'
                                }}
                              >
                                {expandedScans[`${sub.id}-${scan.id}`] ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                                <FolderPlus size={14} style={{ color: '#00f3ff' }} />
                                <Typography sx={{ fontSize: '12px', fontWeight: 600 }}>
                                  <Box component="span" sx={{ px: 1, py: 0.2, bgcolor: 'rgba(0, 243, 255, 0.1)', borderRadius: 0.5, mr: 1, color: '#00f3ff' }}>
                                    {scan.directory_files.length}
                                  </Box>
                                  Directories found on {scan.scanned_date}
                                </Typography>
                              </Box>
                              
                              <Collapse in={expandedScans[`${sub.id}-${scan.id}`]}>
                                <Box sx={{ ml: 4, mt: 1, borderLeft: '1px dashed rgba(255,255,255,0.1)', pl: 2 }}>
                                  <Stack spacing={1}>
                                    {scan.directory_files.map((file, fIdx) => (
                                      <Box 
                                        key={`${scan.id}-${fIdx}`}
                                        sx={{ 
                                          display: 'flex', 
                                          alignItems: 'center', 
                                          justifyContent: 'space-between',
                                          p: 1,
                                          bgcolor: 'rgba(255,255,255,0.02)',
                                          borderRadius: 0.5,
                                          '&:hover': { bgcolor: 'rgba(255,255,255,0.04)' }
                                        }}
                                      >
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flex: 1 }}>
                                          <Typography sx={{ 
                                            fontSize: '12px', 
                                            fontWeight: 700, 
                                            color: '#fff',
                                            textDecoration: 'none',
                                            '&:hover': { color: '#00f3ff' }
                                          }} component="a" href={file.url} target="_blank">
                                            {decodeBase64(file.name)}
                                          </Typography>
                                          <Box sx={{ 
                                            px: 0.8, 
                                            py: 0.1, 
                                            borderRadius: 0.5, 
                                            bgcolor: `${getStatusColor(file.http_status)}20`,
                                            border: `1px solid ${getStatusColor(file.http_status)}40`,
                                          }}>
                                            <Typography sx={{ fontSize: '9px', fontWeight: 900, color: getStatusColor(file.http_status) }}>
                                              {file.http_status}
                                            </Typography>
                                          </Box>
                                          <Chip 
                                            label={file.content_type} 
                                            size="small" 
                                            sx={{ height: 14, fontSize: '8px', bgcolor: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.5)', borderRadius: 0.5 }} 
                                          />
                                        </Box>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                          <Typography sx={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
                                            {(file.length / 1024).toFixed(1)} KB
                                          </Typography>
                                          {file.lines && (
                                            <Typography sx={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
                                              {file.lines} L
                                            </Typography>
                                          )}
                                          <IconButton size="small" component="a" href={file.url} target="_blank" sx={{ color: 'rgba(255,255,255,0.3)', p: 0.5 }}>
                                            <ExternalLink size={12} />
                                          </IconButton>
                                        </Box>
                                      </Box>
                                    ))}
                                  </Stack>
                                </Box>
                              </Collapse>
                            </Box>
                          ))}
                        </Stack>
                      </Box>
                    ) : (
                      <Typography sx={{ fontSize: '11px', color: 'rgba(255,255,255,0.2)', fontStyle: 'italic' }}>
                        No directory data available
                      </Typography>
                    )}
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
              count={Math.ceil((data?.count || 0) / 50)} 
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

      {/* Lightbox Modal */}
      <Modal
        open={!!lightboxSrc}
        onClose={closeLightbox}
        closeAfterTransition
        slots={{ backdrop: Backdrop }}
        slotProps={{
          backdrop: {
            sx: { bgcolor: 'rgba(0, 0, 0, 0.92)', backdropFilter: 'blur(6px)' },
            timeout: 200,
          },
        }}
      >
        <Fade in={!!lightboxSrc} timeout={200}>
          <Box
            onClick={closeLightbox}
            sx={{
              position: 'fixed',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              p: 4,
              outline: 'none',
            }}
          >
            {/* Controls bar */}
            <Box
              onClick={(e) => e.stopPropagation()}
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%',
                maxWidth: '90vw',
                mb: 1.5,
              }}
            >
              <Typography sx={{
                color: '#00f3ff',
                fontFamily: 'Orbitron',
                fontSize: '12px',
                fontWeight: 700,
                letterSpacing: 1,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                maxWidth: 'calc(100% - 80px)',
              }}>
                {lightboxLabel}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <IconButton
                  component="a"
                  href={lightboxSrc ?? '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  size="small"
                  sx={{
                    color: 'rgba(255,255,255,0.6)',
                    bgcolor: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    '&:hover': { color: '#00f3ff', borderColor: 'rgba(0,243,255,0.4)' },
                  }}
                >
                  <ExternalLink size={14} />
                </IconButton>
                <IconButton
                  onClick={closeLightbox}
                  size="small"
                  sx={{
                    color: 'rgba(255,255,255,0.6)',
                    bgcolor: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    '&:hover': { color: '#ff003c', borderColor: 'rgba(255,0,60,0.4)' },
                  }}
                >
                  <X size={14} />
                </IconButton>
              </Box>
            </Box>

            {/* Image */}
            <Box
              onClick={(e) => e.stopPropagation()}
              sx={{
                maxWidth: '90vw',
                maxHeight: '80vh',
                border: '1px solid rgba(0, 243, 255, 0.2)',
                borderRadius: 1,
                overflow: 'hidden',
                boxShadow: '0 0 60px rgba(0, 243, 255, 0.1)',
              }}
            >
              {lightboxSrc && (
                <img
                  src={lightboxSrc}
                  alt={lightboxLabel}
                  style={{
                    display: 'block',
                    maxWidth: '90vw',
                    maxHeight: '80vh',
                    objectFit: 'contain',
                  }}
                />
              )}
            </Box>

            {/* Dismiss hint */}
            <Typography
              onClick={closeLightbox}
              sx={{
                mt: 2,
                fontSize: '10px',
                color: 'rgba(255,255,255,0.2)',
                fontFamily: 'Orbitron',
                letterSpacing: 1,
                cursor: 'pointer',
                userSelect: 'none',
              }}
            >
              CLICK ANYWHERE TO CLOSE
            </Typography>
          </Box>
        </Fade>
      </Modal>
    </Box>
  );
};
