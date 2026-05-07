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
  IconButton, 
  Tooltip 
} from '@mui/material';
import { Mail, Key, Copy, Check } from 'lucide-react';
import { TacticalPanel } from '../../../../components/TacticalPanel';

interface Email {
  id: number;
  address: string;
  password?: string;
}

interface EmailSectionProps {
  emails: Email[];
}

export const EmailSection: React.FC<EmailSectionProps> = ({ emails }) => {
  const [copiedId, setCopiedId] = React.useState<string | null>(null);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (!emails || emails.length === 0) return null;

  return (
    <TacticalPanel title="EMAILS & CREDENTIALS" icon={<Mail size={18} />}>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ color: 'text.secondary', fontWeight: 'bold' }}>ADDRESS</TableCell>
              <TableCell sx={{ color: 'text.secondary', fontWeight: 'bold' }}>CREDENTIALS</TableCell>
              <TableCell align="right" sx={{ color: 'text.secondary', fontWeight: 'bold' }}>ACTIONS</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {emails.map((email) => (
              <TableRow key={email.id} hover>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {email.address}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  {email.password ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'error.main' }}>
                      <Key size={14} />
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {email.password}
                      </Typography>
                    </Box>
                  ) : (
                    <Typography variant="caption" sx={{ color: 'text.disabled', fontStyle: 'italic' }}>
                      No password found
                    </Typography>
                  )}
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                    <Tooltip title={copiedId === `addr-${email.id}` ? "Copied!" : "Copy Address"}>
                      <IconButton 
                        size="small" 
                        onClick={() => handleCopy(email.address, `addr-${email.id}`)}
                        sx={{ color: copiedId === `addr-${email.id}` ? 'success.main' : 'inherit' }}
                      >
                        {copiedId === `addr-${email.id}` ? <Check size={14} /> : <Copy size={14} />}
                      </IconButton>
                    </Tooltip>
                    {email.password && (
                      <Tooltip title={copiedId === `pass-${email.id}` ? "Copied!" : "Copy Password"}>
                        <IconButton 
                          size="small" 
                          onClick={() => handleCopy(email.password!, `pass-${email.id}`)}
                          sx={{ color: copiedId === `pass-${email.id}` ? 'success.main' : 'inherit' }}
                        >
                          {copiedId === `pass-${email.id}` ? <Check size={14} /> : <Copy size={14} />}
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </TacticalPanel>
  );
};
