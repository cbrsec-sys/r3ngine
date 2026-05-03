export type TodoNote = {
  id: number;
  title: string;
  description: string;
  is_done: boolean;
  is_important: boolean;
  scan_history?: number;
  subdomain?: number;
  project: number;
  domain_name?: string;
  subdomain_name?: string;
};

export type CreateTodoData = {
  title: string;
  description: string;
  project: string; // project slug
  subdomain_id?: number;
  scan_history_id?: number;
};
