import type { components, operations } from '@/types/api';

export type Vulnerability = components["schemas"]["Vulnerability"];

export type VulnerabilityResponse = operations["api_listVulnerability_list"]["responses"]["200"]["content"]["application/json"];


/**
 * A nested `CveId` row. `VulnerabilitySerializer` uses depth=2 and so returns every
 * enrichment column, while the generated schema only lists `id`, `name` and `is_cisa_kev`.
 */
export type VulnerabilityCve = NonNullable<Vulnerability["cve_ids"]>[number] & {
  cvss_v31_base_score?: number | null;
  attack_vector?: string | null;
  attack_complexity?: string | null;
  privileges_required?: string | null;
  user_interaction?: string | null;
  confidentiality_impact?: string | null;
  integrity_impact?: string | null;
  availability_impact?: string | null;
  epss_score?: number | null;
  epss_percentile?: number | null;
  published_date?: string | null;
  last_modified_date?: string | null;
  vulnerability_type?: string | null;
};

/** Response of `GET /api/tools/gpt_vulnerability_report/`. */
export interface GptVulnerabilityReport {
  status: boolean;
  description?: string;
  impact?: string;
  remediation?: string;
  references?: string[];
  error?: string;
}

/**
 * A vulnerability shown in a detail modal: after an AI analysis `references` holds the
 * report's newline-joined URLs instead of the serializer's `{ id, url }` rows.
 */
export type VulnerabilityWithReportReferences = Omit<Vulnerability, "references"> & {
  references?: Vulnerability["references"] | string;
};
