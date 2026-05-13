import { useSuspenseQuery, useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';

export interface GraphData {
  nodes: any[];
  edges: any[];
}

export const useGraphData = (projectSlug: string, scanId?: number, targetId?: number) => {
  return useSuspenseQuery<GraphData>({
    queryKey: ['graph-data', projectSlug, scanId, targetId],
    queryFn: async () => {
      let apiUrl = `/${projectSlug}/api/graph/scan/${scanId}/data/`;
      if (targetId && (!scanId || scanId === 0)) {
        apiUrl = `/${projectSlug}/api/graph/target/${targetId}/data/`;
      }
      const response = await fetch(apiUrl, { credentials: 'include' });
      if (!response.ok) {
        throw new Error('Failed to fetch graph data');
      }
      return response.json();
    }
  });
};

export const useGraphNodeDetails = (projectSlug: string, nodeId: string | null) => {
  return useQuery({
    queryKey: ['graph-node-details', projectSlug, nodeId],
    queryFn: async () => {
      const response = await fetch(`/${projectSlug}/api/graph/node/${nodeId}/details/`, { credentials: 'include' });
      if (!response.ok) {
        throw new Error('Failed to fetch node details');
      }
      return response.json();
    },
    enabled: !!nodeId,
  });
};

export const useGraphBlastRadius = (projectSlug: string, nodeId: string | null) => {
  return useQuery({
    queryKey: ['graph-blast-radius', projectSlug, nodeId],
    queryFn: async () => {
      const response = await fetch(`/${projectSlug}/api/graph/blast-radius/${nodeId}/`, { credentials: 'include' });
      if (!response.ok) {
        throw new Error('Failed to fetch blast radius');
      }
      return response.json();
    },
    enabled: !!nodeId,
  });
};

export const useCreateTicket = (projectSlug: string) => {
  return useMutation({
    mutationFn: async (nodeId: string) => {
      const response = await axios.post(`/${projectSlug}/api/graph/node/${nodeId}/ticket/`);
      return response.data;
    }
  });
};
