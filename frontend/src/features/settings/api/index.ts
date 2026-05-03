import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

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

export interface OpSecSettings {
  enable_opsec: boolean;
  enable_random_ua: boolean;
  enable_waf_bypass: boolean;
  enable_ja3_randomization: boolean;
  enable_rate_limit: boolean;
  max_rps: number;
  enable_delay: boolean;
  delay_ms: number;
  enable_jitter: boolean;
  jitter_percent: number;
  http_protocol: string;
  custom_dns_servers: string;
  enable_metadata_stripping: boolean;
}

export interface ToolSettings {
  gf_patterns: string[];
  nuclei_templates: string[];
}

export interface ApiVaultSettings {
  netlas_key: string;
  chaos_key: string;
  shodan_key: string;
  censys_id: string;
  censys_secret: string;
  leaklookup_key: string;
  hackerone_username: string;
  hackerone_key: string;
}

export interface InstalledTool {
  id: number;
  name: string;
  description: string;
  logo_url: string | null;
  github_url: string;
  license_url: string | null;
  is_default: boolean;
  is_subdomain_gathering: boolean;
  is_github_cloned: boolean;
  github_clone_path: string | null;
  install_command: string;
  update_command: string | null;
  version_lookup_command: string | null;
}

export interface FileContentResponse {
  status: boolean;
  content: string;
  message?: string;
}

const getCsrfToken = () => {
  return document.cookie.split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
};

export const useProxySettings = (slug: string) => {
  return useQuery<ProxySettings>({
    queryKey: ['proxy-settings', slug],
    queryFn: async () => {
      const response = await axios.get(`/scanEngine/${slug}/proxy_settings`, {
        headers: { 'Accept': 'application/json' }
      });
      return response.data;
    },
  });
};

export const useUpdateProxySettings = (slug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: ProxySettings) => {
      const formData = new FormData();
      if (data.use_proxy) {
        formData.append('use_proxy', 'on');
      }
      formData.append('proxies', data.proxies);
      
      const response = await axios.post(`/scanEngine/${slug}/proxy_settings`, formData, {
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'Accept': 'application/json'
        }
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['proxy-settings', slug] });
    },
  });
};

export const useFetchProxies = (slug: string) => {
  return useMutation({
    mutationFn: async () => {
      const response = await axios.post(`/scanEngine/${slug}/fetch_proxies`, {}, {
        headers: {
          'X-CSRFToken': getCsrfToken()
        }
      });
      return response.data as { task_id: string };
    },
  });
};

export const useProxyTaskStatus = (slug: string, taskId: string | null) => {
  return useQuery<ProxyTaskStatus>({
    queryKey: ['proxy-task-status', slug, taskId],
    queryFn: async () => {
      const response = await axios.get(`/scanEngine/${slug}/task_status/${taskId}`);
      return response.data;
    },
    enabled: !!taskId,
    refetchInterval: (data) => {
      if (data && (data.status === 'SUCCESS' || data.status === 'FAILURE')) {
        return false;
      }
      return 2000;
    },
  });
};

export const useOpSecSettings = (slug: string) => {
  return useQuery<OpSecSettings>({
    queryKey: ['opsec-settings', slug],
    queryFn: async () => {
      const response = await axios.get(`/scanEngine/${slug}/opsec_settings`, {
        headers: { 'Accept': 'application/json' }
      });
      return response.data;
    },
  });
};

export const useUpdateOpSecSettings = (slug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: OpSecSettings) => {
      const formData = new FormData();
      if (data.enable_opsec) formData.append('enable_opsec', 'on');
      if (data.enable_random_ua) formData.append('enable_random_ua', 'on');
      if (data.enable_waf_bypass) formData.append('enable_waf_bypass', 'on');
      if (data.enable_ja3_randomization) formData.append('enable_ja3_randomization', 'on');
      if (data.enable_rate_limit) formData.append('enable_rate_limit', 'on');
      formData.append('max_rps', data.max_rps.toString());
      if (data.enable_delay) formData.append('enable_delay', 'on');
      formData.append('delay_ms', data.delay_ms.toString());
      if (data.enable_jitter) formData.append('enable_jitter', 'on');
      formData.append('jitter_percent', data.jitter_percent.toString());
      formData.append('http_protocol', data.http_protocol);
      formData.append('custom_dns_servers', data.custom_dns_servers);
      if (data.enable_metadata_stripping) formData.append('enable_metadata_stripping', 'on');
      
      const response = await axios.post(`/scanEngine/${slug}/opsec_settings`, formData, {
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'Accept': 'application/json'
        }
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opsec-settings', slug] });
    },
  });
};

export const useToolSettings = (slug: string) => {
  return useQuery<ToolSettings>({
    queryKey: ['toolSettings', slug],
    queryFn: async () => {
      const { data } = await axios.get(`/scanEngine/${slug}/tool_settings`, {
        headers: { Accept: 'application/json' },
      });
      return data;
    },
  });
};

export const useUpdateToolConfig = (slug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ key, content }: { key: string; content: string }) => {
      const formData = new FormData();
      formData.append(key, content);
      const { data } = await axios.post(`/scanEngine/${slug}/tool_settings`, formData, {
        headers: {
          'X-CSRFToken': getCsrfToken(),
          Accept: 'application/json',
        },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['toolSettings', slug] });
    },
  });
};

export const useUploadToolFiles = (slug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ key, files }: { key: string; files: File[] }) => {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append(`${key}[]`, file);
      });
      const { data } = await axios.post(`/scanEngine/${slug}/tool_settings`, formData, {
        headers: {
          'X-CSRFToken': getCsrfToken(),
          Accept: 'application/json',
          'Content-Type': 'multipart/form-data',
        },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['toolSettings', slug] });
    },
  });
};

export const useFileContent = (params: Record<string, string>) => {
  return useQuery<FileContentResponse>({
    queryKey: ['fileContent', params],
    queryFn: async () => {
      const { data } = await axios.get(`/api/getFileContents/`, {
        params,
      });
      return data;
    },
    enabled: Object.keys(params).length > 0,
  });
};

export const useToolArsenal = (slug: string) => {
  return useQuery<{ tools: InstalledTool[] }>({
    queryKey: ['toolArsenal', slug],
    queryFn: async () => {
      const { data } = await axios.get(`/scanEngine/${slug}/tool_arsenal`, {
        headers: { Accept: 'application/json' },
      });
      return data;
    },
  });
};

export const useToolVersion = () => {
  return useMutation({
    mutationFn: async ({ toolId, type }: { toolId: number; type: 'current' | 'latest' }) => {
      const endpoint = type === 'current' 
        ? `/api/external/tool/get_current_release/` 
        : `/api/github/tool/get_latest_releases/`;
      const { data } = await axios.get(endpoint, {
        params: { tool_id: toolId },
      });
      return data;
    },
  });
};

export const useUpdateTool = () => {
  return useMutation({
    mutationFn: async (toolId: number) => {
      const { data } = await axios.get(`/api/tool/update/`, {
        params: { tool_id: toolId },
      });
      return data;
    },
  });
};

export const useUninstallTool = (slug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (toolId: number) => {
      const { data } = await axios.get(`/api/tool/uninstall/`, {
        params: { tool_id: toolId },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['toolArsenal', slug] });
    },
  });
};

export const useAddTool = (slug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (formData: FormData) => {
      const { data } = await axios.post(`/scanEngine/${slug}/tool_arsenal/add/`, formData, {
        headers: {
          'X-CSRFToken': getCsrfToken(),
          Accept: 'application/json',
        },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['toolArsenal', slug] });
    },
  });
};

export const useModifyTool = (slug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ toolId, formData }: { toolId: number; formData: FormData }) => {
      const { data } = await axios.post(`/scanEngine/${slug}/tool_arsenal/update/${toolId}`, formData, {
        headers: {
          'X-CSRFToken': getCsrfToken(),
          Accept: 'application/json',
        },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['toolArsenal', slug] });
    },
  });
};

export const useApiVault = (slug: string) => {
  return useQuery<ApiVaultSettings>({
    queryKey: ['api-vault', slug],
    queryFn: async () => {
      const response = await axios.get(`/scanEngine/${slug}/api_vault`, {
        headers: { 'Accept': 'application/json' }
      });
      return response.data;
    },
  });
};

export const useUpdateApiVault = (slug: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: ApiVaultSettings) => {
      const formData = new FormData();
      formData.append('key_netlas', data.netlas_key);
      formData.append('key_chaos', data.chaos_key);
      formData.append('key_shodan', data.shodan_key);
      formData.append('key_censys_id', data.censys_id);
      formData.append('key_censys_secret', data.censys_secret);
      formData.append('key_leaklookup', data.leaklookup_key);
      formData.append('username_hackerone', data.hackerone_username);
      formData.append('key_hackerone', data.hackerone_key);
      
      const response = await axios.post(`/scanEngine/${slug}/api_vault`, formData, {
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'Accept': 'application/json'
        }
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-vault', slug] });
    },
  });
};

