import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { TodoNote, CreateTodoData } from '../types';

export const useTodoNotes = (projectSlug: string) => {
  return useQuery({
    queryKey: ['todos', projectSlug],
    queryFn: async () => {
      const response = await axios.get(`/api/listTodoNotes/?project=${projectSlug}`);
      return response.data.notes as TodoNote[];
    },
  });
};

export const useCreateTodo = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateTodoData) => {
      const response = await axios.post('/api/add/recon_note/', data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['todos', variables.project] });
    },
  });
};

export const useToggleTodoStatus = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, projectSlug }: { id: number; projectSlug: string }) => {
      const response = await axios.post('/recon_note/flip_todo_status', { id });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['todos', variables.projectSlug] });
    },
  });
};

export const useToggleImportantStatus = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, projectSlug }: { id: number; projectSlug: string }) => {
      const response = await axios.post('/recon_note/flip_important_status', { id });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['todos', variables.projectSlug] });
    },
  });
};

export const useDeleteTodo = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, projectSlug }: { id: number; projectSlug: string }) => {
      const response = await axios.post('/recon_note/delete_note', { id });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['todos', variables.projectSlug] });
    },
  });
};
