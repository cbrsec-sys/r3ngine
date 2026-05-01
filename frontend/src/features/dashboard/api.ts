import { useQuery } from '@tanstack/react-query';

export interface DashboardData {
  project_info: {
    name: string;
    slug: string;
  };
  rengine_version: string;
  kpis: {

    domain_count: number;
    subdomain_count: number;
    endpoint_count: number;
    vulnerability_count: number;
    critical_count: number;
    high_count: number;
    medium_count: number;
    low_count: number;
    info_count: number;
    unknown_count: number;
    secret_leak_count: number;
    alive_count: number;
    endpoint_alive_count: number;
    total_vul_count: number;
  };
  trends: {
    targets_in_last_week: number[];
    subdomains_in_last_week: number[];
    endpoints_in_last_week: number[];
    vulns_in_last_week: number[];
    leaks_in_last_week: number[];
    last_7_dates: string[];
  };
  most_used_port: Array<{ number: number; service_name: string; count: number }>;
  most_used_ip: Array<{ address: string; count: number }>;
  most_used_tech: Array<{ name: string; count: number }>;
  most_common_cve: Array<{ name: string; count: number }>;
  most_common_cwe: Array<{ name: string; count: number }>;
  most_common_tags: Array<{ name: string; count: number }>;
  asset_countries: { name: string; iso: string; count: number }[];
  most_vulnerable_targets: { name: string; vuln_count: number }[];
  activity_feed: any[];
  vulnerability_feed: any[];
}

export const useDashboardData = (projectSlug: string) => {
  return useQuery<DashboardData>({
    queryKey: ['dashboard', projectSlug],
    queryFn: async () => {
      const response = await fetch(`/api/dashboard/${projectSlug}/`, {
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
