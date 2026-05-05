import axios from 'axios';
import { useQuery } from '@tanstack/react-query';

export const useWhois = (target: string, isReload: boolean = false) => {
  return useQuery({
    queryKey: ['whois', target, isReload],
    queryFn: async () => {
      const response = await axios.get(`/api/tools/whois/?target=${target}${isReload ? '&is_reload=true' : ''}`);
      return response.data;
    },
    enabled: false, // Don't run on mount
  });
};

export const useCMSDetector = (url: string) => {
  return useQuery({
    queryKey: ['cms-detector', url],
    queryFn: async () => {
      const response = await axios.get(`/api/tools/cms_detector/?url=${url}`);
      return response.data;
    },
    enabled: false,
  });
};

export const useCVEDetails = (cveId: string) => {
  return useQuery({
    queryKey: ['cve-details', cveId],
    queryFn: async () => {
      const response = await axios.get(`/api/tools/cve_details/?cve_id=${cveId}`);
      return response.data;
    },
    enabled: false,
  });
};

export const useWafDetector = (url: string) => {
  return useQuery({
    queryKey: ['waf-detector', url],
    queryFn: async () => {
      const response = await axios.get(`/api/tools/waf_detector/?url=${url}`);
      return response.data;
    },
    enabled: false,
  });
};
