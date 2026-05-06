import React from 'react';
import { Box, Grid, Typography, Alert } from '@mui/material';
import { Info } from 'lucide-react';
import { EmailSection } from './EmailSection';
import { EmployeeSection } from './EmployeeSection';
import { DorkSection } from './DorkSection';
import { DocumentSection } from './DocumentSection';

interface OsintTabProps {
  data: any;
}

export const OsintTab: React.FC<OsintTabProps> = ({ data }) => {
  const hasData = 
    (data.emails && data.emails.length > 0) || 
    (data.employees && data.employees.length > 0) || 
    (data.dorks && data.dorks.length > 0) || 
    (data.documents && data.documents.length > 0);

  if (!hasData) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center' }}>
        <Alert 
          severity="info" 
          icon={<Info size={20} />}
          sx={{ 
            background: 'rgba(2, 136, 209, 0.05)', 
            border: '1px solid rgba(2, 136, 209, 0.2)',
            color: 'info.light',
            borderRadius: 0,
            width: '100%',
            maxWidth: 600
          }}
        >
          No OSINT data discovered for this scan. This could be because the OSINT tasks were not included in the scan engine or no relevant information was found.
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, width: '100%', p: 1 }}>
      <Grid container spacing={3}>
        {data.emails && data.emails.length > 0 && (
          <Grid size={12}>
            <EmailSection emails={data.emails} />
          </Grid>
        )}
        
        {data.employees && data.employees.length > 0 && (
          <Grid size={12}>
            <EmployeeSection employees={data.employees} />
          </Grid>
        )}

        {data.dorks && data.dorks.length > 0 && (
          <Grid size={12}>
            <DorkSection dorks={data.dorks} />
          </Grid>
        )}

        {data.documents && data.documents.length > 0 && (
          <Grid size={12}>
            <DocumentSection documents={data.documents} />
          </Grid>
        )}
      </Grid>
    </Box>
  );
};
