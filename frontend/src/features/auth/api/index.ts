import { useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { getCsrfToken } from '../../settings/api';
import type { LoginResponse } from '../types';

export const useLogin = () => {
  return useMutation({
    mutationFn: async (data: FormData) => {
      const response = await axios.post('/login/', data, {
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'Content-Type': 'multipart/form-data',
          'Accept': 'application/json'
        },
      });
      return response.data as LoginResponse;
    },
  });
};

export interface OnboardingData {
  project_name: string;
  create_username?: string;
  create_password?: string;
  create_user_role?: string;
  key_openai?: string;
  key_netlas?: string;
  key_chaos?: string;
  key_hackerone?: string;
  username_hackerone?: string;
  key_shodan?: string;
  key_censys_id?: string;
  key_censys_secret?: string;
  bug_bounty_mode: boolean;
}

export const useOnboarding = () => {
  return useMutation({
    mutationFn: async (data: OnboardingData) => {
      const formData = new FormData();
      Object.entries(data).forEach(([key, value]) => {
        if (value !== undefined) {
          if (typeof value === 'boolean') {
            if (value) formData.append(key, 'on');
          } else {
            formData.append(key, value);
          }
        }
      });

      const response = await axios.post('/onboarding/', formData, {
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'Content-Type': 'multipart/form-data',
          'Accept': 'application/json'
        },
      });
      return response.data;
    },
  });
};
