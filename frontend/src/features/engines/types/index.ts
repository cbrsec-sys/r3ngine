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
