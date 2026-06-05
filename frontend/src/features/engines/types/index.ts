export interface Engine {
  id: number;
  engine_name: string;
  yaml_configuration: string;
  default_engine: boolean;
  tasks: string[];
}

export interface Wordlist {
  id: number;
  name: string;
  short_name: string;
  count: number;
}

export interface HardwareProfile {
  id: number;
  name: string;
  description?: string;
  threads: number;
  rate_limit: number;
  timeout: number;
  delay: number;
  retries: number;
  profile_type: 'builtin' | 'custom';
  is_active: boolean;
  is_default: boolean;
}
