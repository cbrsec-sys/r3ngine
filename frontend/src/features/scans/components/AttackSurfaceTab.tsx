import React, { useState, Suspense, useRef, useCallback } from 'react';
import { Box, Typography, CircularProgress, Stack, Button } from '@mui/material';
import { Map as MapIcon } from 'lucide-react';
import { TacticalPanel } from '../../../components/TacticalPanel';
import { GraphNodeDetailPanel } from './GraphNodeDetailPanel';
import { GraphBlastRadiusPanel } from './GraphBlastRadiusPanel';
import { GraphControlPanel } from './GraphControlPanel';
import { GraphCanvas } from './GraphCanvas';
import { useGraphData } from '../api/graphApi';

interface AttackSurfaceTabProps {
  projectSlug: string;
  scanId?: number;
  targetId?: number;
}

const AttackSurfaceContent: React.FC<AttackSurfaceTabProps> = ({ projectSlug, scanId, targetId }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [layoutName, setLayoutName] = useState<'fcose' | 'klay' | 'cose'>('fcose');
  const cyRef = useRef<cytoscape.Core | null>(null);

  const { data } = useGraphData(projectSlug, scanId, targetId);

  const handleInit = useCallback((cy: cytoscape.Core) => {
    cyRef.current = cy;
  }, []);

  const resetZoom = useCallback(() => {
    cyRef.current?.fit(undefined, 50);
  }, []);

  const refreshLayout = useCallback(() => {
    if (!cyRef.current) return;
    cyRef.current.layout({ 
      name: layoutName,
      animate: true,
      ...(layoutName === 'fcose' ? {
        nodeRepulsion: 4500,
        idealEdgeLength: 100,
      } : layoutName === 'klay' ? {
        klay: { direction: 'DOWN', spacing: 50 }
      } : {})
    } as any).run();
  }, [layoutName]);

  const exportPNG = useCallback(() => {
    if (!cyRef.current) return;
    const pngContent = cyRef.current.png({ full: true, bg: '#0f172a' });
    const link = document.createElement('a');
    link.href = pngContent;
    link.download = `attack-surface-${targetId ? 'target-' + targetId : 'scan-' + scanId}.png`;
    link.click();
  }, [scanId, targetId]);

  return (
    <TacticalPanel title="GRAPH CONTROLS" icon={<MapIcon size={14} />}>
      <GraphControlPanel 
          searchQuery={searchQuery}
          onSearch={setSearchQuery}
          onResetZoom={resetZoom}
          onRefreshLayout={refreshLayout}
          onExport={exportPNG}
          layoutName={layoutName}
          onChangeLayout={setLayoutName}
      />

      <Box sx={{ position: 'relative', bgcolor: '#0f172a', height: '600px', overflow: 'hidden' }}>
        <GraphCanvas 
          data={data} 
          layoutName={layoutName} 
          searchQuery={searchQuery}
          onInit={handleInit}
        />
        
        <Box sx={{ 
          position: 'absolute', 
          bottom: 20, 
          left: 20, 
          bgcolor: 'rgba(30, 41, 59, 0.8)', 
          backdropFilter: 'blur(8px)',
          p: 1.5,
          borderRadius: 1,
          border: '1px solid rgba(255,255,255,0.1)',
          zIndex: 2,
          pointerEvents: 'none'
        }}>
            <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.5)', fontWeight: 900, mb: 1, textTransform: 'uppercase' }}>Legend</Typography>
            <Stack spacing={1}>
              <Stack spacing={0.5}>
                  <Typography sx={{ fontSize: '0.55rem', color: 'rgba(0,243,255,0.6)', fontWeight: 800 }}>NODE TYPES</Typography>
                  {[
                    { label: 'Domain', color: '#3b82f6', shape: 'hexagon' },
                    { label: 'Subdomain', color: '#10b981', shape: 'circle' },
                    { label: 'IP Address', color: '#f59e0b', shape: 'circle' },
                    { label: 'Vulnerability', color: '#ef4444', shape: 'diamond' }
                  ].map(item => (
                    <Stack key={item.label} direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                      <Box sx={{ 
                        width: 8, height: 8, 
                        bgcolor: item.color, 
                        borderRadius: item.shape === 'circle' ? '50%' : 0,
                        transform: item.shape === 'diamond' ? 'rotate(45deg)' : 'none'
                      }} />
                      <Typography sx={{ fontSize: '0.7rem', color: '#e2e8f0', fontWeight: 600 }}>{item.label}</Typography>
                    </Stack>
                  ))}
              </Stack>
            </Stack>
        </Box>
        
        <Box sx={{ position: 'absolute', top: 0, right: 0, bottom: 0, zIndex: 3, display: 'flex', pointerEvents: 'none' }}>
          <Box sx={{ pointerEvents: 'auto' }}>
            <GraphNodeDetailPanel projectSlug={projectSlug} />
          </Box>
          <Box sx={{ pointerEvents: 'auto' }}>
            <GraphBlastRadiusPanel projectSlug={projectSlug} />
          </Box>
        </Box>
      </Box>
    </TacticalPanel>
  );
};

export const AttackSurfaceTab: React.FC<AttackSurfaceTabProps> = (props) => {
  return (
    <Box sx={{ width: '100%', mt: 2 }}>
      <Box sx={{ mb: 4, px: { xs: 2, sm: 0 } }}>
        <Typography variant="h5" sx={{ 
          fontWeight: 900, 
          fontFamily: 'Orbitron', 
          letterSpacing: { xs: 1, sm: 3 }, 
          color: '#fff',
          textTransform: 'uppercase',
          fontSize: { xs: '1.1rem', sm: '1.5rem' }
        }}>
          Attack Surface Map {props.targetId ? `(Target Coverage)` : `(Scan #${props.scanId})`}
        </Typography>
        <Typography sx={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', mt: 0.5, letterSpacing: 1 }}>
          V3.0 INFRASTRUCTURE GRAPH VISUALIZATION
        </Typography>
      </Box>

      <Suspense fallback={
        <Box sx={{ height: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#0f172a', borderRadius: 1, border: '1px solid rgba(255,255,255,0.05)' }}>
          <CircularProgress sx={{ color: '#00f3ff' }} />
        </Box>
      }>
        <AttackSurfaceContent {...props} />
      </Suspense>
    </Box>
  );
};
