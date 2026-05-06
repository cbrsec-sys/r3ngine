import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ScanHistory, ScheduledScan, SubScan } from '../types';
import type { Domain } from '../../targets/types';

export const useDomains = (projectSlug: string) => {
  return useQuery<Domain[]>({
    queryKey: ['domains', projectSlug],
    queryFn: async () => {
      const response = await fetch(`/api/listTargets/?slug=${projectSlug}`, {
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

export const useSubScans = (projectSlug: string) => {
  return useQuery<SubScan[]>({
    queryKey: ['subscans', projectSlug],
    queryFn: async () => {
      const response = await fetch(`/api/subscans/?project=${projectSlug}`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      return Array.isArray(data) ? data : data.results || [];
    },
    enabled: !!projectSlug,
  });
};

export const useBulkStopSubScans = (projectSlug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (ids: number[]) => {
      const response = await fetch('/api/subscans/bulk_stop/', {
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
      queryClient.invalidateQueries({ queryKey: ['subscans', projectSlug] });
    },
  });
};

export const useBulkDeleteSubScans = (projectSlug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (ids: number[]) => {
      const response = await fetch('/api/subscans/bulk_delete/', {
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
      queryClient.invalidateQueries({ queryKey: ['subscans', projectSlug] });
    },
  });
};

export const useScansHistory = (project: string) => {
  return useQuery<ScanHistory[]>({
    queryKey: ['scans-history', project],
    queryFn: async () => {
      const response = await fetch(`/api/listScans/?project=${project}`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      return Array.isArray(data) ? data : data.results || [];
    },
    enabled: !!project,
  });
};

export const useStopScan = (projectSlug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await fetch(`/api/listScans/${id}/stop_scan/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '',
        },
        credentials: 'include',
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans-history', projectSlug] });
    },
  });
};

export const useDeleteScan = (projectSlug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await fetch(`/api/listScans/${id}/delete_scan/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '',
        },
        credentials: 'include',
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans-history', projectSlug] });
    },
  });
};

export const useBulkScanAction = (projectSlug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ action, ids }: { action: 'bulk_stop' | 'bulk_delete', ids: number[] }) => {
      const response = await fetch(`/api/listScans/${action}/`, {
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
      queryClient.invalidateQueries({ queryKey: ['scans-history', projectSlug] });
    },
  });
};

export const useScanSummary = (projectSlug: string, scanId: number) => {
  return useQuery({
    queryKey: ['scan-summary', projectSlug, scanId],
    queryFn: async () => {
      const response = await fetch(`/api/scan-summary/${projectSlug}/${scanId}/`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    },
    enabled: !!projectSlug && !!scanId,
    refetchInterval: (query: any) => {
      const data = query.state.data;
      if (data && data.scan_info && data.scan_info.scan_status === 2) return false;
      return 5000;
    }
  });
};

export const useSecretLeaks = (projectSlug: string, scanId: number) => {
  return useQuery({
    queryKey: ['secret-leaks', projectSlug, scanId],
    queryFn: async () => {
      const response = await fetch(`/api/scan-summary/${projectSlug}/${scanId}/`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      return data.secret_leaks || [];
    },
    enabled: !!projectSlug && !!scanId,
  });
};

export const useScanStatus = (projectSlug: string) => {
  return useQuery({
    queryKey: ['scan-status', projectSlug],
    queryFn: async () => {
      const response = await fetch(`/api/scan_status/?project=${projectSlug}`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    },
    enabled: !!projectSlug,
    refetchInterval: 10000, // Poll every 10 seconds
  });
};

export const useStopScanAction = (projectSlug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await fetch(`/api/action/stop/scan/?scan_id=${id}`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '',
        },
        credentials: 'include',
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scan-status', projectSlug] });
    }
  });
};

export const useDeleteScanAction = (projectSlug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await fetch(`/api/action/rows/delete/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '',
        },
        credentials: 'include',
        body: JSON.stringify({
          rows: [id],
          model: 'ScanHistory'
        })
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scan-status', projectSlug] });
    }
  });
};

export const useActivityLogs = (activityId: number | null) => {
  return useQuery({
    queryKey: ['activity-logs', activityId],
    queryFn: async () => {
      const response = await fetch(`/api/listActivityLogs/?activity_id=${activityId}`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      return Array.isArray(data) ? data : data.results || [];
    },
    enabled: !!activityId,
    refetchInterval: 5000, // Poll every 5 seconds for real-time logs
  });
};

export const useStressTelemetry = (scanId: number | string | undefined) => {
  return useQuery({
    queryKey: ['stress-telemetry', scanId],
    queryFn: async () => {
      if (!scanId) return [];
      const response = await fetch(`/api/stress-testing/${scanId}/`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      return Array.isArray(data.results) ? data.results : [];
    },
    enabled: !!scanId,
    refetchInterval: 15000, // Refresh every 15s during test runs
  });
};
