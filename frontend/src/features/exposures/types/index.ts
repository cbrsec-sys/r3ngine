import type { Vulnerability } from '@/features/vulnerabilities/types';
import type { Subdomain } from '@/features/subdomains/types';
import type { Endpoint } from '@/features/endpoints/types';

export interface ExposureEvidence {
  id: number;
  exposure: number;
  evidence_type: 'port' | 'header' | 'tag' | 'cpe';
  evidence_value: string;
  endpoint?: Endpoint;
  subdomain?: Subdomain;
  created_at: string;
}

export interface Exposure {
  id: number;
  scan_history: number;
  type: string[];
  risk_score: number;
  status: 'open' | 'resolved' | 'false_positive';
  evidence: ExposureEvidence[];
  vulnerabilities: Vulnerability[];
  created_at: string;
  updated_at: string;
}

export interface ExposuresResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Exposure[];
}

export interface ExposureQueryParams {
  project?: string;
  target_id?: string;
  scan_history?: string;
  status?: string;
  type?: string;
  page?: number;
  length?: number;
}
