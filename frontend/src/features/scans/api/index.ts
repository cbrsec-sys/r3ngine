import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ScanHistory, ScheduledScan } from '../types';

export const useScans = (projectSlug: string) => {
  return useQuery<ScanHistory[]>({
    queryKey: ['scans', projectSlug],
    queryFn: async () => {
      const response = await fetch(`/api/listScanHistory/?project=${projectSlug}`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      if (Array.isArray(data)) return data;
      if (data.results && Array.isArray(data.results)) return data.results;
      if (data.data && Array.isArray(data.data)) return data.data;
      return [];
    },
    enabled: !!projectSlug,
  });
};

export const useInitiateScan = (projectSlug: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (params: {
      domain_id: number | number[];
      engine_id: number;
      importSubdomainTextArea?: string[];
      outOfScopeSubdomainTextarea?: string[];
      startingPointPath?: string;
      excludedPaths?: string | string[];
      customDorkSwitch?: boolean;
      customDorkTextarea?: string;
      api_discovery_tools?: string[];
      kr_wordlist?: string;
      spiderfoot_scan?: boolean;
    }) => {
      const response = await fetch('/api/action/initiate/scan/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '',
        },
        credentials: 'include',
        body: JSON.stringify(params),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to initiate scan');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans', projectSlug] });
    },
  });
};

export const useScheduledScans = () => {
  return useQuery<ScheduledScan[]>({
    queryKey: ['scheduled-scans'],
    queryFn: async () => {
      const response = await fetch('/api/scheduledScans/', {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      return Array.isArray(data) ? data : data.results || [];
    },
  });
};

export const useToggleScheduledScan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await fetch(`/api/scheduledScans/${id}/toggle/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '',
        },
        credentials: 'include',
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-scans'] });
    },
  });
};

export const useBulkDeleteScheduledScans = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (ids: number[]) => {
      const response = await fetch('/api/scheduledScans/bulk_delete/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '',
        },
        credentials: 'include',
        body: JSON.stringify({ ids }),
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-scans'] });
    },
  });
};
