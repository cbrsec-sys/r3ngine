import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ScanProfile, CreateProfilePayload } from '../types';

const CSRF_TOKEN = () =>
  document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';

export const useScanProfiles = () => {
  return useQuery<ScanProfile[]>({
    queryKey: ['scanProfiles'],
    queryFn: async () => {
      const response = await fetch('/api/scanProfiles/', {
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      return Array.isArray(data) ? data : (data.results || []);
    },
  });
};

export const useCreateScanProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateProfilePayload) => {
      const response = await fetch('/api/scanProfiles/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': CSRF_TOKEN(),
        },
        body: JSON.stringify(payload),
        credentials: 'include',
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to create scan profile');
      }
      return response.json() as Promise<ScanProfile>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scanProfiles'] });
    },
  });
};

export const useDeleteScanProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const response = await fetch(`/api/scanProfiles/${encodeURIComponent(name)}/`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': CSRF_TOKEN(),
        },
        credentials: 'include',
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to delete scan profile');
      }
      // DELETE may return 204 No Content
      if (response.status === 204) {
        return null;
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scanProfiles'] });
    },
  });
};
