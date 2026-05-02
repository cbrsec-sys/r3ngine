import { useQuery } from '@tanstack/react-query';
import type { SubdomainResponse } from '../types';

export const useSubdomains = (projectSlug: string, page = 1, searchQuery = '') => {
  return useQuery<SubdomainResponse>({
    queryKey: ['subdomains', projectSlug, page, searchQuery],
    queryFn: async () => {
      const url = new URL(`${window.location.origin}/api/listDatatableSubdomain/`);
      url.searchParams.append('project', projectSlug);
      url.searchParams.append('page', page.toString());
      if (searchQuery) {
        url.searchParams.append('search[value]', searchQuery);
      }
      url.searchParams.append('format', 'json');

      const response = await fetch(url.toString(), {
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
