import { useQuery } from '@tanstack/react-query';
import type { MonitoringDiscovery, MonitoringStats } from '../types';

export const useMonitoringDiscoveries = (projectSlug: string) => {
  return useQuery<MonitoringDiscovery[]>({
    queryKey: ['monitoring', projectSlug],
    queryFn: async () => {
      const response = await fetch(`/api/monitoring/?slug=${projectSlug}&format=json`, {
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

export const useMonitoringStats = (projectSlug: string) => {
  return useQuery<MonitoringStats>({
    queryKey: ['monitoring-stats', projectSlug],
    queryFn: async () => {
      const response = await fetch(`/api/monitoring/statistics/?slug=${projectSlug}&format=json`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    },
    enabled: !!projectSlug,
  });
};
