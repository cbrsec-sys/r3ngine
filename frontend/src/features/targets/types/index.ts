import type { components } from '@/types/api';

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
