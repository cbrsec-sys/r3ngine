import type { components, operations } from '@/types/api';

export type Vulnerability = components["schemas"]["Vulnerability"];

export type VulnerabilityResponse = operations["listVulnerability_list"]["responses"]["200"]["content"]["application/json"];

