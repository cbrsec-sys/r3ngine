import React, { useState } from 'react';
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
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  CircularProgress,
  Divider,
} from '@mui/material';
import Chart from 'react-apexcharts';
import type { DashboardData } from '../api';

interface CWEInfo {
  name: string;
  description: string;
  impact: string;
  remediation: string;
  examples: string[];
  severity: string;
}

const CWE_COLORS = [
  '#7000ff', '#9020f0', '#b040ff', '#5500cc',
  '#c060ff', '#4400aa', '#d080ff', '#330088',
];

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
  const [cweDialogOpen, setCweDialogOpen] = useState(false);
  const [selectedCwe, setSelectedCwe] = useState<string | null>(null);
  const [cweInfo, setCweInfo] = useState<CWEInfo | null>(null);
  const [cweLoading, setCweLoading] = useState(false);
  const [cweError, setCweError] = useState<string | null>(null);

  const handleCweClick = async (cweName: string) => {
    setSelectedCwe(cweName);
    setCweInfo(null);
    setCweError(null);
    setCweLoading(true);
    setCweDialogOpen(true);

    try {
      const response = await fetch(`/api/cwe-info/?name=${encodeURIComponent(cweName)}`, {
        credentials: 'include',
      });
      const json = await response.json();
      if (json.status) {
        setCweInfo(json as CWEInfo);
      } else {
        setCweError(json.error || 'Failed to load CWE information.');
      }
    } catch {
      setCweError('Network error fetching CWE information.');
    } finally {
      setCweLoading(false);
    }
  };

  const donutOptions: any = {
    chart: { type: 'donut' as any, background: 'transparent' },
    theme: { mode: 'dark' as any },
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
    chart: { type: 'bar' as any, toolbar: { show: false }, background: 'transparent' },
    plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '60%' } },
    dataLabels: { enabled: false },
    xaxis: {
      categories,
      labels: { style: { colors: theme.palette.text.secondary, fontSize: '9px' } }
    },
    yaxis: { labels: { style: { colors: theme.palette.text.secondary, fontSize: '9px' } } },
    colors: [color],
    grid: { borderColor: 'rgba(255, 255, 255, 0.05)', strokeDashArray: 4 },
    theme: { mode: 'dark' as any }
  });

  return (
    <Box>
      {/* Row 1: High Level Risk & Most Vulnerable Targets */}
      <Grid container spacing={3} sx={{ mb: 3, alignItems: 'stretch' }}>
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
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 600, color: '#c7c7c7ff' }}>{target.name}</Typography>
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
      <Grid container spacing={3} sx={{ mb: 3, alignItems: 'stretch' }}>
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
            {data.most_common_cwe && data.most_common_cwe.length > 0 ? (
              <>
                <Chart
                  options={{
                    chart: {
                      type: 'treemap' as any,
                      toolbar: { show: false },
                      background: 'transparent',
                      events: {
                        dataPointSelection: (_e: any, _ctx: any, config: any) => {
                          const idx = config.dataPointIndex;
                          const cweItem = data.most_common_cwe.slice(0, 8)[idx];
                          if (cweItem) handleCweClick(cweItem.name);
                        },
                      },
                    },
                    dataLabels: {
                      enabled: true,
                      style: { fontSize: '10px', fontFamily: 'Inter, sans-serif', colors: ['#ffffffcc'] },
                      formatter: (text: string, op: any) => [text, `×${op.value}`],
                    },
                    plotOptions: {
                      treemap: {
                        distributed: true,
                        enableShades: true,
                        shadeIntensity: 0.3,
                        colorScale: {
                          ranges: [
                            { from: 0, to: 9999, color: '#7000ff' },
                          ],
                        },
                      },
                    },
                    colors: CWE_COLORS,
                    tooltip: {
                      theme: 'dark',
                      y: { formatter: (v: number) => `${v} occurrence${v !== 1 ? 's' : ''}` },
                    },
                    legend: { show: false },
                    theme: { mode: 'dark' as any },
                  }}
                  series={[{
                    data: data.most_common_cwe.slice(0, 8).map((c, i) => ({
                      x: c.name,
                      y: c.count,
                      fillColor: CWE_COLORS[i % CWE_COLORS.length],
                    })),
                  }]}
                  type="treemap"
                  height={170}
                />
                {/* Clickable legend */}
                <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {data.most_common_cwe.slice(0, 8).map((c, i) => (
                    <Chip
                      key={c.name}
                      label={`${c.name} (${c.count})`}
                      size="small"
                      onClick={() => handleCweClick(c.name)}
                      sx={{
                        height: 20,
                        fontSize: '0.6rem',
                        fontWeight: 700,
                        fontFamily: 'Inter',
                        cursor: 'pointer',
                        bgcolor: `${CWE_COLORS[i % CWE_COLORS.length]}18`,
                        color: CWE_COLORS[i % CWE_COLORS.length],
                        border: `1px solid ${CWE_COLORS[i % CWE_COLORS.length]}44`,
                        '&:hover': {
                          bgcolor: `${CWE_COLORS[i % CWE_COLORS.length]}35`,
                        },
                      }}
                    />
                  ))}
                </Box>
              </>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 210 }}>
                <Typography sx={{ color: 'rgba(255, 255, 255, 0.3)', fontSize: '0.8rem', fontFamily: 'Inter' }}>
                  No CWE Data Available
                </Typography>
              </Box>
            )}
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

      {/* CWE Detail Modal */}
      <Dialog
        open={cweDialogOpen}
        onClose={() => setCweDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        sx={{
          '& .MuiDialog-paper': {
            bgcolor: 'rgba(5, 5, 15, 0.97)',
            border: '1px solid rgba(112, 0, 255, 0.4)',
            backdropFilter: 'blur(20px)',
            borderRadius: 2,
          },
        }}
      >
        <DialogTitle sx={{ pb: 1 }}>
          <Typography variant="h6" sx={{ fontFamily: 'Orbitron', fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1.5, color: '#7000ff' }}>
            {selectedCwe}
          </Typography>
          {cweInfo && (
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontFamily: 'Inter', display: 'block', mt: 0.25 }}>
              {cweInfo.name}
            </Typography>
          )}
        </DialogTitle>

        <DialogContent sx={{ pt: 0 }}>
          {cweLoading && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 3 }}>
              <CircularProgress size={20} sx={{ color: '#7000ff' }} />
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', fontFamily: 'Inter', fontSize: '0.8rem' }}>
                Generating CWE intelligence...
              </Typography>
            </Box>
          )}

          {cweError && (
            <Typography variant="body2" sx={{ color: '#ff003c', fontFamily: 'Inter', fontSize: '0.8rem', py: 2 }}>
              {cweError}
            </Typography>
          )}

          {cweInfo && !cweLoading && (
            <Box>
              {cweInfo.severity && (
                <Box sx={{ mb: 2 }}>
                  <SeverityBadge severity={cweInfo.severity.toLowerCase()} label={cweInfo.severity.toUpperCase()} />
                </Box>
              )}

              <Typography variant="subtitle2" sx={{ fontFamily: 'Orbitron', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: '#7000ff', mb: 0.5 }}>
                Description
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'Inter', fontSize: '0.8rem', color: 'rgba(255,255,255,0.8)', lineHeight: 1.6, mb: 2 }}>
                {cweInfo.description}
              </Typography>

              <Divider sx={{ borderColor: 'rgba(112, 0, 255, 0.2)', mb: 2 }} />

              <Typography variant="subtitle2" sx={{ fontFamily: 'Orbitron', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: '#ff9f00', mb: 0.5 }}>
                Impact
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'Inter', fontSize: '0.8rem', color: 'rgba(255,255,255,0.8)', lineHeight: 1.6, mb: 2 }}>
                {cweInfo.impact}
              </Typography>

              <Divider sx={{ borderColor: 'rgba(112, 0, 255, 0.2)', mb: 2 }} />

              <Typography variant="subtitle2" sx={{ fontFamily: 'Orbitron', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: '#00ff62', mb: 0.5 }}>
                Remediation
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'Inter', fontSize: '0.8rem', color: 'rgba(255,255,255,0.8)', lineHeight: 1.6, mb: 2 }}>
                {cweInfo.remediation}
              </Typography>

              {cweInfo.examples && cweInfo.examples.length > 0 && (
                <>
                  <Divider sx={{ borderColor: 'rgba(112, 0, 255, 0.2)', mb: 2 }} />
                  <Typography variant="subtitle2" sx={{ fontFamily: 'Orbitron', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: '#00f3ff', mb: 1 }}>
                    Examples
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                    {cweInfo.examples.map((ex, i) => (
                      <Box key={i} sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                        <Box sx={{ width: 4, height: 4, borderRadius: '50%', bgcolor: '#00f3ff', mt: 0.8, flexShrink: 0 }} />
                        <Typography variant="body2" sx={{ fontFamily: 'Inter', fontSize: '0.78rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.5 }}>
                          {ex}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </>
              )}
            </Box>
          )}
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setCweDialogOpen(false)}
            size="small"
            sx={{
              fontFamily: 'Orbitron',
              fontSize: '0.65rem',
              fontWeight: 800,
              textTransform: 'uppercase',
              letterSpacing: 1,
              color: '#7000ff',
              border: '1px solid rgba(112, 0, 255, 0.4)',
              px: 2,
              '&:hover': { bgcolor: 'rgba(112, 0, 255, 0.1)' },
            }}
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
