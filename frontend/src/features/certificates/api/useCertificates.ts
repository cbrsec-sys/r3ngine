import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export interface CertificateRecord {
  id: number;
  host: string;
  port: number;
  subject_cn: string | null;
  subject_an: string[];
  issuer_cn: string | null;
  issuer_org: string | null;
  not_before: string | null;
  not_after: string | null;
  tls_version: string | null;
  cipher: string | null;
  fingerprint_sha256: string | null;
  self_signed: boolean;
  mismatched: boolean;
  is_expired: boolean;
  has_weak_cipher: boolean;
}

export interface CertificateResponse {
  count: number;
  results: CertificateRecord[];
}

export const useCertificates = (scanId: number | undefined) =>
  useQuery<CertificateResponse>({
    queryKey: ['certificates', scanId],
    queryFn: async () => {
      const { data } = await axios.get<CertificateResponse>(
        `/api/certs/?scan_id=${scanId}`
      );
      return data;
    },
    enabled: scanId !== undefined,
  });
