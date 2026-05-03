import React from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Grid, 
  useTheme, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow,
  Chip
} from '@mui/material';
import Chart from 'react-apexcharts';
import type { DashboardData } from '../api';

const ChartCard: React.FC<{ title: string; children: React.ReactNode; height?: number | string }> = ({ title, children, height }) => (
  <Card sx={{ height: height || '100%', minHeight: 320, bgcolor: 'rgba(5, 5, 15, 0.6)', backdropFilter: 'blur(10px)', border: '1px solid rgba(0, 243, 255, 0.1)' }}>
    <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h6" sx={{ mb: 2, fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1.5, color: 'primary.main', fontFamily: 'Orbitron' }}>
        {title}
      </Typography>
      <Box sx={{ mt: 1, flexGrow: 1, overflow: 'hidden' }}>
        {children}
      </Box>
    </CardContent>
  </Card>
);

const SeverityBadge: React.FC<{ severity: number | string; label?: string }> = ({ severity, label }) => {
  const getSeverityInfo = (sev: number | string) => {
    const sevNum = typeof sev === 'string' ? parseInt(sev) : sev;
    if (sev === 'critical' || sevNum === 4) return { label: label || 'CRITICAL', color: '#ff003c' };
    if (sev === 'high' || sevNum === 3) return { label: label || 'HIGH', color: '#ff9f00' };
    if (sev === 'medium' || sevNum === 2) return { label: label || 'MEDIUM', color: '#fffc00' };
    if (sev === 'low' || sevNum === 1) return { label: label || 'LOW', color: '#00ff62' };
    if (sev === 'info' || sevNum === 0) return { label: label || 'INFO', color: '#00f3ff' };
    return { label: label || 'UNKNOWN', color: '#7000ff' };
  };

  const info = getSeverityInfo(severity);
  return (
    <Chip 
      label={info.label} 
      size="small" 
      sx={{ 
        height: 18, 
        fontSize: '0.6rem', 
        fontWeight: 900, 
        bgcolor: `${info.color}15`, 
        color: info.color,
        borderRadius: 0.5,
        fontFamily: 'Inter',
        border: `1px solid ${info.color}33`,
      }} 
    />
  );
};

export const DistributionCharts: React.FC<{ data: DashboardData }> = ({ data }) => {
  const theme = useTheme();

  const donutOptions: any = {
    chart: { type: 'donut', background: 'transparent' },
    theme: { mode: 'dark' },
    stroke: { show: true, width: 2, colors: ['#05050f'] },
    dataLabels: { enabled: false },
    legend: { position: 'bottom', labels: { colors: theme.palette.text.secondary }, fontSize: '10px' },
    plotOptions: {
      pie: {
        donut: {
          size: '70%',
          labels: {
            show: true,
            name: { show: true, color: theme.palette.text.primary, fontSize: '10px' },
            value: { show: true, color: theme.palette.text.secondary, fontSize: '12px' },
            total: { show: true, label: 'TOTAL', color: theme.palette.primary.main, fontSize: '10px' }
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
      labels: { style: { colors: theme.palette.text.secondary, fontSize: '9px' } }
    },
    yaxis: { labels: { style: { colors: theme.palette.text.secondary, fontSize: '9px' } } },
    colors: [color],
    grid: { borderColor: 'rgba(255, 255, 255, 0.05)', strokeDashArray: 4 },
    theme: { mode: 'dark' }
  });

  return (
    <Box>
      {/* Row 1: High Level Risk & Most Vulnerable Targets */}
      <Grid container spacing={3} sx={{ mb: 3 }} alignItems="stretch">
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
            <TableContainer sx={{ maxHeight: 300 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ bgcolor: 'rgba(10, 10, 20, 0.95)', color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem', fontWeight: 800, borderBottom: '1px solid rgba(0, 243, 255, 0.2)', textTransform: 'uppercase', letterSpacing: 1 }}>Target Name</TableCell>
                    <TableCell align="center" sx={{ bgcolor: 'rgba(10, 10, 20, 0.95)', color: '#ff003c', fontSize: '0.65rem', fontWeight: 800, borderBottom: '1px solid rgba(0, 243, 255, 0.2)', textTransform: 'uppercase' }}>Critical</TableCell>
                    <TableCell align="center" sx={{ bgcolor: 'rgba(10, 10, 20, 0.95)', color: '#ff9f00', fontSize: '0.65rem', fontWeight: 800, borderBottom: '1px solid rgba(0, 243, 255, 0.2)', textTransform: 'uppercase' }}>High</TableCell>
                    <TableCell align="center" sx={{ bgcolor: 'rgba(10, 10, 20, 0.95)', color: '#fffc00', fontSize: '0.65rem', fontWeight: 800, borderBottom: '1px solid rgba(0, 243, 255, 0.2)', textTransform: 'uppercase' }}>Med</TableCell>
                    <TableCell align="center" sx={{ bgcolor: 'rgba(10, 10, 20, 0.95)', color: '#00ff62', fontSize: '0.65rem', fontWeight: 800, borderBottom: '1px solid rgba(0, 243, 255, 0.2)', textTransform: 'uppercase' }}>Low</TableCell>
                    <TableCell align="center" sx={{ bgcolor: 'rgba(10, 10, 20, 0.95)', color: '#00f3ff', fontSize: '0.65rem', fontWeight: 800, borderBottom: '1px solid rgba(0, 243, 255, 0.2)', textTransform: 'uppercase' }}>Total</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.most_vulnerable_targets.map((target, index) => (
                    <TableRow key={index} sx={{ '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' } }}>
                      <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', py: 1 }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 600, color: 'primary.main' }}>{target.name}</Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 700, color: target.critical_count > 0 ? '#ff003c' : 'rgba(255,255,255,0.1)' }}>{target.critical_count}</Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 700, color: target.high_count > 0 ? '#ff9f00' : 'rgba(255,255,255,0.1)' }}>{target.high_count}</Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 700, color: target.medium_count > 0 ? '#fffc00' : 'rgba(255,255,255,0.1)' }}>{target.medium_count}</Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 700, color: target.low_count > 0 ? '#00ff62' : 'rgba(255,255,255,0.1)' }}>{target.low_count}</Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <Box sx={{ px: 1, py: 0.25, borderRadius: 0.5, bgcolor: 'rgba(0, 243, 255, 0.1)', display: 'inline-block' }}>
                          <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 800, color: '#00f3ff' }}>{target.vuln_count}</Typography>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </ChartCard>
        </Grid>
      </Grid>

      {/* Row 2: Technologies & Most Common Vulnerabilities */}
      <Grid container spacing={3} sx={{ mb: 3 }} alignItems="stretch">
        <Grid size={{ xs: 12, md: 4 }}>
          <ChartCard title="Most Used Technologies">
            <Chart 
              options={getBarOptions(data.most_used_tech.slice(0, 8).map(t => t.name))} 
              series={[{ name: 'Usage', data: data.most_used_tech.slice(0, 8).map(t => t.count) }]} 
              type="bar" 
              height={240} 
            />
          </ChartCard>
        </Grid>
        
        <Grid size={{ xs: 12, md: 8 }}>
          <ChartCard title="Most Common Vulnerabilities">
            <TableContainer sx={{ maxHeight: 300 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ bgcolor: 'rgba(10, 10, 20, 0.95)', color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem', fontWeight: 800, borderBottom: '1px solid rgba(0, 243, 255, 0.2)', textTransform: 'uppercase', letterSpacing: 1 }}>Vulnerability Name</TableCell>
                    <TableCell align="center" sx={{ bgcolor: 'rgba(10, 10, 20, 0.95)', color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem', fontWeight: 800, borderBottom: '1px solid rgba(0, 243, 255, 0.2)', textTransform: 'uppercase', letterSpacing: 1 }}>Severity</TableCell>
                    <TableCell align="center" sx={{ bgcolor: 'rgba(10, 10, 20, 0.95)', color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem', fontWeight: 800, borderBottom: '1px solid rgba(0, 243, 255, 0.2)', textTransform: 'uppercase', letterSpacing: 1 }}>Count</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.most_common_vulnerabilities.map((vuln, index) => (
                    <TableRow key={index} sx={{ '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' } }}>
                      <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', py: 1 }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 600, color: '#fff' }}>{vuln.name}</Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <SeverityBadge severity={vuln.severity} />
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 700, color: 'primary.main' }}>{vuln.count}</Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
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
                labels: data.most_used_port.slice(0, 5).map(p => `${p.number}/${p.service_name}`)
              }} 
              series={data.most_used_port.slice(0, 5).map(p => p.count)} 
              type="donut" 
              height={240} 
            />
          </ChartCard>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <ChartCard title="Most Common CWE">
            <Chart 
              options={getBarOptions(data.most_common_cwe.slice(0, 8).map(c => c.name), '#7000ff')} 
              series={[{ name: 'Occurrences', data: data.most_common_cwe.slice(0, 8).map(c => c.count) }]} 
              type="bar" 
              height={240} 
            />
          </ChartCard>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <ChartCard title="Top IP Addresses">
            <Chart 
              options={getBarOptions(data.most_used_ip.slice(0, 8).map(ip => ip.address || 'Unknown'), '#00ff62')} 
              series={[{ name: 'Usage', data: data.most_used_ip.slice(0, 8).map(ip => ip.count) }]} 
              type="bar" 
              height={240} 
            />
          </ChartCard>
        </Grid>
      </Grid>
    </Box>
  );
};
