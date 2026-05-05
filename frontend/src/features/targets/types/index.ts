export interface Domain {
  id: number;
  name: string;
  description: string | null;
  insert_date: string;
  insert_date_humanized: string;
  start_scan_date: string | null;
  start_scan_date_humanized: string | null;
  vuln_count: number | null;
  organization: string[] | null;
  most_recent_scan: number | null;
  is_monitored: boolean;
  monitor_frequency: 'hourly' | 'daily' | 'weekly' | 'monthly';
  last_monitored: string | null;
  project: number;
}

export interface Organization {
  id: number;
  name: string;
  description: string | null;
  insert_date: string;
  domains: number[];
  project: number;
}
