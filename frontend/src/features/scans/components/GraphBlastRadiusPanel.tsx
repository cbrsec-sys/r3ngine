import React, { useEffect, useState } from 'react';
import { Box, Typography, Stack, CircularProgress, Button } from '@mui/material';
import { useGraphStore } from '../../../store/useGraphStore';
import { ArrowLeft, Crosshair } from 'lucide-react';
import axios from 'axios';

interface Props {
  projectSlug: string;
}

export const GraphBlastRadiusPanel: React.FC<Props> = ({ projectSlug }) => {
  const { selectedNodeId, selectedNodeData, activePanel, setActivePanel } = useGraphStore();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedNodeId && activePanel === 'blastRadius') {
      fetchBlastRadius(selectedNodeId);
    }
  }, [selectedNodeId, activePanel]);

  const fetchBlastRadius = async (id: string) => {
    setLoading(true);
    try {
      const res = await axios.get(`/${projectSlug}/api/graph/blast-radius/${id}/`);
      setData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (!selectedNodeId || activePanel !== 'blastRadius') return null;

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
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Button 
            size="small" 
            onClick={() => setActivePanel('details')}
            sx={{ minWidth: 0, p: 0.5, color: 'rgba(255,255,255,0.5)' }}
        >
            <ArrowLeft size={16} />
        </Button>
        <Typography sx={{ color: '#00f3ff', fontWeight: 800, fontSize: '14px', fontFamily: 'Orbitron' }}>
          BLAST RADIUS
        </Typography>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress size={24} sx={{ color: '#00f3ff' }} />
        </Box>
      ) : data ? (
        <Stack spacing={2}>
            <Box sx={{ bgcolor: 'rgba(239, 68, 68, 0.1)', p: 2, borderRadius: 1, border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                <Typography sx={{ fontSize: '12px', color: 'rgba(239, 68, 68, 0.8)', fontWeight: 700, mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Crosshair size={14} /> COMPROMISED ASSETS
                </Typography>
                <Typography sx={{ fontSize: '24px', color: '#ef4444', fontWeight: 900 }}>
                    {data.nodes?.length || 0}
                </Typography>
                <Typography sx={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)', mt: 1 }}>
                    Downstream assets exposed if {selectedNodeData?.label} is breached.
                </Typography>
            </Box>

            <Box sx={{ bgcolor: 'rgba(255,255,255,0.02)', p: 1.5, borderRadius: 1, border: '1px solid rgba(255,255,255,0.05)' }}>
                <Typography sx={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)', mb: 1, fontWeight: 700 }}>AFFECTED NODES</Typography>
                <Stack spacing={1}>
                {data.nodes?.map((n: any) => (
                    <Box key={n.data.id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1, bgcolor: 'rgba(0,0,0,0.2)', borderRadius: 1 }}>
                        <Typography sx={{ fontSize: '11px', color: '#fff', fontWeight: 500, wordBreak: 'break-all' }}>
                            {n.data.label}
                        </Typography>
                        <Typography sx={{ fontSize: '9px', color: n.data.color, fontWeight: 700, ml: 1 }}>
                            {n.data.type}
                        </Typography>
                    </Box>
                ))}
                </Stack>
            </Box>
        </Stack>
      ) : (
        <Typography sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '12px' }}>Failed to compute blast radius.</Typography>
      )}
    </Box>
  );
};
