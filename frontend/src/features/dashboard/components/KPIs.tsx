import React from 'react';
import { Box, Grid, Typography, Card, CardContent, useTheme } from '@mui/material';
import {
  Globe,
  Layers,
  Target,
  AlertTriangle,
  ShieldAlert,
  Key
} from 'lucide-react';
import type { DashboardData } from '../api';

interface KpiCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: string;
  subtitle?: string;
}

const KpiCard: React.FC<KpiCardProps> = ({ title, value, icon, color, subtitle }) => {
  return (
    <Card sx={{
      height: '100%',
      bgcolor: 'rgba(5, 5, 15, 0.4)',
      backdropFilter: 'blur(12px)',
      border: '1px solid rgba(255, 255, 255, 0.05)',
      position: 'relative',
      overflow: 'hidden',
      transition: 'transform 0.2s ease-in-out, border-color 0.2s',
      '&:hover': {
        transform: 'translateY(-4px)',
        borderColor: color,
        '& .kpi-icon-bg': { opacity: 0.15, transform: 'scale(1.1) rotate(-10deg)' }
      }
    }}>
      <CardContent sx={{ p: 3 }}>
        <Box
          className="kpi-icon-bg"
          sx={{
            position: 'absolute',
            right: -15,
            top: -15,
            opacity: 0.08,
            transition: 'all 0.3s ease',
            color: color
          }}
        >
          {React.cloneElement(icon as React.ReactElement<any>, { size: 100 })}
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2.5 }}>
          <Box sx={{
            p: 1.2,
            borderRadius: 2,
            bgcolor: `${color}15`,
            color: color,
            display: 'flex',
            mr: 1.5,
            border: `1px solid ${color}33`,
            boxShadow: `0 0 15px ${color}22`
          }}>
            {React.cloneElement(icon as React.ReactElement<any>, { size: 22 })}
          </Box>
          <Typography variant="overline" sx={{
            fontWeight: 800,
            letterSpacing: 2,
            color: 'text.secondary',
            fontFamily: 'Orbitron'
          }}>
            {title}
          </Typography>
        </Box>

        <Typography variant="h3" sx={{
          fontWeight: 900,
          mb: 0.5,
          fontFamily: 'Orbitron',
          letterSpacing: -1,
          color: '#fff'
        }}>
          {value.toLocaleString()}
        </Typography>

        {subtitle && (
          <Typography variant="caption" sx={{
            color: 'text.secondary',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            '&::before': {
              content: '""',
              width: 4,
              height: 4,
              borderRadius: '50%',
              bgcolor: color,
              mr: 1
            }
          }}>
            {subtitle.toUpperCase()}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export const KpiGrid: React.FC<{ data: DashboardData['kpis'] }> = ({ data }) => {
  return (
    <Grid container spacing={3}>
      <Grid size={{ xs: 12, sm: 6, lg: 2.4 }}>
        <KpiCard
          title="TARGETS"
          value={data.domain_count}
          icon={<Globe />}
          color="#00f3ff"
          subtitle="Registered Domains"
        />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, lg: 2.4 }}>
        <KpiCard
          title="SUBDOMAINS"
          value={data.subdomain_count}
          icon={<Layers />}
          color="#7000ff"
          subtitle={`${data.alive_count} Active Assets`}
        />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, lg: 2.4 }}>
        <KpiCard
          title="ENDPOINTS"
          value={data.endpoint_count}
          icon={<Target />}
          color="#ff00f7"
          subtitle={`${data.endpoint_alive_count} Total Alive`}
        />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, lg: 2.4 }}>
        <KpiCard
          title="VULNS"
          value={data.vulnerability_count}
          icon={<AlertTriangle />}
          color="#ff003c"
          subtitle={`${data.critical_count} Critical Risks`}
        />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, lg: 2.4 }}>
        <KpiCard
          title="LEAKS"
          value={data.secret_leak_count}
          icon={<Key />}
          color="#fffc00"
          subtitle="Sensitive Data Found"
        />
      </Grid>
    </Grid>
  );
};
