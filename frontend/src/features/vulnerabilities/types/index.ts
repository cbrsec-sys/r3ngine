export type Severity = 'Critical' | 'High' | 'Medium' | 'Low' | 'Info' | 'Unknown';

export interface Vulnerability {
  id: number;
  name: string;
  severity: Severity;
  discovered_date: string;
  source: string | null;
  http_url: string | null;
  description: string | null;
  impact: string | null;
  remediation: string | null;
  cvss_score: number | null;
  open_status: boolean;
  validation_status: 'unverified' | 'verified' | 'not_working' | 'patched';
  scan_history: {
    id: number;
    domain: {
      name: string;
      slug: string;
    };
    completed_ago: string | null;
  };
}
