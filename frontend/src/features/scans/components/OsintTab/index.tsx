import React from 'react';
import { Box, Grid, Typography, Alert } from '@mui/material';
import { Info } from 'lucide-react';
import { EmailSection } from './EmailSection';

import { EmployeeSection } from './EmployeeSection';
import { DorkSection } from './DorkSection';
import { DocumentSection } from './DocumentSection';
import { OsintStagingSection } from './OsintStagingSection';

interface OsintTabProps {
  data: any;
  scanId: number;
}

export const OsintTab: React.FC<OsintTabProps> = ({ data, scanId }) => {
  const hasData = 
    (data.emails && data.emails.length > 0) || 
    (data.employees && data.employees.length > 0) || 
    (data.dorks && data.dorks.length > 0) || 
    (data.documents && data.documents.length > 0);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, width: '100%', p: 1 }}>
      {/* Staging Section Always Visible if Scan is for OSINT or has data */}
      <Grid container spacing={3}>
        <Grid size={12}>
          <OsintStagingSection scanId={scanId} />
        </Grid>

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

      {!hasData && (
        <Box sx={{ mt: 1 }}>
          <Alert 
            severity="info" 
            icon={<Info size={20} />}
            sx={{ 
              background: 'rgba(2, 136, 209, 0.05)', 
              border: '1px solid rgba(2, 136, 209, 0.2)',
              color: 'info.light',
              borderRadius: 0,
            }}
          >
            No high-confidence OSINT data discovered for this scan. You may still find results in the Staging area above that require manual validation.
          </Alert>
        </Box>
      )}
    </Box>
  );
};
