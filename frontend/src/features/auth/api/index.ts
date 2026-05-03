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
