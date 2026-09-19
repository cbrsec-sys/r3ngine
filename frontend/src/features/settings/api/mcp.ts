import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { getCsrfToken } from '../../../api/axiosConfig';

export type McpTransportMode = 'stdio' | 'http' | 'both';

export interface McpSettings {
  transport_mode: McpTransportMode;
}

export interface McpKey {
  id: number;
  name: string;
  prefix: string;
  created_at: string | null;
  last_used_at: string | null;
  revoked_at: string | null;
  status: 'active' | 'revoked';
  secret?: string;
}

export interface McpSession {
  id: string;
  session_id: string;
  key_id: number;
  key_name: string;
  key_prefix: string;
  user_id: number;
  username: string;
  transport: 'stdio' | 'http';
  client_name: string;
  client_version: string;
  user_agent: string;
  source_ip: string | null;
  connected_at: string | null;
  last_seen_at: string | null;
  revoked_at: string | null;
  ended_at: string | null;
  connected: boolean;
  status: 'connected' | 'idle' | 'revoked' | 'ended';
}

export interface McpAuditEvent {
  id: number;
  session_id: string | null;
  created_at: string | null;
  tool_name: string;
  method: string;
  path: string;
  status_code: number;
  duration_ms: number;
  request_body: unknown;
  response_body: unknown;
  truncated: boolean;
  error_message: string;
  username: string | null;
}

export interface McpPage<T> {
  total_count: number;
  count: number;
  offset: number;
  limit: number;
  has_more: boolean;
  next_offset: number | null;
  items: T[];
}

export interface McpAuditFilters {
  tool_name?: string;
  status_code?: string;
  session_id?: string;
  all?: boolean;
}

const csrfHeaders = () => ({
  'X-CSRFToken': getCsrfToken(),
  Accept: 'application/json',
});

export function stdioSnippet(origin: string, secret: string) {
  return JSON.stringify(
    {
      mcpServers: {
        r3ngine: {
          command: 'npx',
          args: ['-y', 'r3ngine-mcp'],
          env: { R3NGINE_URL: origin, R3NGINE_MCP_API_KEY: secret },
        },
      },
    },
    null,
    2,
  );
}

export function httpSnippet(origin: string, secret: string) {
  return `URL: ${origin}/mcp\nHeader: Authorization: Bearer ${secret}`;
}

export const useMcpSettings = () =>
  useQuery<McpSettings>({
    queryKey: ['mcp-settings'],
    queryFn: async () => {
      const { data } = await axios.get('/api/mcp/settings/', {
        headers: { Accept: 'application/json' },
      });
      return data;
    },
  });

export const useUpdateMcpSettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (transport_mode: McpTransportMode) => {
      const { data } = await axios.patch(
        '/api/mcp/settings/',
        { transport_mode },
        { headers: csrfHeaders() },
      );
      return data as McpSettings;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-settings'] });
    },
  });
};

export const useMcpKeys = () =>
  useQuery<{ items: McpKey[]; count: number }>({
    queryKey: ['mcp-keys'],
    queryFn: async () => {
      const { data } = await axios.get('/api/mcp/keys/', {
        headers: { Accept: 'application/json' },
      });
      return data;
    },
  });

export const useCreateMcpKey = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const { data } = await axios.post(
        '/api/mcp/keys/',
        { name },
        { headers: csrfHeaders() },
      );
      return data as McpKey;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-keys'] });
    },
  });
};

export const useRegenerateMcpKey = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (keyId: number) => {
      const { data } = await axios.post(
        `/api/mcp/keys/${keyId}/regenerate/`,
        {},
        { headers: csrfHeaders() },
      );
      return data as McpKey;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-keys'] });
      queryClient.invalidateQueries({ queryKey: ['mcp-sessions'] });
    },
  });
};

export const useRevokeMcpKey = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (keyId: number) => {
      const { data } = await axios.post(
        `/api/mcp/keys/${keyId}/revoke/`,
        {},
        { headers: csrfHeaders() },
      );
      return data as McpKey;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-keys'] });
      queryClient.invalidateQueries({ queryKey: ['mcp-sessions'] });
    },
  });
};

export const useMcpSessions = () =>
  useQuery<{ items: McpSession[]; count: number }>({
    queryKey: ['mcp-sessions'],
    queryFn: async () => {
      const { data } = await axios.get('/api/mcp/sessions/', {
        headers: { Accept: 'application/json' },
      });
      return data;
    },
    refetchInterval: 15000,
  });

export const useRevokeMcpSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (sessionId: string) => {
      const { data } = await axios.post(
        `/api/mcp/sessions/${sessionId}/revoke/`,
        {},
        { headers: csrfHeaders() },
      );
      return data as McpSession;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-sessions'] });
    },
  });
};

export const useMcpSessionEvents = (sessionId: string | null) =>
  useQuery<McpPage<McpAuditEvent>>({
    queryKey: ['mcp-session-events', sessionId],
    queryFn: async () => {
      const { data } = await axios.get(`/api/mcp/sessions/${sessionId}/events/`, {
        headers: { Accept: 'application/json' },
        params: { limit: 100, offset: 0 },
      });
      return data;
    },
    enabled: !!sessionId,
  });

export const useMcpAudit = (filters: McpAuditFilters) =>
  useQuery<McpPage<McpAuditEvent>>({
    queryKey: ['mcp-audit', filters],
    queryFn: async () => {
      const { data } = await axios.get('/api/mcp/audit/', {
        headers: { Accept: 'application/json' },
        params: {
          limit: 50,
          offset: 0,
          tool_name: filters.tool_name || undefined,
          status_code: filters.status_code || undefined,
          session_id: filters.session_id || undefined,
          all: filters.all ? '1' : undefined,
        },
      });
      return data;
    },
  });
