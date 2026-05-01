import { useQuery } from '@tanstack/react-query';

export interface MonitoringStats {
  total_discoveries: number;
  subdomain_discoveries: number;
  endpoint_discoveries: number;
  login_discoveries: number;
}

export interface Discovery {
  id: number;
  domain_name: string;
  discovery_type: string;
  content: any;
  discovered_at: string;
  scan_history_id: number | null;
}

export const fetchMonitoringStats = async (slug: string): Promise<MonitoringStats> => {
  const response = await fetch(`/api/monitoring/statistics/?slug=${slug}`, {
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Network response was not ok');
  return response.json();
};

export const fetchDiscoveries = async (slug: string): Promise<Discovery[]> => {
  const response = await fetch(`/api/monitoring/?slug=${slug}`, {
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Network response was not ok');
  return response.json();
};

export const useMonitoringData = (slug: string) => {
  const statsQuery = useQuery({
    queryKey: ['monitoring', 'stats', slug],
    queryFn: () => fetchMonitoringStats(slug),
  });

  const discoveriesQuery = useQuery({
    queryKey: ['monitoring', 'discoveries', slug],
    queryFn: () => fetchDiscoveries(slug),
  });

  return {
    stats: statsQuery.data,
    discoveries: discoveriesQuery.data,
    isLoading: statsQuery.isLoading || discoveriesQuery.isLoading,
    isError: statsQuery.isError || discoveriesQuery.isError,
  };
};
