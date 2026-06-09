import { useMutation } from '@tanstack/react-query';
import type { WorkflowSlug, StartWorkflowPayload, StartWorkflowResponse } from '../types';

const CSRF_TOKEN = () =>
  document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';

export const useStartWorkflow = () => {
  return useMutation({
    mutationFn: async ({
      slug,
      payload,
    }: {
      slug: WorkflowSlug;
      payload: StartWorkflowPayload;
    }) => {
      const response = await fetch(`/api/v1/workflows/${slug}/start/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': CSRF_TOKEN(),
        },
        body: JSON.stringify(payload),
        credentials: 'include',
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to start workflow');
      }
      return response.json() as Promise<StartWorkflowResponse>;
    },
  });
};
