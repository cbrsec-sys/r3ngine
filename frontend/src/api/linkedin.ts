import axios from './axiosConfig';

export interface LinkedInSessionStatus {
  is_valid: boolean;
  last_validated_at: string | null;
  username: string;
  has_state_file: boolean;
  has_cookies: boolean;
}

export const getLinkedInSessionStatus = async (): Promise<LinkedInSessionStatus> => {
  const res = await axios.get<LinkedInSessionStatus>('/api/linkedin/session/status/');
  return res.data;
};

export const uploadLinkedInStateFile = async (file: File): Promise<void> => {
  const formData = new FormData();
  formData.append('state_file', file);
  await axios.post('/api/linkedin/session/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const uploadLinkedInCookiesJson = async (cookiesJson: string): Promise<void> => {
  await axios.post('/api/linkedin/session/upload/', { cookies_json: cookiesJson });
};

export const revokeLinkedInSession = async (): Promise<void> => {
  await axios.delete('/api/linkedin/session/');
};

export const downloadLinkedInHelperScript = (): void => {
  window.location.href = '/api/linkedin/session/helper/';
};
