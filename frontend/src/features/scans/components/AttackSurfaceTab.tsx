import React, { useEffect, useRef, useState } from 'react';
import { Box, Typography, CircularProgress, Stack, Button, InputBase } from '@mui/material';
import { Map as MapIcon, Maximize, RefreshCw, Download, Search } from 'lucide-react';
import { TacticalPanel } from '../../../components/TacticalPanel';

interface AttackSurfaceTabProps {
  projectSlug: string;
  scanId: number;
}

declare global {
  interface Window {
    cytoscape: any;
  }
}

export const AttackSurfaceTab: React.FC<AttackSurfaceTabProps> = ({ projectSlug, scanId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    // Load Cytoscape from CDN if not already loaded
    if (!window.cytoscape) {
      const script = document.createElement('script');
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js';
      script.async = true;
      script.onload = () => initGraph();
      document.head.appendChild(script);
    } else {
      initGraph();
    }

    async function initGraph() {
      try {
        const response = await fetch(`/${projectSlug}/api/graph/scan/${scanId}/data/`);
        const elements = await response.json();
        
        if (containerRef.current && window.cytoscape) {
          cyRef.current = window.cytoscape({
            container: containerRef.current,
            elements: elements,
            boxSelectionEnabled: false,
            autounselectify: true,
            style: [
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'background-color': 'data(color)',
                        'color': '#fff',
                        'font-size': '10px',
                        'font-family': 'Inter, sans-serif',
                        'text-valign': 'bottom',
                        'text-margin-y': '5px',
                        'text-opacity': 0,
                        'width': 30,
                        'height': 30,
                        'border-width': 2,
                        'border-color': 'data(color)',
                        'border-opacity': 0.5,
                        'overlay-padding': '6px',
                        'z-index': 1
                    }
                },
                {
                    selector: 'node[type = "Domain"]',
                    style: {
                        'width': 60,
                        'height': 60,
                        'font-size': '14px',
                        'font-weight': 'bold',
                        'text-opacity': 1
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 1.5,
                        'line-color': 'rgba(148, 163, 184, 0.2)',
                        'target-arrow-color': 'rgba(148, 163, 184, 0.2)',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'font-size': '8px',
                        'color': '#94a3b8',
                        'text-rotation': 'autorotate',
                        'text-margin-y': '-10px',
                        'text-opacity': 0
                    }
                },
                {
                    selector: 'node.hover',
                    style: {
                        'text-opacity': 1,
                        'width': 45,
                        'height': 45,
                        'border-width': 4,
                        'border-color': '#fff',
                        'border-opacity': 1,
                        'z-index': 999,
                        'text-background-opacity': 0.8,
                        'text-background-color': '#0f172a',
                        'text-background-padding': '3px',
                        'text-background-shape': 'roundrectangle'
                    }
                },
                {
                    selector: 'node.highlighted',
                    style: {
                        'opacity': 1,
                        'z-index': 100
                    }
                },
                {
                    selector: 'node.faded',
                    style: {
                        'opacity': 0.1,
                        'text-opacity': 0
                    }
                },
                {
                    selector: 'edge.highlighted',
                    style: {
                        'line-color': '#00f3ff',
                        'target-arrow-color': '#00f3ff',
                        'width': 3,
                        'opacity': 1
                    }
                },
                {
                    selector: 'edge.faded',
                    style: {
                        'opacity': 0.05
                    }
                }
            ],
            layout: {
                name: 'cose',
                animate: true,
                randomize: true,
                componentSpacing: 150,
                nodeRepulsion: 8000,
                edgeElasticity: 100,
                nestingFactor: 5,
                gravity: 80,
                numIter: 1000,
                initialTemp: 200,
                coolingFactor: 0.95,
                minTemp: 1.0,
                idealEdgeLength: 100
            }
          });

          cyRef.current.on('mouseover', 'node', function(e: any) {
              const node = e.target;
              const neighborhood = node.neighborhood().add(node);
              cyRef.current.elements().addClass('faded');
              neighborhood.removeClass('faded').addClass('highlighted');
              node.addClass('hover');
          });

          cyRef.current.on('mouseout', 'node', function() {
              cyRef.current.elements().removeClass('faded highlighted hover');
          });

          setIsLoading(false);
        }
      } catch (error) {
        console.error("Error initializing graph:", error);
        setIsLoading(false);
      }
    }

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [projectSlug, scanId]);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (!cyRef.current) return;

    if (!query) {
      cyRef.current.elements().removeClass('faded highlighted');
      return;
    }

    const matches = cyRef.current.nodes().filter((node: any) => {
      return node.data('label').toLowerCase().includes(query.toLowerCase());
    });

    if (matches.length > 0) {
      cyRef.current.elements().addClass('faded');
      matches.removeClass('faded').addClass('highlighted');
      
      if (matches.length === 1) {
        cyRef.current.animate({
          center: { eles: matches },
          zoom: 1.5,
          duration: 500
        });
      }
    } else {
      cyRef.current.elements().addClass('faded');
    }
  };

  const resetZoom = () => cyRef.current?.fit(null, 50);
  const refreshLayout = () => {
    cyRef.current?.layout({ 
      name: 'cose', 
      animate: true,
      componentSpacing: 150,
      nodeRepulsion: 10000,
      idealEdgeLength: 120
    }).run();
  };
  const exportPNG = () => {
    if (!cyRef.current) return;
    const pngContent = cyRef.current.png({ full: true, bg: '#0f172a' });
    const link = document.createElement('a');
    link.href = pngContent;
    link.download = `attack-surface-scan-${scanId}.png`;
    link.click();
  };

  return (
    <Box sx={{ width: '100%', mt: 2 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" sx={{ 
          fontWeight: 900, 
          fontFamily: 'Orbitron', 
          letterSpacing: 3, 
          color: '#fff',
          textTransform: 'uppercase'
        }}>
          Attack Surface Map
        </Typography>
        <Typography sx={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', mt: 0.5, letterSpacing: 1 }}>
          V3.0 INFRASTRUCTURE_GRAPH_VISUALIZATION
        </Typography>
      </Box>

      <TacticalPanel title="GRAPH CONTROLS" icon={<MapIcon size={14} />}>
        <Box sx={{ p: 2, display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
           <Box sx={{ 
              display: 'flex', 
              bgcolor: 'rgba(255,255,255,0.03)', 
              borderRadius: 1, 
              border: '1px solid rgba(0, 243, 255, 0.1)',
              width: '300px'
           }}>
              <Box sx={{ p: 1, color: 'rgba(255,255,255,0.3)' }}><Search size={16} /></Box>
              <InputBase 
                placeholder="Search assets..." 
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                sx={{ flex: 1, color: '#fff', fontSize: '0.8rem' }} 
              />
           </Box>
           <Stack direction="row" spacing={1}>
              <Button size="small" startIcon={<Maximize size={14} />} onClick={resetZoom} sx={{ bgcolor: 'rgba(33,150,243,0.1)', color: '#2196f3', fontSize: '0.7rem', fontWeight: 800 }}>RESET ZOOM</Button>
              <Button size="small" startIcon={<RefreshCw size={14} />} onClick={refreshLayout} sx={{ bgcolor: 'rgba(112,0,255,0.1)', color: '#7000ff', fontSize: '0.7rem', fontWeight: 800 }}>RELAYOUT</Button>
              <Button size="small" startIcon={<Download size={14} />} onClick={exportPNG} sx={{ bgcolor: 'rgba(0,255,170,0.1)', color: '#00ffaa', fontSize: '0.7rem', fontWeight: 800 }}>EXPORT PNG</Button>
           </Stack>
        </Box>

        <Box sx={{ position: 'relative', bgcolor: '#0f172a', height: '600px' }}>
          {isLoading && (
            <Box sx={{ position: 'absolute', inset: 0, display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 5 }}>
              <CircularProgress sx={{ color: '#00f3ff' }} />
            </Box>
          )}
          <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
          
          <Box sx={{ 
            position: 'absolute', 
            bottom: 20, 
            left: 20, 
            bgcolor: 'rgba(30, 41, 59, 0.8)', 
            backdropFilter: 'blur(8px)',
            p: 1.5,
            borderRadius: 1,
            border: '1px solid rgba(255,255,255,0.1)',
            zIndex: 2
          }}>
             <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.5)', fontWeight: 900, mb: 1, textTransform: 'uppercase' }}>Legend</Typography>
             <Stack spacing={0.5}>
                {[
                  { label: 'Domain', color: '#3b82f6' },
                  { label: 'Subdomain', color: '#10b981' },
                  { label: 'IP Address', color: '#f59e0b' },
                  { label: 'Vulnerability', color: '#ef4444' }
                ].map(item => (
                  <Stack key={item.label} direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                    <Box sx={{ width: 8, height: 8, borderRadius: 0.5, bgcolor: item.color }} />
                    <Typography sx={{ fontSize: '0.7rem', color: '#e2e8f0', fontWeight: 600 }}>{item.label}</Typography>
                  </Stack>
                ))}
             </Stack>
          </Box>
        </Box>
      </TacticalPanel>
    </Box>
  );
};
