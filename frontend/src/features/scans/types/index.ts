import type { components } from '@/types/api';

export type ScanHistory = components["schemas"]["ScanHistory"];
export type ScheduledScan = components["schemas"]["PeriodicTask"];
export type SubScan = components["schemas"]["SubScan"];

export interface SecretLeak {
  id: number;
  leak_type: string;
  leak_content: string;
  found_in: string;
}
