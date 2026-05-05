import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import type { SearchResponse, SearchHistoryItem } from '../types';

export const useSearch = (query: string) => {
  return useQuery({
    queryKey: ['search', query],
    queryFn: async () => {
      if (!query) return null;
      const response = await axios.get(`/api/search/`, {
        params: { query, format: 'json' }
      });
      return response.data as SearchResponse;
    },
    enabled: !!query,
  });
};

export const useSearchHistory = () => {
  return useQuery({
    queryKey: ['search-history'],
    queryFn: async () => {
      const response = await axios.get('/api/search/history/');
      return response.data as { status: boolean; results: SearchHistoryItem[] };
    },
  });
};
