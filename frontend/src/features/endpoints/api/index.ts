import { useQuery } from '@tanstack/react-query';
import type { EndpointResponse } from '../types';

export const useEndpoints = (projectSlug: string, page = 1, searchQuery = '', scanId?: number, gfTag?: string) => {
  return useQuery<EndpointResponse>({
    queryKey: ['endpoints', projectSlug, page, searchQuery, scanId, gfTag],
    queryFn: async () => {
      const url = new URL(`${window.location.origin}/api/listEndpoints/`);
      url.searchParams.append('project', projectSlug);
      url.searchParams.append('page', page.toString());
      
      if (searchQuery) {
        url.searchParams.append('query_param', searchQuery);
      }
      
      if (scanId) {
        url.searchParams.append('scan_history', scanId.toString());
      }
      
      if (gfTag) {
        url.searchParams.append('gf_tag', gfTag);
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
