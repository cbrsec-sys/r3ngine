import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
// @ts-ignore
import fcose from 'cytoscape-fcose';
// @ts-ignore
import klay from 'cytoscape-klay';
// @ts-ignore
import expandCollapse from 'cytoscape-expand-collapse';

import type { GraphData } from '../api/graphApi';
import { useGraphStore } from '../../../store/useGraphStore';

cytoscape.use(fcose);
cytoscape.use(klay);
cytoscape.use(expandCollapse);

interface GraphCanvasProps {
  data: GraphData;
  layoutName: 'fcose' | 'klay' | 'cose';
  searchQuery: string;
  onInit?: (cy: cytoscape.Core) => void;
}

const SCAN_COLORS = [
  '#00f3ff', '#7000ff', '#ff00f7', '#ff003c', '#ff9f00', 
  '#fffc00', '#00ff62', '#2196f3', '#ec4899', '#8b5cf6'
];

export const GraphCanvas: React.FC<GraphCanvasProps> = ({ data, layoutName, searchQuery, onInit }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const { setSelectedNode } = useGraphStore();

  useEffect(() => {
    if (!containerRef.current) return;

    // Process data to add compound node structures (parent relationships)
    const parentMap = new Map<string, string>();
    data.edges.forEach(edge => {
      const { source, target, label } = edge.data;
      if (['HAS_SUBDOMAIN', 'HAS_ENDPOINT'].includes(label)) {
        if (!parentMap.has(target)) {
           parentMap.set(target, source);
        }
      }
    });

    const processedNodes = data.nodes.map(node => {
      const parentId = parentMap.get(node.data.id);
      return parentId ? { ...node, data: { ...node.data, parent: parentId } } : node;
    });

    const uniqueScans = new Set<number>();
    processedNodes.forEach((n: any) => {
        if (n.data?.scan_ids && Array.isArray(n.data.scan_ids)) {
            n.data.scan_ids.forEach((id: number) => uniqueScans.add(id));
        }
    });
    
    const colorMap: Record<number, string> = {};
    Array.from(uniqueScans).forEach((id, index) => {
        colorMap[id] = SCAN_COLORS[index % SCAN_COLORS.length];
    });

    const cy = cytoscape({
      container: containerRef.current,
      elements: {
        nodes: processedNodes,
        edges: data.edges
      },
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
            'text-margin-y': 5,
            'text-opacity': 0,
            'width': (ele: any) => Math.min(80, 30 + (ele.data('degree_centrality') || 0) * 5),
            'height': (ele: any) => Math.min(80, 30 + (ele.data('degree_centrality') || 0) * 5),
            'border-width': (ele: any) => (ele.data('criticalVulnCount') || 0) > 0 ? 4 : 1,
            'border-color': (ele: any) => (ele.data('criticalVulnCount') || 0) > 0 ? '#ef4444' : 'data(color)',
            'overlay-padding': 6,
            'z-index': '1' as any
          }
        },
        {
          selector: 'node:parent',
          style: {
            'background-opacity': 0.05,
            'border-width': 1,
            'border-style': 'dashed',
            'border-color': '#00f3ff',
            'padding': '20px',
            'text-valign': 'top',
            'text-margin-y': -5,
            'font-size': '14px',
            'font-weight': 'bold',
            'text-opacity': 0.8,
            'shape': 'roundrectangle'
          }
        },
        {
          selector: 'node[type = "Domain"]',
          style: {
            'width': 60,
            'height': 60,
            'font-size': '14px',
            'font-weight': 'bold',
            'text-opacity': 1,
            'shape': 'hexagon',
            'border-width': 2,
            'border-color': '#fff'
          }
        },
        {
          selector: 'node[type = "Vulnerability"]',
          style: {
            'shape': 'diamond',
            'width': 40,
            'height': 40,
          }
        },
        {
          selector: 'node.cy-expand-collapse-collapsed-node',
          style: {
            'background-color': '#1e293b',
            'border-width': 2,
            'border-color': '#00f3ff',
            'shape': 'roundrectangle',
            'text-opacity': 1,
            'label': (ele: any) => `${ele.data('label')} (${ele.data('collapsedChildren').length})`
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
            'opacity': 0.4
          }
        },
        {
            selector: 'node.hover',
            style: {
                'text-opacity': 1,
                'border-width': 4,
                'border-color': '#fff',
                'z-index': '999' as any,
                'text-background-opacity': 0.8,
                'text-background-color': '#0f172a',
                'text-background-padding': '3px',
                'text-background-shape': 'roundrectangle'
            }
        },
        {
            selector: 'node.highlighted',
            style: { 'opacity': 1, 'z-index': '100' as any }
        },
        {
            selector: 'node.faded',
            style: { 'opacity': 0.1, 'text-opacity': 0 }
        },
        {
            selector: 'edge.highlighted',
            style: { 'line-color': '#00f3ff', 'target-arrow-color': '#00f3ff', 'width': 3, 'opacity': 1 }
        },
        {
            selector: 'edge.faded',
            style: { 'opacity': 0.05 }
        }
      ]
    });

    // Initialize expand-collapse API
    const api = (cy as any).expandCollapse({
      layoutBy: {
        name: layoutName,
        animate: true,
        randomize: false,
        fit: true
      },
      fisheye: true,
      animate: true,
      undoable: false,
      expandCollapseCuePosition: 'top-left',
      expandCollapseCueSize: 12,
      expandCollapseCueLineSize: 8,
      expandCueImage: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2300f3ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>',
      collapseCueImage: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2300f3ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="8" y1="12" x2="16" y2="12"></line></svg>'
    });

    // Initial collapse of everything except root domain
    // api.collapseAll();
    
    // Initial Layout
    cy.layout({ 
      name: layoutName,
      animate: true,
      nodeDimensionsIncludeLabels: true,
      ...(layoutName === 'fcose' ? {
        quality: 'default',
        randomize: true,
        nodeRepulsion: 4500,
        idealEdgeLength: 100,
        edgeElasticity: 0.45,
        nestingFactor: 0.1,
        gravity: 0.25,
        numIter: 2500,
      } : layoutName === 'klay' ? {
        klay: {
          direction: 'DOWN',
          spacing: 50,
          nodeLayering: 'NETWORK_SIMPLEX'
        }
      } : {})
    } as any).run();

    cy.on('mouseover', 'node', (e) => {
        const node = e.target;
        const neighborhood = node.neighborhood().add(node);
        cy.elements().addClass('faded');
        neighborhood.removeClass('faded').addClass('highlighted');
        node.addClass('hover');
    });

    cy.on('mouseout', 'node', () => {
        cy.elements().removeClass('faded highlighted hover');
    });

    cy.on('tap', 'node', (e) => {
        const node = e.target;
        setSelectedNode(node.id(), node.data());
    });

    cy.on('tap', (e) => {
        if (e.target === cy) {
            setSelectedNode(null);
        }
    });

    cyRef.current = cy;
    if (onInit) onInit(cy);

    return () => {
      cy.destroy();
    };
  }, [data]);

  // Handle Search and Layout changes without re-initializing
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;

    if (searchQuery) {
      const matches = cy.nodes().filter((node: any) => 
        node.data('label')?.toLowerCase().includes(searchQuery.toLowerCase())
      );

      if (matches.length > 0) {
        cy.elements().addClass('faded');
        matches.removeClass('faded').addClass('highlighted');
        if (matches.length === 1) {
          cy.animate({ center: { eles: matches }, zoom: 1.5, duration: 500 });
        }
      } else {
        cy.elements().addClass('faded');
      }
    } else {
      cy.elements().removeClass('faded highlighted hover');
    }
  }, [searchQuery]);

  useEffect(() => {
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

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
};
