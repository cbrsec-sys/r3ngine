export interface ScanProfile {
  id: number;
  name: string;
  description: string;
  category: 'speed' | 'evasion' | 'content' | 'network' | 'general' | 'hardware';
  is_builtin: boolean;
  rate_limit: number | null;
  delay: number | null;
  threads: number | null;
  timeout: number | null;
  retries: number | null;
  passive: boolean;
  active: boolean;
  stealth: boolean;
  headless: boolean;
  screenshot: boolean;
  hunt_secrets: boolean;
  nuclei_full: boolean;
  brute_dns: boolean;
  brute_http: boolean;
  test_ssl: boolean;
  all_ports: boolean;
  tor: boolean;
  fragment: boolean;
}

export interface CreateProfilePayload {
  name: string;
  description?: string;
  category?: ScanProfile['category'];
  rate_limit?: number;
  delay?: number;
  threads?: number;
  timeout?: number;
  retries?: number;
  passive?: boolean;
  active?: boolean;
  stealth?: boolean;
  hunt_secrets?: boolean;
}
