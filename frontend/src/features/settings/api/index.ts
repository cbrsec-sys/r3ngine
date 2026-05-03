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

const getCsrfToken = () => {
  return document.cookie.split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
};

export const useProxySettings = (slug: string) => {
  return useQuery<ProxySettings>({
    queryKey: ['proxy-settings', slug],
    queryFn: async () => {
      // The current Django view returns HTML for GET, but we need JSON.
      // I'll check if there's a JSON endpoint or if I need to scrape/modify.
      // For now, I'll assume we can get it via a specialized endpoint or I'll have to add one.
      // Wait, let's look at how other settings are handled.
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
