import type { components } from '@/types/api';
import type { SummaryResponseBase } from '../../scans/types';

export type Domain = components["schemas"]["Domain"];

export interface Organization {
  id: number;
  name: string;
  description?: string;
}

export interface Engine {
  id: number;
  engine_name: string;
  yaml_configuration: string;
  default_engine: boolean;
}

/** Response of `GET /api/target-summary/<slug>/<id>/` (`TargetSummaryAPIView`). */
export interface TargetSummaryResponse extends SummaryResponseBase {
  important_subdomains: { name: string; http_status: number | null; page_title: string | null }[];
  target_info: {
    name: string;
    id: number;
    in_scope_ips: string[];
    secondary_domains: string[];
    manual_subdomains: string[];
  };
  vulnerability_highlights: {
    name: string;
    severity: number;
    http_url: string | null;
    discovered_date: string;
  }[];
  subdomains: { name: string; http_status: number | null; page_title: string | null }[];
  endpoints: { http_url: string; http_status: number | null; content_type: string | null }[];
  vulnerabilities: { name: string; severity: number; description: string | null }[];
}
