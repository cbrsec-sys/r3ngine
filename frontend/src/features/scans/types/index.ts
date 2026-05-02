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

export interface ScheduledScan {
  id: number;
  name: string;
  task: string;
  description: string;
  frequency: string;
  enabled: boolean;
  last_run_at: string | null;
  total_run_count: number;
  one_off: boolean;
  kwargs: string;
  date_changed: string;
}

export interface SubScan {
  id: number;
  type: string;
  start_scan_date: string;
  stop_scan_date: string | null;
  status: number;
  subdomain: number;
  subdomain_name: string;
  engine: string;
  time_taken: string;
  elapsed_time: string;
  completed_ago: string;
  error_message: string | null;
}
