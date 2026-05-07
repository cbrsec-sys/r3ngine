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
  manifest: any;
}

export const fetchPlugins = async (): Promise<Plugin[]> => {
  const { data } = await axios.get(API_URL);
  return data;
};

export const uploadPlugin = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await axios.post(`${API_URL}upload/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
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

export const usePlugins = () => {
  return useQuery({ queryKey: ['plugins'], queryFn: fetchPlugins });
};

export const useUploadPlugin = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: uploadPlugin,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['plugins'] }),
  });
};

export const useTogglePlugin = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: togglePlugin,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['plugins'] }),
  });
};
