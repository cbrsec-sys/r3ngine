import React from 'react';
import { Box, Card, CardContent, Typography, Grid, useTheme } from '@mui/material';
import Chart from 'react-apexcharts';
import type { DashboardData } from '../api';

const ChartCard: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <Card sx={{ height: '100%', minHeight: 320, bgcolor: 'rgba(5, 5, 15, 0.6)', backdropFilter: 'blur(10px)', border: '1px solid rgba(0, 243, 255, 0.1)' }}>
    <CardContent>
      <Typography variant="h6" sx={{ mb: 2, fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1.5, color: 'primary.main', fontFamily: 'Orbitron' }}>
        {title}
      </Typography>
      <Box sx={{ mt: 2 }}>
        {children}
      </Box>
    </CardContent>
  </Card>
);

export const DistributionCharts: React.FC<{ data: DashboardData }> = ({ data }) => {
  const theme = useTheme();

  const donutOptions: any = {
    chart: { type: 'donut', background: 'transparent' },
    theme: { mode: 'dark' },
    stroke: { show: true, width: 2, colors: ['#05050f'] },
    dataLabels: { enabled: false },
    legend: { position: 'bottom', labels: { colors: theme.palette.text.secondary } },
    plotOptions: {
      pie: {
        donut: {
          size: '70%',
          labels: {
            show: true,
            name: { show: true, color: theme.palette.text.primary, fontSize: '12px' },
            value: { show: true, color: theme.palette.text.secondary, fontSize: '14px' },
            total: { show: true, label: 'TOTAL', color: theme.palette.primary.main }
          }
        }
      }
    },
    colors: ['#00f3ff', '#7000ff', '#ff00f7', '#ff003c', '#00ff62', '#fffc00', '#ff9f00']
  };

  const getBarOptions = (categories: string[], color = '#00f3ff') => ({
    chart: { type: 'bar', toolbar: { show: false }, background: 'transparent' },
    plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '60%' } },
    dataLabels: { enabled: false },
    xaxis: { 
      categories,
      labels: { style: { colors: theme.palette.text.secondary, fontSize: '10px' } }
    },
    yaxis: { labels: { style: { colors: theme.palette.text.secondary, fontSize: '10px' } } },
    colors: [color],
    grid: { borderColor: 'rgba(255, 255, 255, 0.05)', strokeDashArray: 4 },
    theme: { mode: 'dark' }
  });

  return (
    <Box>
      {/* Row 1: High Level Risk */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 4 }}>

          <ChartCard title="Vulnerability Severity">
            <Chart 
              options={{
                ...donutOptions,
                labels: ['Critical', 'High', 'Medium', 'Low', 'Info', 'Unknown'],
                colors: ['#ff003c', '#ff9f00', '#fffc00', '#00ff62', '#00f3ff', '#7000ff']
              }} 
              series={[
                data.kpis.critical_count,
                data.kpis.high_count,
                data.kpis.medium_count,
                data.kpis.low_count,
                data.kpis.info_count,
                data.kpis.unknown_count
              ]} 
              type="donut" 
              height={300} 
            />
          </ChartCard>
        </Grid>
        
        <Grid size={{ xs: 12, md: 8 }}>

          <ChartCard title="Most Vulnerable Targets">
            <Chart 
              options={getBarOptions(data.most_vulnerable_targets.map(t => t.name), '#ff003c')} 
              series={[{ name: 'Vulnerabilities', data: data.most_vulnerable_targets.map(t => t.vuln_count) }]} 
              type="bar" 
              height={300} 
            />
          </ChartCard>
        </Grid>
      </Grid>

      {/* Row 2: Technologies & Weaknesses */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 4 }}>

          <ChartCard title="Most Used Technologies">
            <Chart 
              options={getBarOptions(data.most_used_tech.map(t => t.name))} 
              series={[{ name: 'Usage', data: data.most_used_tech.map(t => t.count) }]} 
              type="bar" 
              height={300} 
            />
          </ChartCard>
        </Grid>
        
        <Grid size={{ xs: 12, md: 4 }}>

          <ChartCard title="Most Common CWE">
            <Chart 
              options={getBarOptions(data.most_common_cwe.map(c => c.name), '#7000ff')} 
              series={[{ name: 'Occurrences', data: data.most_common_cwe.map(c => c.count) }]} 
              type="bar" 
              height={300} 
            />
          </ChartCard>
        </Grid>
        
        <Grid size={{ xs: 12, md: 4 }}>

          <ChartCard title="Most Common CVE">
            <Chart 
              options={getBarOptions(data.most_common_cve.map(c => c.name), '#ff00f7')} 
              series={[{ name: 'Occurrences', data: data.most_common_cve.map(c => c.count) }]} 
              type="bar" 
              height={300} 
            />
          </ChartCard>
        </Grid>
      </Grid>

      {/* Row 3: Infrastructure & Tags */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 4 }}>

          <ChartCard title="Open Ports Distribution">
            <Chart 
              options={{
                ...donutOptions,
                labels: data.most_used_port.map(p => `${p.number}/${p.service_name}`)
              }} 
              series={data.most_used_port.map(p => p.count)} 
              type="donut" 
              height={300} 
            />
          </ChartCard>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>

          <ChartCard title="Vulnerability Tags">
            <Chart 
              options={{
                ...donutOptions,
                labels: data.most_common_tags.map(t => t.name)
              }} 
              series={data.most_common_tags.map(t => t.count)} 
              type="donut" 
              height={300} 
            />
          </ChartCard>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>

          <ChartCard title="Top IP Addresses">
            <Chart 
              options={getBarOptions(data.most_used_ip.map(ip => ip.address || 'Unknown'), '#00ff62')} 
              series={[{ name: 'Usage', data: data.most_used_ip.map(ip => ip.count) }]} 
              type="bar" 
              height={300} 
            />
          </ChartCard>
        </Grid>
      </Grid>
    </Box>
  );
};
