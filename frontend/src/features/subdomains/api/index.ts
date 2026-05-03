import { useQuery } from '@tanstack/react-query';
import type { SubdomainResponse } from '../types';

export const useSubdomains = (projectSlug: string, page = 1, searchQuery = '', scanId?: number, onlyDirectory = false, targetId?: number) => {
  return useQuery<SubdomainResponse>({
    queryKey: ['subdomains', projectSlug, page, searchQuery, scanId, onlyDirectory, targetId],
    queryFn: async () => {
      const url = new URL(`${window.location.origin}/api/listDatatableSubdomain/`);
      url.searchParams.append('project', projectSlug);
      url.searchParams.append('page', page.toString());
      if (searchQuery) {
        url.searchParams.append('search[value]', searchQuery);
      }
      if (scanId) {
        url.searchParams.append('scan_id', scanId.toString());
      }
      if (targetId) {
        url.searchParams.append('target_id', targetId.toString());
      }
      if (onlyDirectory) {
        url.searchParams.append('only_directory', 'true');
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
