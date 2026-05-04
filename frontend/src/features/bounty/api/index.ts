import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { getCsrfToken } from '../../settings/api';
import type { HackerOneProgram, ProgramDetails } from '../types';

export const useBountyPrograms = (params: { sort_by?: string; sort_order?: string; bookmarked?: boolean }) => {
  return useQuery({
    queryKey: ['bounty-programs', params],
    queryFn: async () => {
      const url = params.bookmarked 
        ? '/api/hackerone-programs/bookmarked_programs/' 
        : '/api/hackerone-programs/';
      
      const response = await axios.get(url, {
        params: {
          sort_by: params.sort_by,
          sort_order: params.sort_order
        }
      });
      return response.data as HackerOneProgram[];
    },
  });
};

export const useProgramDetails = (handle: string | null) => {
  return useQuery({
    queryKey: ['program-details', handle],
    queryFn: async () => {
      if (!handle) return null;
      const response = await axios.get(`/api/hackerone-programs/${handle}/program_details/`);
      return response.data as ProgramDetails;
    },
    enabled: !!handle,
  });
};

export const useImportPrograms = () => {
  return useMutation({
    mutationFn: async ({ handles, projectSlug }: { handles: string[]; projectSlug: string }) => {
      const response = await axios.post(`/api/hackerone-programs/import_programs/?project_slug=${projectSlug}`, 
        { handles },
        {
          headers: {
            'X-CSRFToken': getCsrfToken(),
          }
        }
      );
      return response.data;
    },
  });
};
