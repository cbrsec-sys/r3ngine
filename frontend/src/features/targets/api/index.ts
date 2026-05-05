import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Domain, Organization } from '../types';

export const useDomains = (projectSlug: string) => {
  return useQuery<Domain[]>({
    queryKey: ['domains', projectSlug],
    queryFn: async () => {
      const response = await fetch(`/api/listTargets/?slug=${projectSlug}`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      if (Array.isArray(data)) return data;
      if (data.results && Array.isArray(data.results)) return data.results;
      if (data.data && Array.isArray(data.data)) return data.data;
      return [];
    },
    enabled: !!projectSlug,
  });
};

export const useAddTarget = (projectSlug: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (params: {
      domain_name: string;
      project_slug: string;
      organization_ids?: number[];
    }) => {
      const response = await fetch('/api/target/add/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '',
        },
        credentials: 'include',
        body: JSON.stringify({
          domain_name: params.domain_name,
          slug: params.project_slug,
          organization: params.organization_ids
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to add target');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains', projectSlug] });
    },
  });
};

export const useOrganizations = () => {
  return useQuery<Organization[]>({
    queryKey: ['organizations'],
    queryFn: async () => {
      const response = await fetch('/api/listOrganizations/', {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      if (Array.isArray(data)) return data;
      if (data.organizations && Array.isArray(data.organizations)) return data.organizations;
      if (data.results && Array.isArray(data.results)) return data.results;
      return [];
    },
  });
};

export const useDeleteTargets = (projectSlug: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (targetIds: number[]) => {
      const response = await fetch('/api/action/delete/rows/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '',
        },
        credentials: 'include',
        body: JSON.stringify({
          type: 'target',
          rows: targetIds,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to delete targets');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['domains', projectSlug] });
    },
  });
};

export const useTargetSummary = (projectSlug: string, targetId: number) => {
  return useQuery({
    queryKey: ['target-summary', projectSlug, targetId],
    queryFn: async () => {
      const response = await fetch(`/api/target-summary/${projectSlug}/${targetId}/`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    },
    enabled: !!projectSlug && !!targetId,
  });
};
