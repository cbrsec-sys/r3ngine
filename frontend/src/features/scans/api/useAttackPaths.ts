import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export interface AttackStep {
  from: string;
  to: string;
  action: string;
  edge_type: string;
  confidence: number;
  validated: boolean;
  status: 'validated' | 'inferred';
}

export interface AttackPath {
  path_id: string;
  risk: string;
  score: number;
  step_count: number;
  steps: AttackStep[];
  potential_impact: string;
  remediation_priority: number;
  vulnerability_id: number | null;
}

export interface AttackPathsResponse {
  total_paths: number;
  paths: AttackPath[];
}

const fetchAttackPaths = async (scanId: number): Promise<AttackPathsResponse> => {
  const { data } = await axios.get(`/api/apme/paths/`, {
    params: { scan_id: scanId },
  });
  return data;
};

export const useAttackPaths = (scanId: number) =>
  useQuery<AttackPathsResponse>({
    queryKey: ['attack-paths', scanId],
    queryFn: () => fetchAttackPaths(scanId),
    staleTime: 5 * 60 * 1000, // 5 min — paths don't change post-scan
    enabled: !!scanId,
  });
