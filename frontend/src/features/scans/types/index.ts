export interface ScanHistory {
  id: number;
  start_scan_date: string;
  stop_scan_date: string | null;
  scan_status: number;
  domain: {
    id: number;
    name: string;
    slug: string;
  };
  scan_type: {
    id: number;
    engine_name: string;
  };
  subdomain_count: number;
  endpoint_count: number;
  vulnerability_count: number;
  current_progress: number;
  completed_time: number;
  elapsed_time: string;
  completed_ago: string;
  organizations: string[];
  initiated_by: {
    username: string;
  } | null;
}
