import React, { useEffect, useRef, useState } from 'react';
import { Box, CircularProgress, Typography, Switch, FormControlLabel, IconButton, Tooltip, Paper } from '@mui/material';
import { Download, Maximize2, Minimize2, ZoomIn, ZoomOut, RefreshCw } from 'lucide-react';
import * as d3 from 'd3';
import axios from 'axios';
import { TacticalPanel } from '../../../components/TacticalPanel';

interface VisualizationNode {
  description: string;
  title?: string;
  http_status?: number;
  children?: VisualizationNode[];
  _children?: VisualizationNode[]; // For collapsed state
  x?: number;
  y?: number;
  x0?: number;
  y0?: number;
  depth?: number;
  id?: number;
}

interface VisualizationTabProps {
  projectSlug: string;
  scanId?: number;
  targetId?: number;
}

const VisualizationTab: React.FC<VisualizationTabProps> = ({ projectSlug, scanId, targetId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandAll, setExpandAll] = useState(false);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetchData();
  }, [scanId, targetId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      let url = `/api/queryAllScanResultVisualise/?format=json`;
      if (scanId) {
        url += `&scan_id=${scanId}`;
      } else if (targetId) {
        url += `&target_id=${targetId}`;
      }
      const response = await axios.get(url);
      if (response.data && response.data.length > 0) {
        setData(response.data[0]);
      } else {
        setError('No visualization data found.');
      }
    } catch (err) {
      console.error('Error fetching visualization data:', err);
      setError('Failed to load visualization data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!data || !svgRef.current) return;

    renderChart();
  }, [data, expandAll]);

  const renderChart = () => {
    const width = containerRef.current?.clientWidth || 1200;
    const height = 800;
    const margin = { top: 20, right: 120, bottom: 20, left: 120 };

    // Clear previous SVG content
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const g = svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 3])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom as any);

    const tree = d3.tree<VisualizationNode>()
      .nodeSize([30, 200]); // [height, width] per node

    const root = d3.hierarchy<VisualizationNode>(data);
    
    // Initial expansion/collapse
    if (!expandAll) {
      root.descendants().forEach((d, i) => {
        if (d.depth > 1) {
          (d as any)._children = d.children;
          d.children = undefined;
        }
      });
    }

    let i = 0;
    const duration = 750;

    const update = (source: any) => {
      const nodes = root.descendants().reverse();
      const links = root.links();

      tree(root as any);

      let left = root;
      let right = root;
      root.eachBefore(node => {
        if (node.x! < left.x!) left = node;
        if (node.x! > right.x!) right = node;
      });

      const height = right.x! - left.x! + margin.top + margin.bottom;

      const transition = svg.transition()
        .duration(duration)
        .attr("viewBox", [-margin.left, left.x! - margin.top, width, height] as any)
        .tween("resize", (window.ResizeObserver ? null : () => () => svg.dispatch("toggle")) as any);

      // Update nodes
      const node = g.selectAll("g.node")
        .data(nodes, (d: any) => d.id || (d.id = ++i));

      const nodeEnter = node.enter().append("g")
        .attr("class", "node")
        .attr("transform", d => `translate(${source.y0},${source.x0})`)
        .attr("fill-opacity", 0)
        .attr("stroke-opacity", 0)
        .on("click", (event, d) => {
          if (d.children) {
            (d as any)._children = d.children;
            d.children = undefined;
          } else {
            d.children = (d as any)._children;
            (d as any)._children = undefined;
          }
          update(d);
        });

      nodeEnter.append("circle")
        .attr("r", 6)
        .attr("fill", (d: any) => d._children ? "#00f3ff" : "rgba(255,255,255,0.2)")
        .attr("stroke", "#00f3ff")
        .attr("stroke-width", 1.5)
        .style("cursor", "pointer");

      nodeEnter.append("text")
        .attr("dy", "0.31em")
        .attr("x", (d: any) => d._children || d.children ? -10 : 10)
        .attr("text-anchor", (d: any) => d._children || d.children ? "end" : "start")
        .attr("fill", (d: any) => {
          const data = d.data;
          if (data.http_status >= 400 || data.title === 'Interesting') return "#ff003c";
          if (data.http_status === 200) return "#00ff62";
          return "rgba(255,255,255,0.8)";
        })
        .attr("font-family", "Orbitron, sans-serif")
        .attr("font-size", "0.7rem")
        .text((d: any) => (d.data.title === 'Interesting' ? `(★) ${d.data.description}` : d.data.description))
        .clone(true).lower()
        .attr("stroke-linejoin", "round")
        .attr("stroke-width", 3)
        .attr("stroke", "rgba(10,10,15,0.8)");

      const nodeUpdate = node.merge(nodeEnter as any).transition(transition as any)
        .attr("transform", d => `translate(${d.y},${d.x})`)
        .attr("fill-opacity", 1)
        .attr("stroke-opacity", 1);

      nodeUpdate.select("circle")
        .attr("fill", (d: any) => d._children ? "#00f3ff" : "rgba(10,10,15,0.8)");

      const nodeExit = node.exit().transition(transition as any).remove()
        .attr("transform", d => `translate(${source.y},${source.x})`)
        .attr("fill-opacity", 0)
        .attr("stroke-opacity", 0);

      // Update links
      const link = g.selectAll("path.link")
        .data(links, (d: any) => d.target.id);

      const linkEnter = link.enter().append("path")
        .attr("class", "link")
        .attr("d", (d: any) => {
          const o = { x: source.x0, y: source.y0 };
          return d3.linkHorizontal()({ source: [o.y, o.x], target: [o.y, o.x] } as any);
        })
        .attr("fill", "none")
        .attr("stroke", "rgba(0,243,255,0.15)")
        .attr("stroke-width", 1.5);

      link.merge(linkEnter as any).transition(transition as any)
        .attr("d", d3.linkHorizontal()
          .x((d: any) => d.y)
          .y((d: any) => d.x) as any
        );

      link.exit().transition(transition as any).remove()
        .attr("d", (d: any) => {
          const o = { x: source.x, y: source.y };
          return d3.linkHorizontal()({ source: [o.y, o.x], target: [o.y, o.x] } as any);
        });

      // Stash the old positions for transition
      root.eachBefore(d => {
        (d as any).x0 = d.x;
        (d as any).y0 = d.y;
      });
    };

    (root as any).x0 = height / 2;
    (root as any).y0 = 0;

    update(root);
  };

  const handleDownload = () => {
    if (!svgRef.current) return;
    const svgData = new XMLSerializer().serializeToString(svgRef.current);
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.onload = () => {
      canvas.width = img.width * 2;
      canvas.height = img.height * 2;
      ctx?.drawImage(img, 0, 0, canvas.width, canvas.height);
      const pngFile = canvas.toDataURL("image/png");
      const downloadLink = document.createElement("a");
      downloadLink.download = `visualization_${scanId}.png`;
      downloadLink.href = pngFile;
      downloadLink.click();
    };
    img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgData)));
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <CircularProgress sx={{ color: '#00f3ff' }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="error">{error}</Typography>
        <IconButton onClick={fetchData} sx={{ mt: 2, color: '#00f3ff' }}>
          <RefreshCw size={20} />
        </IconButton>
      </Box>
    );
  }

  return (
    <TacticalPanel 
      title="SCAN RESULT VISUALIZATION" 
      icon={<Maximize2 size={14} />}
      headerAction={
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <FormControlLabel
            control={
              <Switch 
                checked={expandAll} 
                onChange={(e) => setExpandAll(e.target.checked)}
                size="small"
                sx={{ 
                  '& .MuiSwitch-switchBase.Mui-checked': { color: '#00f3ff' },
                  '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#00f3ff' }
                }}
              />
            }
            label={<Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.6)', fontWeight: 900, fontFamily: 'Orbitron' }}>EXPAND ALL</Typography>}
          />
          <Tooltip title="Download as PNG">
            <IconButton size="small" onClick={handleDownload} sx={{ color: '#00f3ff' }}>
              <Download size={16} />
            </IconButton>
          </Tooltip>
        </Box>
      }
    >
      <Box ref={containerRef} sx={{ position: 'relative', overflow: 'hidden', bgcolor: 'rgba(10,10,15,0.3)', borderRadius: 1, minHeight: '700px' }}>
        <svg 
          ref={svgRef} 
          width="100%" 
          height="800" 
          style={{ cursor: 'grab' }}
        />
        
        {/* Legend */}
        <Paper 
          sx={{ 
            position: 'absolute', 
            bottom: 20, 
            right: 20, 
            p: 1.5, 
            bgcolor: 'rgba(10,10,15,0.9)', 
            border: '1px solid rgba(0,243,255,0.2)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <Typography sx={{ fontSize: '0.6rem', color: '#00f3ff', fontWeight: 900, mb: 1, fontFamily: 'Orbitron' }}>LEGEND</Typography>
          <Stack spacing={0.5}>
            <LegendItem color="#00ff62" label="200 OK / SAFE" />
            <LegendItem color="#ff003c" label="40x / INTERESTING / CRITICAL" />
            <LegendItem color="rgba(255,255,255,0.8)" label="OTHER" />
          </Stack>
        </Paper>
      </Box>
    </TacticalPanel>
  );
};

const LegendItem = ({ color, label }: { color: string, label: string }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
    <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: color, boxShadow: `0 0 5px ${color}` }} />
    <Typography sx={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.6)', fontWeight: 700 }}>{label}</Typography>
  </Box>
);

const Stack = ({ children, spacing }: { children: React.ReactNode, spacing: number }) => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: spacing }}>{children}</Box>
);

export default VisualizationTab;
