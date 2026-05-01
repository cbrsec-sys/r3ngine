import React from 'react';
import { Container, Box, Typography, CircularProgress, Alert } from '@mui/material';
import { useParams } from '@tanstack/react-router';
import { useMonitoringData } from './api';
import { MonitoringStats } from './components/MonitoringStats';
import { DiscoveryTable } from './components/DiscoveryTable';
import { Activity } from 'lucide-react';

export const MonitoringPage: React.FC = () => {
  const { projectSlug = 'default' } = useParams({ strict: false });
  const { stats, discoveries, isLoading, isError } = useMonitoringData(projectSlug);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress sx={{ color: 'primary.main' }} />
      </Box>
    );
  }

  if (isError) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ bgcolor: 'rgba(255, 0, 60, 0.1)', border: '1px solid #ff003c', color: '#ff003c' }}>
          Failed to fetch monitoring data.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ mb: 5 }}>
        <Typography variant="h4" sx={{ 
          fontWeight: 900, 
          fontFamily: 'Orbitron', 
          mb: 1, 
          letterSpacing: 3,
          textShadow: '0 0 25px rgba(0, 243, 255, 0.6), 0 0 10px rgba(0, 243, 255, 0.4)',
          color: '#fff',
          textTransform: 'uppercase'
        }}>
          CONTINUOUS_MONITORING_OPERATIONS
        </Typography>
        <Typography variant="body2" sx={{ color: 'rgba(0, 243, 255, 0.6)', display: 'flex', alignItems: 'center', gap: 1, fontWeight: 700, letterSpacing: 1 }}>
          <Activity size={14} />
          REAL-TIME ASSET DISCOVERY & CHANGE DETECTION
        </Typography>
      </Box>

      {stats && <MonitoringStats stats={stats} />}
      {discoveries && <DiscoveryTable discoveries={discoveries} projectSlug={projectSlug} />}
    </Container>
  );
};
