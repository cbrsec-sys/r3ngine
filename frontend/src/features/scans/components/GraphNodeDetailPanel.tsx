import React, { useEffect, useState } from 'react';
import { Box, Typography, Stack, CircularProgress, Chip, Button } from '@mui/material';
import { useGraphStore } from '../../../store/useGraphStore';
import { ShieldAlert, Activity } from 'lucide-react';
import axios from 'axios';

interface Props {
  projectSlug: string;
}

export const GraphNodeDetailPanel: React.FC<Props> = ({ projectSlug }) => {
  const { selectedNodeId, selectedNodeData, activePanel, setActivePanel } = useGraphStore();
  const [details, setDetails] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedNodeId && activePanel === 'details') {
      fetchDetails(selectedNodeId);
    }
  }, [selectedNodeId, activePanel]);

  const fetchDetails = async (id: string) => {
    setLoading(true);
    try {
      const res = await axios.get(`/${projectSlug}/api/graph/node/${id}/details/`);
      setDetails(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTicket = async () => {
    if (!selectedNodeId) return;
    try {
      const res = await axios.post(`/${projectSlug}/api/graph/node/${selectedNodeId}/ticket/`);
      alert(res.data.message);
    } catch (e) {
      console.error(e);
    }
  };

  if (!selectedNodeId || activePanel !== 'details') return null;

  return (
    <Box sx={{
      width: 350,
      bgcolor: 'rgba(15, 23, 42, 0.95)',
      borderLeft: '1px solid rgba(0,243,255,0.2)',
      p: 2,
      display: 'flex',
      flexDirection: 'column',
      gap: 2,
      height: '100%',
      overflowY: 'auto'
    }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography sx={{ color: '#00f3ff', fontWeight: 800, fontSize: '14px', fontFamily: 'Orbitron' }}>
          NODE DETAILS
        </Typography>
        <Chip label={selectedNodeData?.type} size="small" sx={{ bgcolor: 'rgba(0,243,255,0.1)', color: '#00f3ff', fontSize: '10px' }} />
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress size={24} sx={{ color: '#00f3ff' }} />
        </Box>
      ) : details ? (
        <Stack spacing={2}>
          <Typography sx={{ color: '#fff', fontSize: '16px', fontWeight: 600, wordBreak: 'break-all' }}>
            {selectedNodeData?.label}
          </Typography>

          <Box sx={{ bgcolor: 'rgba(255,255,255,0.02)', p: 1.5, borderRadius: 1, border: '1px solid rgba(255,255,255,0.05)' }}>
            <Typography sx={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)', mb: 1, fontWeight: 700 }}>PROPERTIES</Typography>
            <Stack spacing={1}>
              {Object.entries(details.properties || {}).map(([k, v]) => (
                <Box key={k} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography sx={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>{k}</Typography>
                  <Typography sx={{ fontSize: '11px', color: '#fff', fontWeight: 500, maxWidth: '60%', textAlign: 'right', wordBreak: 'break-all' }}>
                    {String(v)}
                  </Typography>
                </Box>
              ))}
            </Stack>
          </Box>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Box sx={{ flex: 1, bgcolor: 'rgba(239, 68, 68, 0.1)', p: 1, borderRadius: 1, border: '1px solid rgba(239, 68, 68, 0.2)', textAlign: 'center' }}>
              <Typography sx={{ fontSize: '18px', color: '#ef4444', fontWeight: 800 }}>{selectedNodeData?.criticalVulnCount || 0}</Typography>
              <Typography sx={{ fontSize: '9px', color: 'rgba(239, 68, 68, 0.8)', fontWeight: 700 }}>CRITICAL</Typography>
            </Box>
            <Box sx={{ flex: 1, bgcolor: 'rgba(249, 115, 22, 0.1)', p: 1, borderRadius: 1, border: '1px solid rgba(249, 115, 22, 0.2)', textAlign: 'center' }}>
              <Typography sx={{ fontSize: '18px', color: '#f97316', fontWeight: 800 }}>{selectedNodeData?.highVulnCount || 0}</Typography>
              <Typography sx={{ fontSize: '9px', color: 'rgba(249, 115, 22, 0.8)', fontWeight: 700 }}>HIGH</Typography>
            </Box>
            <Box sx={{ flex: 1, bgcolor: 'rgba(0, 243, 255, 0.1)', p: 1, borderRadius: 1, border: '1px solid rgba(0, 243, 255, 0.2)', textAlign: 'center' }}>
              <Typography sx={{ fontSize: '18px', color: '#00f3ff', fontWeight: 800 }}>{selectedNodeData?.degree_centrality || 0}</Typography>
              <Typography sx={{ fontSize: '9px', color: 'rgba(0, 243, 255, 0.8)', fontWeight: 700 }}>EDGES</Typography>
            </Box>
          </Box>

          <Stack spacing={1}>
            <Button 
              fullWidth 
              variant="outlined" 
              startIcon={<Activity size={14} />}
              onClick={() => setActivePanel('blastRadius')}
              sx={{ borderColor: 'rgba(0,243,255,0.3)', color: '#00f3ff', fontSize: '11px', fontWeight: 700 }}
            >
              COMPUTE BLAST RADIUS
            </Button>
            <Button 
              fullWidth 
              variant="contained" 
              startIcon={<ShieldAlert size={14} />}
              onClick={handleCreateTicket}
              sx={{ bgcolor: '#ef4444', color: '#fff', fontSize: '11px', fontWeight: 700, '&:hover': { bgcolor: '#dc2626' } }}
            >
              CREATE TICKET
            </Button>
          </Stack>
        </Stack>
      ) : (
        <Typography sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '12px' }}>Failed to load details.</Typography>
      )}
    </Box>
  );
};
