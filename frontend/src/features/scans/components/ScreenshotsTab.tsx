import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  CircularProgress,
  Grid,
  IconButton,
  Modal,
  Backdrop,
  Fade,
} from '@mui/material';
import { X, ExternalLink, Camera } from 'lucide-react';
import { TacticalPanel } from '../../../components/TacticalPanel';

interface ScreenshotSubdomain {
  id: number;
  name: string;
  http_url: string | null;
  screenshot_path: string;
  http_status: number | null;
}

interface ScreenshotsTabProps {
  projectSlug: string;
  scanId: number;
}

const useScreenshots = (scanId: number) => {
  return useQuery<ScreenshotSubdomain[]>({
    queryKey: ['screenshots', scanId],
    queryFn: async () => {
      const url = new URL(`${window.location.origin}/api/listSubdomains/`);
      url.searchParams.append('scan_id', scanId.toString());
      url.searchParams.append('only_screenshot', '');
      url.searchParams.append('no_page', '');
      url.searchParams.append('format', 'json');

      const response = await fetch(url.toString(), {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch screenshots');
      }

      const data = await response.json();
      // SubdomainsViewSet returns the list directly (array) when no_page is set,
      // or as { results: [...] }. Handle both.
      if (Array.isArray(data)) return data;
      if (Array.isArray(data?.results)) return data.results;
      return [];
    },
    enabled: !!scanId,
  });
};

export const ScreenshotsTab: React.FC<ScreenshotsTabProps> = ({ scanId }) => {
  const { data: screenshots, isLoading, isError } = useScreenshots(scanId);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [lightboxLabel, setLightboxLabel] = useState<string>('');

  const openLightbox = (path: string, label: string) => {
    setLightboxSrc(`/media/${path}`);
    setLightboxLabel(label);
  };

  const closeLightbox = () => {
    setLightboxSrc(null);
    setLightboxLabel('');
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 4, mt: 2 }}>
        <Camera size={20} color="#00f3ff" />
        <Box>
          <Typography variant="h5" sx={{
            fontWeight: 900,
            fontFamily: 'Orbitron',
            letterSpacing: 3,
            color: '#fff',
            textTransform: 'uppercase',
          }}>
            Visual Intelligence
          </Typography>
          <Typography sx={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', mt: 0.5, letterSpacing: 1 }}>
            EYEWITNESS CAPTURE RESULTS
          </Typography>
        </Box>
      </Box>

      <TacticalPanel>
        {/* Stats bar */}
        <Box sx={{
          p: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          bgcolor: 'rgba(255,255,255,0.01)',
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography sx={{ fontSize: '11px', fontWeight: 600, color: 'rgba(255,255,255,0.5)' }}>
              Captured:
            </Typography>
            <Box sx={{ px: 1, py: 0.5, bgcolor: 'rgba(0, 243, 255, 0.08)', border: '1px solid rgba(0, 243, 255, 0.2)', borderRadius: 1 }}>
              <Typography sx={{ fontSize: '11px', color: '#00f3ff', fontWeight: 700 }}>
                {isLoading ? '...' : (screenshots?.length ?? 0)} targets
              </Typography>
            </Box>
          </Box>
          <Typography sx={{ fontSize: '10px', color: 'rgba(255,255,255,0.2)', fontFamily: 'monospace' }}>
            CLICK THUMBNAIL TO EXPAND
          </Typography>
        </Box>

        {/* Content */}
        <Box sx={{ p: 3, minHeight: 300 }}>
          {isLoading && (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, py: 8 }}>
              <CircularProgress size={32} sx={{ color: '#00f3ff', filter: 'drop-shadow(0 0 8px #00f3ff)' }} />
              <Typography sx={{
                fontSize: '10px',
                fontWeight: 900,
                color: 'rgba(0, 243, 255, 0.5)',
                fontFamily: 'Orbitron',
                letterSpacing: 2,
                textTransform: 'uppercase',
              }}>
                Loading Captures...
              </Typography>
            </Box>
          )}

          {isError && (
            <Box sx={{
              p: 3,
              textAlign: 'center',
              border: '1px solid rgba(255, 0, 60, 0.2)',
              borderRadius: 1,
              bgcolor: 'rgba(255, 0, 60, 0.05)',
            }}>
              <Typography sx={{ color: '#ff003c', fontFamily: 'Orbitron', fontSize: '0.75rem', fontWeight: 700 }}>
                FETCH ERROR
              </Typography>
              <Typography sx={{ color: 'rgba(255, 255, 255, 0.3)', fontSize: '0.65rem', mt: 1 }}>
                Could not load screenshots from server.
              </Typography>
            </Box>
          )}

          {!isLoading && !isError && screenshots?.length === 0 && (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Camera size={40} color="rgba(255,255,255,0.1)" />
              <Typography sx={{
                mt: 2,
                color: 'rgba(255,255,255,0.2)',
                fontFamily: 'Orbitron',
                fontSize: '0.75rem',
                fontWeight: 700,
              }}>
                NO SCREENSHOTS CAPTURED
              </Typography>
              <Typography sx={{ color: 'rgba(255,255,255,0.15)', fontSize: '0.65rem', mt: 1 }}>
                EyeWitness did not produce any results for this scan, or the task has not completed yet.
              </Typography>
            </Box>
          )}

          {!isLoading && !isError && screenshots && screenshots.length > 0 && (
            <Grid container spacing={2}>
              {screenshots.map((sub) => (
                <Grid
                  key={sub.id}
                  size={{ xs: 12, sm: 6, md: 4, lg: 3 }}
                >
                  <Box
                    onClick={() => openLightbox(sub.screenshot_path, sub.name)}
                    sx={{
                      position: 'relative',
                      borderRadius: 1,
                      overflow: 'hidden',
                      border: '1px solid rgba(255,255,255,0.08)',
                      cursor: 'pointer',
                      bgcolor: 'rgba(0,0,0,0.4)',
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        border: '1px solid rgba(0, 243, 255, 0.4)',
                        boxShadow: '0 0 20px rgba(0, 243, 255, 0.1)',
                        transform: 'translateY(-2px)',
                        '& .screenshot-overlay': { opacity: 1 },
                      },
                    }}
                  >
                    {/* Thumbnail */}
                    <Box sx={{ aspectRatio: '16/9', overflow: 'hidden', bgcolor: 'rgba(0,0,0,0.6)' }}>
                      <img
                        src={`/media/${sub.screenshot_path}`}
                        alt={`Screenshot of ${sub.name}`}
                        loading="lazy"
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: 'cover',
                          display: 'block',
                        }}
                        onError={(e) => {
                          (e.currentTarget as HTMLImageElement).style.display = 'none';
                        }}
                      />
                    </Box>

                    {/* Hover overlay */}
                    <Box
                      className="screenshot-overlay"
                      sx={{
                        position: 'absolute',
                        inset: 0,
                        bgcolor: 'rgba(0, 243, 255, 0.08)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        opacity: 0,
                        transition: 'opacity 0.2s',
                      }}
                    >
                      <Typography sx={{
                        color: '#00f3ff',
                        fontSize: '10px',
                        fontWeight: 900,
                        fontFamily: 'Orbitron',
                        letterSpacing: 1,
                        textShadow: '0 0 10px #00f3ff',
                      }}>
                        EXPAND
                      </Typography>
                    </Box>

                    {/* Footer label */}
                    <Box sx={{
                      px: 1.5,
                      py: 1,
                      borderTop: '1px solid rgba(255,255,255,0.05)',
                      bgcolor: 'rgba(0,0,0,0.4)',
                    }}>
                      <Typography sx={{
                        fontSize: '11px',
                        fontWeight: 700,
                        color: '#fff',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}>
                        {sub.name}
                      </Typography>
                      {sub.http_status && (
                        <Typography sx={{
                          fontSize: '9px',
                          color: sub.http_status < 400 ? '#00ffaa' : '#ff003c',
                          fontWeight: 700,
                          fontFamily: 'monospace',
                        }}>
                          HTTP {sub.http_status}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                </Grid>
              ))}
            </Grid>
          )}
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
