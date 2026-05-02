import React from 'react';
import { Grid, Box, Container, Typography, CircularProgress, Alert } from '@mui/material';
import { useDashboardData } from './api';
import { KpiGrid } from './components/KPIs';
import { TrendCharts } from './components/TrendCharts';
import { DistributionCharts } from './components/DistributionCharts';
import { ActivityFeed } from './components/ActivityFeed';
import { VulnerabilityFeed } from './components/VulnerabilityFeed';
import { GeoMap } from './components/GeoMap';
import { useAppContext } from '../../context/AppContext';


import { useParams } from '@tanstack/react-router';

export const DashboardPage: React.FC = () => {
  const { setVersion, setProjectName } = useAppContext();
  const { projectSlug = 'default' } = useParams({ strict: false });
  const { data, isLoading, error } = useDashboardData(projectSlug);

  React.useEffect(() => {
    if (data) {
      setVersion(data.rengine_version);
      setProjectName(data.project_info.name.toUpperCase());
    }
  }, [data, setVersion, setProjectName]);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress sx={{ color: 'primary.main' }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ bgcolor: 'rgba(255, 0, 60, 0.1)', border: '1px solid #ff003c', color: '#ff003c' }}>
          Failed to fetch dashboard data. Please ensure you are logged into the reNgine backend.
        </Alert>
      </Container>
    );
  }

  if (!data) return null;

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
          {data.project_info.name.toUpperCase()} Dashboard
        </Typography>
        <Typography variant="body2" sx={{ color: 'rgba(0, 243, 255, 0.6)', display: 'flex', alignItems: 'center', gap: 1, fontWeight: 700, letterSpacing: 1 }}>
          <Box component="span" sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: 'primary.main', boxShadow: '0 0 10px #00f3ff' }} />
          REAL-TIME TACTICAL INTELLIGENCE FEED
        </Typography>
      </Box>


      <KpiGrid data={data.kpis} />

      <Grid container spacing={3} sx={{ mt: 3 }}>
        {/* Row 2: Activity & GeoMap */}
        <Grid size={{ xs: 12, md: 4 }}>
          <ActivityFeed data={data} />
        </Grid>
        <Grid size={{ xs: 12, md: 8 }}>
          <GeoMap data={data.asset_countries} />
        </Grid>

        {/* Row 3: Vulnerabilities & Trends (7 Day Horizon) */}
        <Grid size={{ xs: 12, md: 4 }}>
          <VulnerabilityFeed data={data.vulnerability_feed} />
        </Grid>
        <Grid size={{ xs: 12, md: 8 }}>
          <TrendCharts data={data.trends} />
        </Grid>

        {/* Row 4: Distribution Charts */}
        <Grid size={{ xs: 12 }}>
          <DistributionCharts data={data} />
        </Grid>
      </Grid>
    </Container>
  );
};
