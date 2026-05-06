import { create } from 'zustand';

export type NodeData = {
    id: string;
    label: string;
    type: string;
    color: string;
    scan_ids: number[];
    degree_centrality: number;
    criticalVulnCount: number;
    highVulnCount: number;
    severity?: number;
    blastRadius?: number;
};

interface GraphState {
    selectedNodeId: string | null;
    selectedNodeData: NodeData | null;
    activePanel: 'details' | 'tickets' | 'blastRadius' | null;
    severityFilter: number | null;
    setSelectedNode: (id: string | null, data?: NodeData | null) => void;
    setActivePanel: (panel: 'details' | 'tickets' | 'blastRadius' | null) => void;
    setSeverityFilter: (severity: number | null) => void;
}

export const useGraphStore = create<GraphState>((set) => ({
    selectedNodeId: null,
    selectedNodeData: null,
    activePanel: null,
    severityFilter: null,
    setSelectedNode: (id, data = null) => set({ 
        selectedNodeId: id, 
        selectedNodeData: data,
        activePanel: id ? 'details' : null 
    }),
    setActivePanel: (panel) => set({ activePanel: panel }),
    setSeverityFilter: (severity) => set({ severityFilter: severity }),
}));
