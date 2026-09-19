import React, { useState } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Chip,
  Drawer,
  Typography,
} from '@mui/material';
import { ChevronDown } from 'lucide-react';
import { useMcpSessionEvents, type McpAuditEvent } from '../api/mcp';
import { useThemeTokens } from '../../../theme/useThemeTokens';
import { getHttpStatusColor, getSurfaceSx } from '../../../theme/semanticColors';

function JsonBlock({ value, tokens }: { value: unknown; tokens: ReturnType<typeof useThemeTokens>['tokens'] }) {
  return (
    <Box
      component="pre"
      sx={{
        m: 0,
        p: 1.5,
        fontSize: 12,
        overflow: 'auto',
        maxHeight: 240,
        color: tokens.text.primary,
        bgcolor: tokens.surface.elevated,
        border: `1px solid ${tokens.border.subtle}`,
        borderRadius: 1,
      }}
    >
      {JSON.stringify(value, null, 2)}
    </Box>
  );
}

export const McpAuditChainDrawer: React.FC<{
  sessionId: string | null;
  onClose: () => void;
}> = ({ sessionId, onClose }) => {
  const { tokens, isLight, theme } = useThemeTokens();
  const { data } = useMcpSessionEvents(sessionId);

  return (
    <Drawer
      anchor="right"
      open={!!sessionId}
      onClose={onClose}
      slotProps={{
        paper: {
          sx: {
            width: { xs: '100%', sm: 480 },
            px: 2,
            pb: 2,
            pt: 12,
            overflowY: 'auto',
            ...getSurfaceSx(isLight, tokens, theme),
          },
        },
      }}
    >
      <Typography variant="h6" sx={{ mb: 2 }}>
        Audit chain
      </Typography>
      {(data?.items || []).map((event: McpAuditEvent) => (
        <Accordion
          key={event.id}
          disableGutters
          sx={{
            mb: 1,
            bgcolor: 'transparent',
            border: `1px solid ${tokens.border.subtle}`,
            '&:before': { display: 'none' },
          }}
        >
          <AccordionSummary expandIcon={<ChevronDown size={16} />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                {event.created_at ? new Date(event.created_at).toLocaleString() : ''}
              </Typography>
              <Typography variant="body2">{event.tool_name || event.path}</Typography>
              <Chip
                size="small"
                label={event.status_code}
                sx={{
                  color: getHttpStatusColor(event.status_code, tokens),
                  borderColor: getHttpStatusColor(event.status_code, tokens),
                }}
                variant="outlined"
              />
              {event.truncated && <Chip size="small" label="truncated" />}
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="caption">Request</Typography>
            <JsonBlock value={event.request_body} tokens={tokens} />
            <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
              Response
            </Typography>
            <JsonBlock value={event.response_body} tokens={tokens} />
          </AccordionDetails>
        </Accordion>
      ))}
    </Drawer>
  );
};
