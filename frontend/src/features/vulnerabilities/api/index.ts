import { useQuery } from '@tanstack/react-query';
import type { Vulnerability } from '../types';

export const useVulnerabilities = (projectSlug: string) => {
  return useQuery<Vulnerability[]>({
    queryKey: ['vulnerabilities', projectSlug],
    queryFn: async () => {
      const response = await fetch(`/api/target/${projectSlug}/vulnerabilities/`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    },
    enabled: !!projectSlug,
  });
};
