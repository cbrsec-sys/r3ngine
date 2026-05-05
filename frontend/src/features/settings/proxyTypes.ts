export interface ProxySettings {
  use_proxy: boolean;
  proxies: string;
}

export interface ProxyTaskStatus {
  task_id: string;
  status: 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE';
  result: string | null;
  message?: string;
  progress?: number;
}
