import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  TextField,
  CircularProgress,
  Chip,
  IconButton,
  Link
} from '@mui/material';
import { Bug, X, ExternalLink } from 'lucide-react';
import type { Subdomain } from './types';
import axios from 'axios';

interface ExploitResult {
  Title: string;
  Date: string;
  Author: string;
  Type: string;
  Platform: string;
  Port: number;
  Path: string;
  Codes: string;
}

interface SearchsploitModalProps {
  open: boolean;
  onClose: () => void;
  subdomain: Subdomain | null;
}

export const SearchsploitModal: React.FC<SearchsploitModalProps> = ({ open, onClose, subdomain }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ExploitResult[] | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  // Extract suggestions from technologies and ports
  const suggestions = React.useMemo(() => {
    if (!subdomain) return [];
    const techNames = subdomain.technologies.map(t => t.name);
    const portServices = subdomain.ip_addresses.flatMap(ip => 
      ip.ports.map(p => p.service_name).filter(s => s && s !== 'unknown' && s !== 'http' && s !== 'https')
    );
    return Array.from(new Set([...techNames, ...portServices]));
  }, [subdomain]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setResults(null);
    }
  }, [open]);

  const handleSearch = async () => {
    if (!query.trim()) {
      setErrorMsg('Please enter a query');
      return;
    }
    if (!subdomain) return;

    setLoading(true);
    setResults(null);
    setErrorMsg('');
    try {
      const response = await axios.post(`/api/action/subdomain/${subdomain.id}/searchsploit/`, { query });
      if (response.data.status) {
        setResults(response.data.results);
      } else {
        setErrorMsg(response.data.message || 'Search failed');
      }
    } catch (error: any) {
      setErrorMsg(error.response?.data?.message || 'Error running searchsploit');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth sx={{
      '& .MuiDialog-paper': { bgcolor: '#001a24', border: '1px solid rgba(0, 243, 255, 0.2)', color: '#fff' }
    }}>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(0, 243, 255, 0.1)', pb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Bug size={20} color="#00f3ff" />
          <Typography variant="h6" sx={{ fontFamily: 'Orbitron', color: '#00f3ff', fontSize: '1.1rem' }}>
            Exploit Search (Searchsploit)
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small" sx={{ color: 'rgba(255,255,255,0.5)' }}><X size={18} /></IconButton>
      </DialogTitle>
      
      <DialogContent sx={{ mt: 2 }}>
        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', mb: 2 }}>
          Search the Exploit-DB archive for known vulnerabilities affecting services on <strong>{subdomain?.name}</strong>.
        </Typography>

        {suggestions.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', display: 'block', mb: 1 }}>
              Suggested Queries from Recon Context:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {suggestions.map((s, i) => (
                <Chip
                  key={i}
                  label={s}
                  size="small"
                  onClick={() => setQuery(s)}
                  sx={{
                    bgcolor: 'rgba(0, 243, 255, 0.05)',
                    color: '#00f3ff',
                    border: '1px solid rgba(0, 243, 255, 0.2)',
                    '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.15)' }
                  }}
                />
              ))}
            </Box>
          </Box>
        )}

        <Box sx={{ display: 'flex', gap: 2, mb: 4 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="e.g. nginx 1.18.0"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            sx={{
              '& .MuiOutlinedInput-root': {
                color: '#fff',
                '& fieldset': { borderColor: 'rgba(0, 243, 255, 0.3)' },
                '&:hover fieldset': { borderColor: '#00f3ff' },
                '&.Mui-focused fieldset': { borderColor: '#00f3ff' }
              }
            }}
          />
          <Button
            variant="contained"
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            sx={{
              bgcolor: 'rgba(0, 243, 255, 0.1)',
              color: '#00f3ff',
              border: '1px solid rgba(0, 243, 255, 0.3)',
              '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)' },
              '&.Mui-disabled': { color: 'rgba(255,255,255,0.3)' },
              minWidth: 120
            }}
          >
            {loading ? <CircularProgress size={20} sx={{ color: '#00f3ff' }} /> : 'Search'}
          </Button>
        </Box>

        {errorMsg && (
          <Typography variant="body2" sx={{ color: '#ff003c', mb: 2 }}>
            {errorMsg}
          </Typography>
        )}

        {results !== null && (
          <Box>
            <Typography variant="subtitle2" sx={{ color: '#00f3ff', mb: 2, borderBottom: '1px dashed rgba(255,255,255,0.1)', pb: 1 }}>
              {results.length} Exploits Found
            </Typography>
            {results.length === 0 ? (
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' }}>
                No matching exploits found in the database.
              </Typography>
            ) : (
              <Box sx={{ maxHeight: 400, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 1 }}>
                {results.map((r, i) => (
                  <Box key={i} sx={{ bgcolor: 'rgba(255,255,255,0.02)', p: 1.5, borderRadius: 1, border: '1px solid rgba(255,255,255,0.05)' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Typography variant="body2" sx={{ fontWeight: 600, color: '#fff', mb: 0.5 }}>{r.Title}</Typography>
                      <Link href={`https://www.exploit-db.com/exploits/${r.Path.split('/').pop()?.split('.')[0] || ''}`} target="_blank" rel="noopener">
                        <IconButton size="small" sx={{ color: '#00f3ff' }}><ExternalLink size={14} /></IconButton>
                      </Link>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 2, color: 'rgba(255,255,255,0.5)' }}>
                      <Typography variant="caption">Date: {r.Date}</Typography>
                      <Typography variant="caption">Type: {r.Type}</Typography>
                      <Typography variant="caption">Platform: {r.Platform}</Typography>
                      {r.Codes && <Typography variant="caption" sx={{ color: '#ffae00' }}>{r.Codes}</Typography>}
                    </Box>
                  </Box>
                ))}
              </Box>
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ borderTop: '1px solid rgba(255,255,255,0.05)', p: 2 }}>
        <Button onClick={onClose} sx={{ color: 'rgba(255,255,255,0.7)' }}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};
