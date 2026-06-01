import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_URL = '/api/plugins/';

export interface Plugin {
  name: string;
  slug: string;
  version: string;
  description: string;
  is_enabled: boolean;
  anchor_step: string;
  runtime_position: 'BEFORE' | 'AFTER';
  order_weight: number;
  manifest: Record<string, any>;
  tools_config: Record<string, any>;
  installed_at: string;
  needs_restart: boolean;
  author: string;
  trust_level: 'official' | 'signed_unknown' | 'unsigned' | 'legacy';
}

export interface MarketplacePlugin {
  name: string;
  slug: string;
  version: string;
  description: string;
  category?: string;
  author?: string;
  signed?: boolean;
  is_installed: boolean;
}

// --- CORE FETCHERS ---
export const fetchPlugins = async (): Promise<Plugin[]> => {
  const { data } = await axios.get(API_URL);
  return Array.isArray(data) ? data : data.results || [];
};

export const uploadPlugin = async (file: File): Promise<{ install_id: string }> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await axios.post(`${API_URL}upload/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export interface InstallStep {
  key: string;
  label: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  message: string;
}

export interface InstallStatus {
  steps: InstallStep[];
  status: 'running' | 'success' | 'failed';
  plugin_name: string | null;
  error?: string;
  warning?: string;
}

export const fetchInstallStatus = async (installId: string): Promise<InstallStatus> => {
  const { data } = await axios.get(`${API_URL}install-status/`, { params: { id: installId } });
  return data;
};

export const togglePlugin = async ({ slug, is_enabled }: { slug: string; is_enabled: boolean }) => {
  const { data } = await axios.patch(`${API_URL}${slug}/`, { is_enabled });
  return data;
};

export const updatePluginWeight = async ({ slug, order_weight }: { slug: string; order_weight: number }) => {
  const { data } = await axios.patch(`${API_URL}${slug}/`, { order_weight });
  return data;
};

export const deletePlugin = async (slug: string) => {
  const { data } = await axios.delete(`${API_URL}${slug}/`);
  return data;
};

// --- CORE HOOKS ---
export const usePlugins = () => {
  return useQuery({ queryKey: ['plugins'], queryFn: fetchPlugins });
};

export const useUploadPlugin = () => {
  return useMutation({
    mutationFn: uploadPlugin,
    // Query invalidation is deferred — InstallProgressOverlay calls onComplete when install finishes
  });
};

export const useInstallStatus = (installId: string | null) => {
  return useQuery({
    queryKey: ['plugin-install-status', installId],
    queryFn: () => fetchInstallStatus(installId!),
    enabled: !!installId,
    refetchInterval: (query) =>
      query.state.data?.status === 'running' ? 800 : false,
  });
};

export const useTogglePlugin = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: togglePlugin,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugins'] });
      queryClient.invalidateQueries({ queryKey: ['pluginsRegistry'] });
    },
  });
};

export const useDeletePlugin = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deletePlugin,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugins'] });
      queryClient.invalidateQueries({ queryKey: ['pluginsRegistry'] });
    },
  });
};

export const useUpdatePluginWeight = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updatePluginWeight,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['plugins'] }),
  });
};

// --- MARKETPLACE FETCHERS ---
export const fetchMarketplacePlugins = async (refresh = false): Promise<MarketplacePlugin[]> => {
  const { data } = await axios.get(`${API_URL}marketplace/`, { params: { refresh } });
  return data;
};

export const installMarketplacePlugin = async (slug: string) => {
  const { data } = await axios.post(`${API_URL}marketplace/install/`, { slug });
  return data;
};

// --- MARKETPLACE HOOKS ---
export const useMarketplacePlugins = () => {
  return useQuery({ 
    queryKey: ['marketplace-plugins'], 
    queryFn: () => fetchMarketplacePlugins() 
  });
};

export const useInstallMarketplacePlugin = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: installMarketplacePlugin,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugins'] });
      queryClient.invalidateQueries({ queryKey: ['marketplace-plugins'] });
      queryClient.invalidateQueries({ queryKey: ['pluginsRegistry'] });
    },
  });
};

export const useRefreshMarketplace = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => fetchMarketplacePlugins(true),
    onSuccess: (data) => {
      queryClient.setQueryData(['marketplace-plugins'], data);
    },
  });
};

export const restartOrchestrator = async () => {
  const { data } = await axios.post(`${API_URL}restart-orchestrator/`);
  return data;
};

export const useRestartOrchestrator = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: restartOrchestrator,
    onSuccess: () => {
      // Invalidate queries so we reload plugin status
      queryClient.invalidateQueries({ queryKey: ['plugins'] });
    },
  });
};
