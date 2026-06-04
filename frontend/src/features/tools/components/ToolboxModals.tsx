import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  Box,
  Typography,
  TextField,
  Button,
  CircularProgress,
  IconButton,
  Stack,
  Paper,
  Alert,
  Chip,
  Divider
} from '@mui/material';
import { X, Search, Globe, Bug, ShieldAlert } from 'lucide-react';
import { useWhois, useCMSDetector, useCVEDetails, useWafDetector } from '../api';

interface ToolModalProps {
  open: boolean;
  onClose: () => void;
}

const ToolDialog: React.FC<{ open: boolean; onClose: () => void; title: string; icon: React.ReactNode; color: string; children: React.ReactNode }> = ({
  open, onClose, title, icon, color, children
}) => (
  <Dialog
    open={open}
    onClose={onClose}
    maxWidth="md"
    fullWidth
    slotProps={{
      paper: {
        sx: {
          bgcolor: 'rgba(10, 10, 15, 0.95)',
          backdropFilter: 'blur(20px)',
          border: `1px solid ${color}44`,
          borderRadius: 4,
          backgroundImage: 'none',
          boxShadow: `0 0 40px ${color}11`,
          overflow: 'hidden'
        }
      }
    }}
  >
    <Box sx={{ p: 0.5, background: `linear-gradient(90deg, ${color}, transparent)`, borderRadius: '25px' }} />
    <Box sx={{ borderRadius: '25px', p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
      <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
        <Box sx={{ color }}>{icon}</Box>
        <Typography variant="h6" sx={{ fontFamily: 'Orbitron', fontWeight: 900, fontSize: '0.9rem', letterSpacing: 2, color }}>
          {title}
        </Typography>
      </Stack>
      <IconButton onClick={onClose} size="small" sx={{ color: 'rgba(255,255,255,0.4)', '&:hover': { color: '#fff' } }}>
        <X size={18} />
      </IconButton>
    </Box>
    <DialogContent sx={{ p: 3 }}>
      {children}
    </DialogContent>
  </Dialog>
);

export const WhoisModal: React.FC<ToolModalProps> = ({ open, onClose }) => {
  const [target, setTarget] = useState('');
  const { data, refetch, isFetching } = useWhois(target);

  return (
    <ToolDialog open={open} onClose={onClose} title="WHOIS LOOKUP" icon={<Globe size={20} />} color="#00f3ff">
      <Stack spacing={3}>
        <Stack direction="row" spacing={2}>
          <TextField
            fullWidth
            size="small"
            placeholder="Enter Domain or IP (e.g. google.com)"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            sx={{
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(0,0,0,0.2)',
                fontFamily: 'monospace',
                '& fieldset': { borderColor: 'rgba(0,243,255,0.2)' },
              }
            }}
          />
          <Button
            variant="contained"
            onClick={() => refetch()}
            disabled={isFetching || !target}
            sx={{ bgcolor: '#00f3ff', color: '#000', fontWeight: 900, px: 4, '&:hover': { bgcolor: '#00d8e4' } }}
          >
            {isFetching ? <CircularProgress size={20} color="inherit" /> : 'QUERY'}
          </Button>
        </Stack>

        {data && (
          <Paper sx={{ p: 2, bgcolor: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.05)', maxHeight: 400, overflow: 'auto' }}>
            <Typography sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.75rem', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
              {data.status === false ? data.message : JSON.stringify(data, null, 2)}
            </Typography>
          </Paper>
        )}
      </Stack>
    </ToolDialog>
  );
};

export const CMSDetectorModal: React.FC<ToolModalProps> = ({ open, onClose }) => {
  const [url, setUrl] = useState('');
  const { data, refetch, isFetching } = useCMSDetector(url);

  return (
    <ToolDialog open={open} onClose={onClose} title="CMS DETECTOR" icon={<Search size={20} />} color="#00f3ff">
      <Stack spacing={3}>
        <Stack direction="row" spacing={2}>
          <TextField
            fullWidth
            size="small"
            placeholder="Enter URL (e.g. https://example.com)"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            sx={{
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(0,0,0,0.2)',
                '& fieldset': { borderColor: 'rgba(0,243,255,0.2)' },
              }
            }}
          />
          <Button
            variant="contained"
            onClick={() => refetch()}
            disabled={isFetching || !url}
            sx={{ bgcolor: '#00f3ff', color: '#000', fontWeight: 900, px: 4 }}
          >
            {isFetching ? <CircularProgress size={20} color="inherit" /> : 'DETECT'}
          </Button>
        </Stack>

        {data && (
          <Paper sx={{ p: 3, bgcolor: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.05)' }}>
            <Typography sx={{ color: '#00f3ff', fontFamily: 'Orbitron', mb: 2, fontSize: '0.8rem' }}>
              DETECTION RESULTS:
            </Typography>
            <Typography sx={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.8rem', fontFamily: 'monospace' }}>
              {data.status ? JSON.stringify(data, null, 2) : data.message || 'No CMS detected.'}
            </Typography>
          </Paper>
        )}
      </Stack>
    </ToolDialog>
  );
};

export const CVELookupModal: React.FC<ToolModalProps> = ({ open, onClose }) => {
  const [cveId, setCveId] = useState('');
  const { data, refetch, isFetching } = useCVEDetails(cveId);

  return (
    <ToolDialog open={open} onClose={onClose} title="CVE LOOKUP" icon={<Bug size={20} />} color="#ff00ff">
      <Stack spacing={3}>
        <Stack direction="row" spacing={2}>
          <TextField
            fullWidth
            size="small"
            placeholder="Enter CVE ID (e.g. CVE-2021-44228)"
            value={cveId}
            onChange={(e) => setCveId(e.target.value)}
            sx={{
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(0,0,0,0.2)',
                '& fieldset': { borderColor: 'rgba(255,0,255,0.2)' },
              }
            }}
          />
          <Button
            variant="contained"
            onClick={() => refetch()}
            disabled={isFetching || !cveId}
            sx={{ bgcolor: '#ff00ff', color: '#fff', fontWeight: 900, px: 4, '&:hover': { bgcolor: '#e600e6' } }}
          >
            {isFetching ? <CircularProgress size={20} color="inherit" /> : 'SEARCH'}
          </Button>
        </Stack>

        {data && (
          <Paper sx={{ p: 3, bgcolor: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.05)' }}>
            {data.status && data.result ? (
              <Stack spacing={2.5}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Typography sx={{ color: '#ff00ff', fontWeight: 900, fontFamily: 'Orbitron', fontSize: '1.1rem' }}>
                    {data.result.id}
                  </Typography>
                  {data.result.is_cisa_kev && (
                    <Chip
                      label="CISA KEV"
                      size="small"
                      sx={{
                        bgcolor: 'rgba(239, 68, 68, 0.15)',
                        color: '#ef4444',
                        border: '1px solid #ef4444',
                        fontSize: '0.6rem',
                        fontWeight: 900,
                        height: 18
                      }}
                    />
                  )}
                </Box>
                <Typography sx={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.85rem', lineHeight: 1.5 }}>
                  {data.result.summary}
                </Typography>
                
                <Stack direction="row" spacing={1.5} sx={{ flexWrap: 'wrap', gap: 1 }}>
                  {data.result.cvss !== null && data.result.cvss !== undefined && (
                    <Chip
                      label={`CVSS: ${Number(data.result.cvss).toFixed(1)}`}
                      size="small"
                      sx={{
                        bgcolor: Number(data.result.cvss) >= 9.0 ? 'rgba(255, 0, 60, 0.15)' : Number(data.result.cvss) >= 7.0 ? 'rgba(249, 115, 22, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                        color: Number(data.result.cvss) >= 9.0 ? '#ff003c' : Number(data.result.cvss) >= 7.0 ? '#f97316' : '#3b82f6',
                        border: `1px solid ${Number(data.result.cvss) >= 9.0 ? '#ff003c' : Number(data.result.cvss) >= 7.0 ? '#f97316' : '#3b82f6'}`,
                        fontWeight: 800,
                        fontFamily: 'Orbitron',
                        fontSize: '0.65rem'
                      }}
                    />
                  )}
                  {data.result.epss_score !== null && data.result.epss_score !== undefined && (
                    <Chip
                      label={`EPSS: ${Number(data.result.epss_score).toFixed(5)} (${Number(data.result.epss_percentile || 0).toFixed(1)}%)`}
                      size="small"
                      sx={{
                        bgcolor: 'rgba(0, 243, 255, 0.15)',
                        color: '#00f3ff',
                        border: '1px solid #00f3ff',
                        fontWeight: 800,
                        fontFamily: 'Orbitron',
                        fontSize: '0.65rem'
                      }}
                    />
                  )}
                  {data.result.attack_vector && (
                    <Chip
                      label={`Vector: ${data.result.attack_vector}`}
                      size="small"
                      sx={{
                        bgcolor: 'rgba(255, 255, 255, 0.05)',
                        color: 'rgba(255, 255, 255, 0.8)',
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        fontWeight: 700,
                        fontSize: '0.65rem'
                      }}
                    />
                  )}
                  {data.result.attack_complexity && (
                    <Chip
                      label={`Complexity: ${data.result.attack_complexity}`}
                      size="small"
                      sx={{
                        bgcolor: 'rgba(255, 255, 255, 0.05)',
                        color: 'rgba(255, 255, 255, 0.8)',
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        fontWeight: 700,
                        fontSize: '0.65rem'
                      }}
                    />
                  )}
                </Stack>

                <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)', my: 0.5 }} />

                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2.5 }}>
                  <Stack spacing={0.5}>
                    <Typography sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem', fontWeight: 900, textTransform: 'uppercase', letterSpacing: 1.5, fontFamily: 'Orbitron' }}>
                      Execution Context
                    </Typography>
                    <Typography sx={{ color: 'rgba(255,255,255,0.85)', fontSize: '0.8rem' }}>
                      Privileges Required: {data.result.privileges_required || 'N/A'} <br />
                      User Interaction: {data.result.user_interaction || 'N/A'}
                    </Typography>
                  </Stack>
                  <Stack spacing={0.5}>
                    <Typography sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem', fontWeight: 900, textTransform: 'uppercase', letterSpacing: 1.5, fontFamily: 'Orbitron' }}>
                      CVSS Impacts
                    </Typography>
                    <Typography sx={{ color: 'rgba(255,255,255,0.85)', fontSize: '0.8rem' }}>
                      Confidentiality: {data.result.confidentiality_impact || 'N/A'} <br />
                      Integrity: {data.result.integrity_impact || 'N/A'} <br />
                      Availability: {data.result.availability_impact || 'N/A'}
                    </Typography>
                  </Stack>
                  <Stack spacing={0.5}>
                    <Typography sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem', fontWeight: 900, textTransform: 'uppercase', letterSpacing: 1.5, fontFamily: 'Orbitron' }}>
                      Vulnerability Type
                    </Typography>
                    <Typography sx={{ color: 'rgba(255,255,255,0.85)', fontSize: '0.8rem' }}>
                      {data.result.vulnerability_type || 'N/A'}
                    </Typography>
                  </Stack>
                  <Stack spacing={0.5}>
                    <Typography sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem', fontWeight: 900, textTransform: 'uppercase', letterSpacing: 1.5, fontFamily: 'Orbitron' }}>
                      Timeline
                    </Typography>
                    <Typography sx={{ color: 'rgba(255,255,255,0.85)', fontSize: '0.8rem' }}>
                      Published: {data.result.published_date ? new Date(data.result.published_date).toLocaleDateString() : 'N/A'} <br />
                      Modified: {data.result.last_modified_date ? new Date(data.result.last_modified_date).toLocaleDateString() : 'N/A'}
                    </Typography>
                  </Stack>
                </Box>
              </Stack>
            ) : (
              <Typography sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.8rem' }}>
                {data.message || 'CVE not found.'}
              </Typography>
            )}
          </Paper>
        )}
      </Stack>
    </ToolDialog>
  );
};

export const WAFDetectorModal: React.FC<ToolModalProps> = ({ open, onClose }) => {
  const [url, setUrl] = useState('');
  const { data, refetch, isFetching } = useWafDetector(url);

  return (
    <ToolDialog open={open} onClose={onClose} title="WAF DETECTOR" icon={<ShieldAlert size={20} />} color="#ff9800">
      <Stack spacing={3}>
        <Stack direction="row" spacing={2}>
          <TextField
            fullWidth
            size="small"
            placeholder="Enter URL (e.g. https://example.com)"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            sx={{
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(0,0,0,0.2)',
                '& fieldset': { borderColor: 'rgba(255,152,0,0.2)' },
              }
            }}
          />
          <Button
            variant="contained"
            onClick={() => refetch()}
            disabled={isFetching || !url}
            sx={{ bgcolor: '#ff9800', color: '#000', fontWeight: 900, px: 4, '&:hover': { bgcolor: '#e68a00' } }}
          >
            {isFetching ? <CircularProgress size={20} color="inherit" /> : 'ANALYZE'}
          </Button>
        </Stack>

        {data && (
          <Paper sx={{ p: 3, bgcolor: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.05)' }}>
            <Typography sx={{ color: '#ff9800', fontFamily: 'Orbitron', mb: 2, fontSize: '0.8rem' }}>
              WAF STATUS:
            </Typography>
            <Typography sx={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.8rem', fontFamily: 'monospace' }}>
              {data.status ? JSON.stringify(data, null, 2) : data.message || 'No WAF detected or error occurred.'}
            </Typography>
          </Paper>
        )}
      </Stack>
    </ToolDialog>
  );
};
