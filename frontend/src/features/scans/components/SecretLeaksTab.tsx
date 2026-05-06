import React from 'react';
import { 
  Box, 
  Typography, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Chip,
  CircularProgress,
  Stack,
  Tooltip,
  IconButton
} from '@mui/material';
import { Shield, ExternalLink, Copy, AlertTriangle } from 'lucide-react';
import { useSecretLeaks } from '../api';
import { TacticalPanel } from '../../../components/TacticalPanel';

interface SecretLeaksTabProps {
  projectSlug: string;
  scanId: number;
}

export const SecretLeaksTab: React.FC<SecretLeaksTabProps> = ({ projectSlug, scanId }) => {
  const { data: leaks, isLoading } = useSecretLeaks(projectSlug, scanId);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 8 }}>
        <CircularProgress sx={{ color: '#00f3ff' }} />
      </Box>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'verified': return '#00ff62';
      case 'unverified': return '#ff9f00';
      case 'false_positive': return '#ff003c';
      default: return '#fff';
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ mb: 4, mt: 2 }}>
        <Typography variant="h5" sx={{ 
          fontWeight: 900, 
          fontFamily: 'Orbitron', 
          letterSpacing: 3, 
          color: '#fff',
          textTransform: 'uppercase'
        }}>
          Leaks & Secrets
        </Typography>
        <Typography sx={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', mt: 0.5, letterSpacing: 1 }}>
          V3.0 CREDENTIAL INTELLIGENCE REPORT
        </Typography>
      </Box>

      <TacticalPanel title="SENSITIVE FINDINGS" icon={<Shield size={14} />}>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ '& th': { borderBottom: '2px solid #7000ff', bgcolor: 'rgba(255,255,255,0.02)', color: '#00f3ff', fontSize: '0.7rem', fontWeight: 900, py: 2 } }}>
                <th style={{ padding: '12px 16px', textAlign: 'left', color: '#00f3ff', fontSize: '10px', fontWeight: 900, fontFamily: 'Orbitron' }}>TOOL</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', color: '#00f3ff', fontSize: '10px', fontWeight: 900, fontFamily: 'Orbitron' }}>TYPE</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', color: '#00f3ff', fontSize: '10px', fontWeight: 900, fontFamily: 'Orbitron' }}>SOURCE</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', color: '#00f3ff', fontSize: '10px', fontWeight: 900, fontFamily: 'Orbitron' }}>MATCH CONTENT</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', color: '#00f3ff', fontSize: '10px', fontWeight: 900, fontFamily: 'Orbitron' }}>STATUS</th>
              </TableRow>
            </TableHead>
            <TableBody>
              {leaks?.map((leak: any) => (
                <TableRow key={leak.id} sx={{ '& td': { borderBottom: '1px solid rgba(255,255,255,0.05)', py: 2 } }}>
                  <TableCell>
                    <Chip 
                      label={leak.tool_name} 
                      size="small" 
                      sx={{ 
                        bgcolor: 'rgba(112,0,255,0.1)', 
                        color: '#7000ff', 
                        fontWeight: 800, 
                        fontSize: '0.65rem',
                        border: '1px solid rgba(112,0,255,0.2)'
                      }} 
                    />
                  </TableCell>
                  <TableCell>
                    <Typography sx={{ fontSize: '0.75rem', fontWeight: 700, color: '#fff' }}>
                      {leak.secret_type}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" sx={{ alignItems: 'center' }} spacing={1}>
                      <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {leak.source_url}
                      </Typography>
                      <IconButton size="small" component="a" href={leak.source_url} target="_blank" sx={{ color: '#00f3ff', p: 0.5 }}>
                        <ExternalLink size={12} />
                      </IconButton>
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ 
                      p: 1, 
                      bgcolor: 'rgba(0,0,0,0.3)', 
                      border: '1px solid rgba(255,255,255,0.05)', 
                      borderRadius: 0.5,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      maxWidth: '300px'
                    }}>
                      <Typography sx={{ 
                        fontSize: '0.7rem', 
                        fontFamily: 'monospace', 
                        color: '#00ff62',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}>
                        {leak.match_content}
                      </Typography>
                      <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.3)', p: 0.2 }}>
                        <Copy size={12} />
                      </IconButton>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ 
                      display: 'inline-flex',
                      px: 1,
                      py: 0.2,
                      borderRadius: 0.5,
                      bgcolor: `${getStatusColor(leak.status)}10`,
                      border: `1px solid ${getStatusColor(leak.status)}30`,
                      color: getStatusColor(leak.status),
                      fontSize: '0.65rem',
                      fontWeight: 900,
                      textTransform: 'uppercase'
                    }}>
                      {leak.status}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
              {(!leaks || leaks.length === 0) && (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 8 }}>
                    <Box sx={{ opacity: 0.3 }}>
                      <AlertTriangle size={32} style={{ marginBottom: '8px' }} />
                      <Typography sx={{ fontSize: '0.8rem', fontWeight: 700 }}>NO SECRETS OR LEAKS DETECTED</Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </TacticalPanel>
    </Box>
  );
};
