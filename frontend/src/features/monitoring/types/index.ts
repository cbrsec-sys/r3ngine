export interface MonitoringDiscovery {
  id: number;
  domain: number;
  domain_name: string;
  discovery_type: 'subdomain' | 'directory' | 'login' | 'status_change' | 'ip';
  content: string;
  discovered_at: string;
  scan_history_id: number | null;
}

export interface MonitoringStats {
  total_discoveries: number;
  subdomain_discoveries: number;
  endpoint_discoveries: number;
  login_discoveries: number;
}
