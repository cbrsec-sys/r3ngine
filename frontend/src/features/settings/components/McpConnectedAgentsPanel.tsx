import React, { useState } from 'react';
import {
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import { Ban } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useMcpSessions, useRevokeMcpSession, type McpSession } from '../api/mcp';
import { McpAuditChainDrawer } from './McpAuditChainDrawer';
import { useThemeTokens } from '../../../theme/useThemeTokens';
import { getDialogPaperSx } from '../../../theme/semanticColors';
import { TacticalPanel } from '../../../components/TacticalPanel';

export const McpConnectedAgentsPanel: React.FC = () => {
  const { tokens, isLight, theme } = useThemeTokens();
  const { data } = useMcpSessions();
  const revokeSession = useRevokeMcpSession();
  const [auditId, setAuditId] = useState<string | null>(null);
  const [pending, setPending] = useState<McpSession | null>(null);

  const statusColor = (status: McpSession['status']) => {
    if (status === 'connected') return tokens.accent.success;
    if (status === 'idle') return tokens.accent.warning;
    if (status === 'revoked') return tokens.accent.error;
    return tokens.text.disabled;
  };

  return (
    <>
      <TacticalPanel title="Connected agents">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Agent</TableCell>
              <TableCell>Key</TableCell>
              <TableCell>Transport</TableCell>
              <TableCell>IP</TableCell>
              <TableCell>Connected</TableCell>
              <TableCell>Last seen</TableCell>
              <TableCell>Status</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {(data?.items || []).map((row) => (
              <TableRow
                key={row.session_id}
                hover
                sx={{ cursor: 'pointer' }}
                onClick={() => setAuditId(row.session_id)}
              >
                <TableCell>
                  {row.client_name || 'unknown'} {row.client_version}
                </TableCell>
                <TableCell sx={{ fontFamily: 'monospace' }}>{row.key_prefix}</TableCell>
                <TableCell>{row.transport}</TableCell>
                <TableCell>{row.source_ip || '—'}</TableCell>
                <TableCell>
                  {row.connected_at
                    ? formatDistanceToNow(new Date(row.connected_at), { addSuffix: true })
                    : '—'}
                </TableCell>
                <TableCell>
                  {row.last_seen_at
                    ? formatDistanceToNow(new Date(row.last_seen_at), { addSuffix: true })
                    : '—'}
                </TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={row.status}
                    sx={{ color: statusColor(row.status), borderColor: statusColor(row.status) }}
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>
                  <Tooltip title="Revoke session">
                    <span>
                      <IconButton
                        size="small"
                        disabled={!!row.revoked_at}
                        onClick={(event) => {
                          event.stopPropagation();
                          setPending(row);
                        }}
                      >
                        <Ban size={16} />
                      </IconButton>
                    </span>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {!data?.items?.length && (
          <Typography variant="body2" sx={{ color: theme.palette.text.secondary, p: 2 }}>
            No agent sessions yet.
          </Typography>
        )}
      </TacticalPanel>

      <Dialog
        open={!!pending}
        onClose={() => setPending(null)}
        slotProps={{ paper: { sx: getDialogPaperSx(isLight, theme, tokens) } }}
      >
        <DialogTitle>Revoke session?</DialogTitle>
        <DialogContent>
          The API key stays valid. The agent must open a new session.
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPending(null)}>Cancel</Button>
          <Button
            color="error"
            onClick={async () => {
              if (!pending) return;
              await revokeSession.mutateAsync(pending.session_id);
              setPending(null);
            }}
          >
            Revoke
          </Button>
        </DialogActions>
      </Dialog>

      <McpAuditChainDrawer sessionId={auditId} onClose={() => setAuditId(null)} />
    </>
  );
};
