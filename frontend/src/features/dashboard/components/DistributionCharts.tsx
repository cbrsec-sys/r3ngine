import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  useTheme,
  alpha,
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
  IconButton,
  Tooltip,
} from '@mui/material';
import Chart from 'react-apexcharts';
import type { DashboardData } from '../api';
import { themeTokens } from '../../../theme/tokens';

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

const ChartCard: React.FC<{ title: React.ReactNode; children: React.ReactNode; height?: number | string }> = ({ title, children, height }) => {
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';

  return (
    <Card sx={{
      height: height || '100%',
      minHeight: 320,
      bgcolor: isLight ? theme.palette.background.paper : 'rgba(5, 5, 15, 0.6)',
      backdropFilter: isLight ? 'none' : 'blur(10px)',
      border: isLight ? `1px solid ${theme.palette.divider}` : '1px solid rgba(0, 243, 255, 0.1)',
      boxShadow: isLight ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
    }}>
      <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {typeof title === 'string' ? (
          <Typography variant="h6" sx={{
            mb: 2,
            fontSize: '0.85rem',
            fontWeight: 800,
            textTransform: 'uppercase',
            letterSpacing: 1.5,
            color: 'primary.main',
            fontFamily: 'var(--r3-heading-font)'
          }}>
            {title}
          </Typography>
        ) : (
          <Box sx={{ mb: 2 }}>{title}</Box>
        )}
        <Box sx={{ mt: 1, flexGrow: 1, overflow: 'hidden' }}>
          {children}
        </Box>
      </CardContent>
    </Card>
  );
};

const SeverityBadge: React.FC<{ severity: number | string; label?: string }> = ({ severity, label }) => {
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';
  const es = themeTokens.enterprise.severity;

  const getSeverityInfo = (sev: number | string) => {
    const sevNum = typeof sev === 'string' ? parseInt(sev) : sev;
    if (sev === 'critical' || sevNum === 4) return { label: label || 'CRITICAL', color: isLight ? es.critical : '#ff003c' };
    if (sev === 'high'     || sevNum === 3) return { label: label || 'HIGH',     color: isLight ? es.high     : '#ff9f00' };
    if (sev === 'medium'   || sevNum === 2) return { label: label || 'MEDIUM',   color: isLight ? es.medium   : '#fffc00' };
    if (sev === 'low'      || sevNum === 1) return { label: label || 'LOW',      color: isLight ? es.low      : '#00ff62' };
    if (sev === 'info'     || sevNum === 0) return { label: label || 'INFO',     color: isLight ? es.info     : '#00f3ff' };
    return { label: label || 'UNKNOWN', color: isLight ? es.unknown : '#7000ff' };
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
  const isLight = theme.palette.mode === 'light';
  const ec = themeTokens.enterprise.charts;
  const donutChartColors = isLight ? ec.donut : ['#00f3ff', '#7000ff', '#ff00f7', '#ff003c', '#00ff62', '#fffc00', '#ff9f00'];
  const treemapColors = isLight ? ec.treemap : CWE_COLORS;
  const chartMode = isLight ? 'light' : 'dark';

  const [viewMode, setViewMode] = useState<'cve' | 'cwe'>('cve');

  // CWE dialog state
  const [cweDialogOpen, setCweDialogOpen] = useState(false);
  const [selectedCwe, setSelectedCwe] = useState<string | null>(null);
  const [cweInfo, setCweInfo] = useState<CWEInfo | null>(null);
  const [cweLoading, setCweLoading] = useState(false);
  const [cweError, setCweError] = useState<string | null>(null);

  // CVE dialog state
  const [cveDialogOpen, setCveDialogOpen] = useState(false);
  const [selectedCve, setSelectedCve] = useState<string | null>(null);
  const [cveInfo, setCveInfo] = useState<any | null>(null);
  const [cveLoading, setCveLoading] = useState(false);
  const [cveError, setCveError] = useState<string | null>(null);
  const [descGenerating, setDescGenerating] = useState(false);
  const [descGenError, setDescGenError] = useState<string | null>(null);

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

  const handleCveClick = async (cveName: string) => {
    setSelectedCve(cveName);
    setCveInfo(null);
    setCveError(null);
    setCveLoading(true);
    setCveDialogOpen(true);

    try {
      const response = await fetch(`/api/tools/cve_details/?cve_id=${encodeURIComponent(cveName)}`, {
        credentials: 'include',
      });
      const json = await response.json();
      if (json.status) {
        setCveInfo(json.result);
      } else {
        setCveError(json.message || 'Failed to load CVE information.');
      }
    } catch {
      setCveError('Network error fetching CVE information.');
    } finally {
      setCveLoading(false);
    }
  };

  const handleGenerateCveDescription = async () => {
    if (!selectedCve) return;
    setDescGenerating(true);
    setDescGenError(null);
    const csrfToken = document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1] || '';
    try {
      const response = await fetch('/api/tools/cve_description_generate/', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ cve_id: selectedCve }),
      });
      const json = await response.json();
      if (json.status) {
        setCveInfo((prev: any) => ({
          ...prev,
          summary: json.description || prev?.summary,
          ai_risk_assessment: json.ai_risk_assessment,
        }));
      } else {
        setDescGenError(json.message || 'Failed to generate description.');
      }
    } catch {
      setDescGenError('Network error generating description.');
    } finally {
      setDescGenerating(false);
    }
  };

  const donutOptions: any = {
    chart: { type: 'donut' as any, background: 'transparent' },
    theme: { mode: chartMode as any },
    stroke: { show: true, width: 2, colors: isLight ? ['#f8fafc'] : ['#05050f'] },
    dataLabels: { enabled: false },
    legend: {
      position: 'bottom',
      labels: { colors: theme.palette.text.secondary },
      fontSize: '10px'
    },
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
    colors: donutChartColors,
  };

  const getBarOptions = (categories: string[], color?: string) => {
    const barColor = color ?? (isLight ? ec.bar : '#00f3ff');
    return {
      chart: { type: 'bar' as any, toolbar: { show: false }, background: 'transparent' },
      plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '60%' } },
      dataLabels: { enabled: false },
      xaxis: {
        categories,
        labels: { style: { colors: theme.palette.text.secondary, fontSize: '9px' } }
      },
      yaxis: { labels: { style: { colors: theme.palette.text.secondary, fontSize: '9px' } } },
      colors: [barColor],
      grid: {
        borderColor: isLight ? theme.palette.divider : 'rgba(255, 255, 255, 0.05)',
        strokeDashArray: 4
      },
      theme: { mode: chartMode as any }
    };
  };

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
                colors: isLight
                  ? [ec.donut[0], ec.donut[1], ec.donut[2], ec.donut[3], ec.donut[4], ec.donut[5]]
                  : ['#ff003c', '#ff9f00', '#fffc00', '#00ff62', '#00f3ff', '#7000ff']
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
                    <TableCell sx={{ bgcolor: isLight ? alpha(theme.palette.primary.main, 0.05) : 'rgba(10, 10, 20, 0.95)', color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.5)', fontSize: '0.65rem', fontWeight: 800, borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(0, 243, 255, 0.2)'}`, textTransform: 'uppercase', letterSpacing: 1 }}>Target Name</TableCell>
                    <TableCell align="center" sx={{ bgcolor: isLight ? alpha(theme.palette.primary.main, 0.05) : 'rgba(10, 10, 20, 0.95)', color: isLight ? themeTokens.enterprise.severity.critical : '#ff003c', fontSize: '0.65rem', fontWeight: 800, borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(0, 243, 255, 0.2)'}`, textTransform: 'uppercase' }}>Critical</TableCell>
                    <TableCell align="center" sx={{ bgcolor: isLight ? alpha(theme.palette.primary.main, 0.05) : 'rgba(10, 10, 20, 0.95)', color: isLight ? themeTokens.enterprise.severity.high : '#ff9f00', fontSize: '0.65rem', fontWeight: 800, borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(0, 243, 255, 0.2)'}`, textTransform: 'uppercase' }}>High</TableCell>
                    <TableCell align="center" sx={{ bgcolor: isLight ? alpha(theme.palette.primary.main, 0.05) : 'rgba(10, 10, 20, 0.95)', color: isLight ? themeTokens.enterprise.severity.medium : '#fffc00', fontSize: '0.65rem', fontWeight: 800, borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(0, 243, 255, 0.2)'}`, textTransform: 'uppercase' }}>Med</TableCell>
                    <TableCell align="center" sx={{ bgcolor: isLight ? alpha(theme.palette.primary.main, 0.05) : 'rgba(10, 10, 20, 0.95)', color: isLight ? themeTokens.enterprise.severity.low : '#00ff62', fontSize: '0.65rem', fontWeight: 800, borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(0, 243, 255, 0.2)'}`, textTransform: 'uppercase' }}>Low</TableCell>
                    <TableCell align="center" sx={{ bgcolor: isLight ? alpha(theme.palette.primary.main, 0.05) : 'rgba(10, 10, 20, 0.95)', color: 'primary.main', fontSize: '0.65rem', fontWeight: 800, borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(0, 243, 255, 0.2)'}`, textTransform: 'uppercase' }}>Total</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.most_vulnerable_targets.map((target, index) => (
                    <TableRow key={index} sx={{ '&:hover': { bgcolor: isLight ? alpha(theme.palette.primary.main, 0.04) : 'rgba(255,255,255,0.02)' } }}>
                      <TableCell sx={{ borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255,255,255,0.05)'}`, py: 1 }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 600, color: isLight ? theme.palette.text.primary : '#c7c7c7ff' }}>{target.name}</Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255,255,255,0.05)'}` }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 700, color: target.critical_count > 0 ? '#ff003c' : isLight ? theme.palette.text.disabled : 'rgba(255,255,255,0.1)' }}>{target.critical_count}</Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255,255,255,0.05)'}` }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 700, color: target.high_count > 0 ? '#ff9f00' : isLight ? theme.palette.text.disabled : 'rgba(255,255,255,0.1)' }}>{target.high_count}</Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255,255,255,0.05)'}` }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 700, color: target.medium_count > 0 ? '#fffc00' : isLight ? theme.palette.text.disabled : 'rgba(255,255,255,0.1)' }}>{target.medium_count}</Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255,255,255,0.05)'}` }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 700, color: target.low_count > 0 ? '#00ff62' : isLight ? theme.palette.text.disabled : 'rgba(255,255,255,0.1)' }}>{target.low_count}</Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255,255,255,0.05)'}` }}>
                        <Box sx={{ px: 1, py: 0.25, borderRadius: 0.5, bgcolor: alpha(theme.palette.primary.main, 0.1), display: 'inline-block' }}>
                          <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 800, color: 'primary.main' }}>{target.vuln_count}</Typography>
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
                    <TableCell sx={{ bgcolor: isLight ? alpha(theme.palette.primary.main, 0.05) : 'rgba(10, 10, 20, 0.95)', color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.5)', fontSize: '0.65rem', fontWeight: 800, borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(0, 243, 255, 0.2)'}`, textTransform: 'uppercase', letterSpacing: 1 }}>Vulnerability Name</TableCell>
                    <TableCell align="center" sx={{ bgcolor: isLight ? alpha(theme.palette.primary.main, 0.05) : 'rgba(10, 10, 20, 0.95)', color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.5)', fontSize: '0.65rem', fontWeight: 800, borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(0, 243, 255, 0.2)'}`, textTransform: 'uppercase', letterSpacing: 1 }}>Severity</TableCell>
                    <TableCell align="center" sx={{ bgcolor: isLight ? alpha(theme.palette.primary.main, 0.05) : 'rgba(10, 10, 20, 0.95)', color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.5)', fontSize: '0.65rem', fontWeight: 800, borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(0, 243, 255, 0.2)'}`, textTransform: 'uppercase', letterSpacing: 1 }}>Count</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.most_common_vulnerabilities.map((vuln, index) => (
                    <TableRow key={index} sx={{ '&:hover': { bgcolor: isLight ? alpha(theme.palette.primary.main, 0.04) : 'rgba(255,255,255,0.02)' } }}>
                      <TableCell sx={{ borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255,255,255,0.05)'}`, py: 1 }}>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 600, color: isLight ? theme.palette.text.primary : '#fff' }}>{vuln.name}</Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255,255,255,0.05)'}` }}>
                        <SeverityBadge severity={vuln.severity} />
                      </TableCell>
                      <TableCell align="center" sx={{ borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255,255,255,0.05)'}` }}>
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
          <ChartCard
            title={
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                <Typography variant="h6" sx={{ fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1.5, color: 'primary.main', fontFamily: 'var(--r3-heading-font)' }}>
                  {viewMode === 'cwe' ? 'Most Common CWE' : 'Most Common CVE'}
                </Typography>
                <Box sx={{
                  display: 'flex',
                  bgcolor: isLight ? alpha(theme.palette.primary.main, 0.08) : 'rgba(112, 0, 255, 0.08)',
                  borderRadius: 1,
                  p: 0.25,
                  border: `1px solid ${isLight ? alpha(theme.palette.primary.main, 0.2) : 'rgba(112, 0, 255, 0.2)'}`,
                }}>
                  <Button
                    size="small"
                    onClick={() => setViewMode('cve')}
                    sx={{
                      minWidth: 50,
                      height: 22,
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      fontFamily: 'var(--r3-heading-font)',
                      borderRadius: 0.5,
                      color: viewMode === 'cve' ? theme.palette.primary.main : theme.palette.text.secondary,
                      bgcolor: viewMode === 'cve' ? alpha(theme.palette.primary.main, 0.15) : 'transparent',
                      boxShadow: viewMode === 'cve' && !isLight ? '0 0 8px rgba(0, 243, 255, 0.2)' : 'none',
                      p: 0,
                      '&:hover': {
                        bgcolor: viewMode === 'cve' ? alpha(theme.palette.primary.main, 0.25) : alpha(theme.palette.divider, 0.5),
                      }
                    }}
                  >
                    CVE
                  </Button>
                  <Button
                    size="small"
                    onClick={() => setViewMode('cwe')}
                    sx={{
                      minWidth: 50,
                      height: 22,
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      fontFamily: 'var(--r3-heading-font)',
                      borderRadius: 0.5,
                      color: viewMode === 'cwe' ? theme.palette.primary.main : theme.palette.text.secondary,
                      bgcolor: viewMode === 'cwe' ? alpha(theme.palette.primary.main, 0.15) : 'transparent',
                      boxShadow: viewMode === 'cwe' && !isLight ? '0 0 8px rgba(0, 243, 255, 0.2)' : 'none',
                      p: 0,
                      '&:hover': {
                        bgcolor: viewMode === 'cwe' ? alpha(theme.palette.primary.main, 0.25) : alpha(theme.palette.divider, 0.5),
                      }
                    }}
                  >
                    CWE
                  </Button>
                </Box>
              </Box>
            }
          >
            {viewMode === 'cwe' ? (
              data.most_common_cwe && data.most_common_cwe.length > 0 ? (
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
                              { from: 0, to: 9999, color: isLight ? '#0284c7' : '#7000ff' },
                            ],
                          },
                        },
                      },
                      colors: treemapColors,
                      tooltip: {
                        theme: chartMode,
                        y: { formatter: (v: number) => `${v} occurrence${v !== 1 ? 's' : ''}` },
                      },
                      legend: { show: false },
                      theme: { mode: chartMode as any },
                    }}
                    series={[{
                      data: data.most_common_cwe.slice(0, 8).map((c, i) => ({
                        x: c.name,
                        y: c.count,
                        fillColor: treemapColors[i % treemapColors.length],
                      })),
                    }]}
                    type="treemap"
                    height={170}
                  />
                  {/* Clickable legend */}
                  <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {data.most_common_cwe.slice(0, 8).map((c, i) => {
                      const chipColor = treemapColors[i % treemapColors.length];
                      return (
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
                            bgcolor: `${chipColor}18`,
                            color: chipColor,
                            border: `1px solid ${chipColor}44`,
                            '&:hover': {
                              bgcolor: `${chipColor}35`,
                            },
                          }}
                        />
                      );
                    })}
                  </Box>
                </>
              ) : (
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 210 }}>
                  <Typography sx={{ color: isLight ? theme.palette.text.disabled : 'rgba(255, 255, 255, 0.3)', fontSize: '0.8rem', fontFamily: 'Inter' }}>
                    No CWE Data Available
                  </Typography>
                </Box>
              )
            ) : (
              data.most_common_cve && data.most_common_cve.length > 0 ? (
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
                            const cveItem = data.most_common_cve.slice(0, 8)[idx];
                            if (cveItem) handleCveClick(cveItem.name);
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
                              { from: 0, to: 9999, color: isLight ? '#0284c7' : '#7000ff' },
                            ],
                          },
                        },
                      },
                      colors: treemapColors,
                      tooltip: {
                        theme: chartMode,
                        y: { formatter: (v: number) => `${v} occurrence${v !== 1 ? 's' : ''}` },
                      },
                      legend: { show: false },
                      theme: { mode: chartMode as any },
                    }}
                    series={[{
                      data: data.most_common_cve.slice(0, 8).map((c, i) => ({
                        x: c.name,
                        y: c.count,
                        fillColor: treemapColors[i % treemapColors.length],
                      })),
                    }]}
                    type="treemap"
                    height={170}
                  />
                  {/* Clickable legend */}
                  <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {data.most_common_cve.slice(0, 8).map((c, i) => {
                      const chipColor = treemapColors[i % treemapColors.length];
                      return (
                        <Chip
                          key={c.name}
                          label={`${c.name} (${c.count})`}
                          size="small"
                          onClick={() => handleCveClick(c.name)}
                          sx={{
                            height: 20,
                            fontSize: '0.6rem',
                            fontWeight: 700,
                            fontFamily: 'Inter',
                            cursor: 'pointer',
                            bgcolor: `${chipColor}18`,
                            color: chipColor,
                            border: `1px solid ${chipColor}44`,
                            '&:hover': {
                              bgcolor: `${chipColor}35`,
                            },
                          }}
                        />
                      );
                    })}
                  </Box>
                </>
              ) : (
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 210 }}>
                  <Typography sx={{ color: isLight ? theme.palette.text.disabled : 'rgba(255, 255, 255, 0.3)', fontSize: '0.8rem', fontFamily: 'Inter' }}>
                    No CVE Data Available
                  </Typography>
                </Box>
              )
            )}
          </ChartCard>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <ChartCard title="Top IP Addresses">
            <Chart
              options={getBarOptions(data.most_used_ip.slice(0, 8).map(ip => ip.address || 'Unknown'), isLight ? '#16a34a' : '#00ff62')}
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
            bgcolor: isLight ? theme.palette.background.paper : 'rgba(5, 5, 15, 0.97)',
            border: isLight ? `1px solid ${theme.palette.divider}` : '1px solid rgba(112, 0, 255, 0.4)',
            backdropFilter: isLight ? 'none' : 'blur(20px)',
            borderRadius: 2,
          },
        }}
      >
        <DialogTitle sx={{ pb: 1 }}>
          <Typography variant="h6" sx={{ fontFamily: 'var(--r3-heading-font)', fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1.5, color: isLight ? themeTokens.enterprise.severity.unknown : '#7000ff' }}>
            {selectedCwe}
          </Typography>
          {cweInfo && (
            <Typography variant="caption" sx={{ color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.5)', fontFamily: 'Inter', display: 'block', mt: 0.25 }}>
              {cweInfo.name}
            </Typography>
          )}
        </DialogTitle>

        <DialogContent sx={{ pt: 0 }}>
          {cweLoading && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 3 }}>
              <CircularProgress size={20} sx={{ color: isLight ? themeTokens.enterprise.severity.unknown : '#7000ff' }} />
              <Typography variant="body2" sx={{ color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.5)', fontFamily: 'Inter', fontSize: '0.8rem' }}>
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

              <Typography variant="subtitle2" sx={{ fontFamily: 'var(--r3-heading-font)', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: isLight ? themeTokens.enterprise.severity.unknown : '#7000ff', mb: 0.5 }}>
                Description
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'Inter', fontSize: '0.8rem', color: isLight ? theme.palette.text.primary : 'rgba(255,255,255,0.8)', lineHeight: 1.6, mb: 2 }}>
                {cweInfo.description}
              </Typography>

              <Divider sx={{ borderColor: isLight ? theme.palette.divider : 'rgba(112, 0, 255, 0.2)', mb: 2 }} />

              <Typography variant="subtitle2" sx={{ fontFamily: 'var(--r3-heading-font)', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: isLight ? themeTokens.enterprise.severity.high : '#ff9f00', mb: 0.5 }}>
                Impact
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'Inter', fontSize: '0.8rem', color: isLight ? theme.palette.text.primary : 'rgba(255,255,255,0.8)', lineHeight: 1.6, mb: 2 }}>
                {cweInfo.impact}
              </Typography>

              <Divider sx={{ borderColor: isLight ? theme.palette.divider : 'rgba(112, 0, 255, 0.2)', mb: 2 }} />

              <Typography variant="subtitle2" sx={{ fontFamily: 'var(--r3-heading-font)', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: isLight ? themeTokens.enterprise.severity.low : '#00ff62', mb: 0.5 }}>
                Remediation
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'Inter', fontSize: '0.8rem', color: isLight ? theme.palette.text.primary : 'rgba(255,255,255,0.8)', lineHeight: 1.6, mb: 2 }}>
                {cweInfo.remediation}
              </Typography>

              {cweInfo.examples && cweInfo.examples.length > 0 && (
                <>
                  <Divider sx={{ borderColor: isLight ? theme.palette.divider : 'rgba(112, 0, 255, 0.2)', mb: 2 }} />
                  <Typography variant="subtitle2" sx={{ fontFamily: 'var(--r3-heading-font)', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: isLight ? themeTokens.enterprise.severity.info : '#00f3ff', mb: 1 }}>
                    Examples
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                    {cweInfo.examples.map((ex, i) => (
                      <Box key={i} sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                        <Box sx={{ width: 4, height: 4, borderRadius: '50%', bgcolor: isLight ? themeTokens.enterprise.severity.info : '#00f3ff', mt: 0.8, flexShrink: 0 }} />
                        <Typography variant="body2" sx={{ fontFamily: 'Inter', fontSize: '0.78rem', color: isLight ? theme.palette.text.primary : 'rgba(255,255,255,0.7)', lineHeight: 1.5 }}>
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
              fontFamily: 'var(--r3-heading-font)',
              fontSize: '0.65rem',
              fontWeight: 800,
              textTransform: 'uppercase',
              letterSpacing: 1,
              color: isLight ? themeTokens.enterprise.severity.unknown : '#7000ff',
              border: `1px solid ${isLight ? alpha(themeTokens.enterprise.severity.unknown, 0.4) : 'rgba(112, 0, 255, 0.4)'}`,
              px: 2,
              '&:hover': { bgcolor: isLight ? alpha(themeTokens.enterprise.severity.unknown, 0.1) : 'rgba(112, 0, 255, 0.1)' },
            }}
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* CVE Detail Modal */}
      <Dialog
        open={cveDialogOpen}
        onClose={() => { setCveDialogOpen(false); setDescGenError(null); }}
        maxWidth="sm"
        fullWidth
        sx={{
          '& .MuiDialog-paper': {
            bgcolor: isLight ? theme.palette.background.paper : 'rgba(5, 5, 15, 0.97)',
            border: isLight ? `1px solid ${theme.palette.divider}` : '1px solid rgba(0, 243, 255, 0.4)',
            backdropFilter: isLight ? 'none' : 'blur(20px)',
            borderRadius: 2,
          },
        }}
      >
        <DialogTitle sx={{ pb: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <Box>
              <Typography variant="h6" sx={{ fontFamily: 'var(--r3-heading-font)', fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1.5, color: isLight ? theme.palette.primary.main : '#00f3ff' }}>
                {selectedCve}
              </Typography>
              {cveInfo && (
                <Typography variant="caption" sx={{ color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.5)', fontFamily: 'Inter', display: 'block', mt: 0.25 }}>
                  {cveInfo.assigner ? `Assigner: ${cveInfo.assigner}` : 'Threat Intelligence Data'}
                </Typography>
              )}
            </Box>
            {cveInfo && cveInfo.cvss_v31_base_score !== null && (
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 0.5 }}>
                <Chip
                  label={`CVSS ${cveInfo.cvss_v31_base_score}`}
                  size="small"
                  sx={{
                    fontFamily: 'var(--r3-heading-font)',
                    fontSize: '0.7rem',
                    fontWeight: 900,
                    bgcolor: `${getCvssColor(cveInfo.cvss_v31_base_score)}20`,
                    color: getCvssColor(cveInfo.cvss_v31_base_score),
                    border: `1px solid ${getCvssColor(cveInfo.cvss_v31_base_score)}55`,
                    borderRadius: 0.5,
                  }}
                />
              </Box>
            )}
          </Box>
        </DialogTitle>

        <DialogContent sx={{ pt: 0 }}>
          {cveLoading && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 3 }}>
              <CircularProgress size={20} sx={{ color: isLight ? theme.palette.primary.main : '#00f3ff' }} />
              <Typography variant="body2" sx={{ color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.5)', fontFamily: 'Inter', fontSize: '0.8rem' }}>
                Loading enriched CVE intelligence...
              </Typography>
            </Box>
          )}

          {cveError && (
            <Typography variant="body2" sx={{ color: '#ff003c', fontFamily: 'Inter', fontSize: '0.8rem', py: 2 }}>
              {cveError}
            </Typography>
          )}

          {cveInfo && !cveLoading && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
              {/* CISA KEV Alert — semantic red, unchanged in both modes */}
              {cveInfo.is_cisa_kev && (
                <Box sx={{
                  p: 1,
                  bgcolor: 'rgba(255, 0, 60, 0.1)',
                  border: '1px solid rgba(255, 0, 60, 0.3)',
                  borderRadius: 0.5,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  boxShadow: '0 0 10px rgba(255, 0, 60, 0.1)'
                }}>
                  <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: '#ff003c', animation: 'pulse 1.5s infinite', boxShadow: '0 0 8px #ff003c' }} />
                  <Typography variant="body2" sx={{ fontFamily: 'Inter', fontSize: '0.75rem', fontWeight: 800, color: '#ff003c', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    Warning: Actively Exploited (CISA KEV)
                  </Typography>
                </Box>
              )}

              {/* EPSS Score Bar */}
              {cveInfo.epss_score !== null && (
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                    <Typography variant="subtitle2" sx={{ fontFamily: 'var(--r3-heading-font)', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: isLight ? theme.palette.primary.main : '#00f3ff' }}>
                      EPSS Exploit Probability
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'var(--r3-heading-font)', fontSize: '0.7rem', fontWeight: 800, color: isLight ? theme.palette.primary.main : '#00f3ff' }}>
                      {(cveInfo.epss_score * 100).toFixed(2)}% ({cveInfo.epss_percentile?.toFixed(1) || 0}th percentile)
                    </Typography>
                  </Box>
                  <Box sx={{ width: '100%', height: 6, bgcolor: isLight ? theme.palette.action.hover : 'rgba(255,255,255,0.05)', borderRadius: 3, overflow: 'hidden', border: `1px solid ${isLight ? theme.palette.divider : 'rgba(255,255,255,0.05)'}` }}>
                    <Box sx={{ width: `${Math.min(cveInfo.epss_score * 100, 100).toFixed(1)}%`, height: '100%', bgcolor: theme.palette.primary.main, boxShadow: isLight ? 'none' : `0 0 8px ${theme.palette.primary.main}` }} />
                  </Box>
                </Box>
              )}

              {/* Metrics Grid */}
              <Typography variant="subtitle2" sx={{ fontFamily: 'var(--r3-heading-font)', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: isLight ? themeTokens.enterprise.severity.unknown : '#7000ff' }}>
                CVSS v3.1 Metrics
              </Typography>
              <Grid container spacing={1}>
                <Grid size={{ xs: 6, sm: 4 }}>
                  <Box sx={{ p: 1, bgcolor: isLight ? alpha(theme.palette.primary.main, 0.04) : 'rgba(255, 255, 255, 0.02)', border: `1px solid ${isLight ? theme.palette.divider : 'rgba(255, 255, 255, 0.05)'}`, borderRadius: 1 }}>
                    <Typography variant="caption" sx={{ fontSize: '0.55rem', fontWeight: 700, color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.4)', textTransform: 'uppercase', display: 'block' }}>Attack Vector</Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.7rem', fontWeight: 800, color: isLight ? theme.palette.text.primary : '#fff', textTransform: 'uppercase' }}>{cveInfo.attack_vector || 'N/A'}</Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 6, sm: 4 }}>
                  <Box sx={{ p: 1, bgcolor: isLight ? alpha(theme.palette.primary.main, 0.04) : 'rgba(255, 255, 255, 0.02)', border: `1px solid ${isLight ? theme.palette.divider : 'rgba(255, 255, 255, 0.05)'}`, borderRadius: 1 }}>
                    <Typography variant="caption" sx={{ fontSize: '0.55rem', fontWeight: 700, color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.4)', textTransform: 'uppercase', display: 'block' }}>Complexity</Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.7rem', fontWeight: 800, color: isLight ? theme.palette.text.primary : '#fff', textTransform: 'uppercase' }}>{cveInfo.attack_complexity || 'N/A'}</Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 6, sm: 4 }}>
                  <Box sx={{ p: 1, bgcolor: isLight ? alpha(theme.palette.primary.main, 0.04) : 'rgba(255, 255, 255, 0.02)', border: `1px solid ${isLight ? theme.palette.divider : 'rgba(255, 255, 255, 0.05)'}`, borderRadius: 1 }}>
                    <Typography variant="caption" sx={{ fontSize: '0.55rem', fontWeight: 700, color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.4)', textTransform: 'uppercase', display: 'block' }}>User Interaction</Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.7rem', fontWeight: 800, color: isLight ? theme.palette.text.primary : '#fff', textTransform: 'uppercase' }}>{cveInfo.user_interaction || 'N/A'}</Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 6, sm: 4 }}>
                  <Box sx={{ p: 1, bgcolor: isLight ? alpha(theme.palette.primary.main, 0.04) : 'rgba(255, 255, 255, 0.02)', border: `1px solid ${isLight ? theme.palette.divider : 'rgba(255, 255, 255, 0.05)'}`, borderRadius: 1 }}>
                    <Typography variant="caption" sx={{ fontSize: '0.55rem', fontWeight: 700, color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.4)', textTransform: 'uppercase', display: 'block' }}>Confidentiality</Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.7rem', fontWeight: 800, color: cveInfo.confidentiality_impact === 'HIGH' ? (isLight ? themeTokens.enterprise.severity.critical : '#ff003c') : cveInfo.confidentiality_impact === 'LOW' ? (isLight ? themeTokens.enterprise.severity.high : '#ff9f00') : (isLight ? themeTokens.enterprise.severity.low : '#00ff62'), textTransform: 'uppercase' }}>{cveInfo.confidentiality_impact || 'N/A'}</Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 6, sm: 4 }}>
                  <Box sx={{ p: 1, bgcolor: isLight ? alpha(theme.palette.primary.main, 0.04) : 'rgba(255, 255, 255, 0.02)', border: `1px solid ${isLight ? theme.palette.divider : 'rgba(255, 255, 255, 0.05)'}`, borderRadius: 1 }}>
                    <Typography variant="caption" sx={{ fontSize: '0.55rem', fontWeight: 700, color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.4)', textTransform: 'uppercase', display: 'block' }}>Integrity</Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.7rem', fontWeight: 800, color: cveInfo.integrity_impact === 'HIGH' ? (isLight ? themeTokens.enterprise.severity.critical : '#ff003c') : cveInfo.integrity_impact === 'LOW' ? (isLight ? themeTokens.enterprise.severity.high : '#ff9f00') : (isLight ? themeTokens.enterprise.severity.low : '#00ff62'), textTransform: 'uppercase' }}>{cveInfo.integrity_impact || 'N/A'}</Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 6, sm: 4 }}>
                  <Box sx={{ p: 1, bgcolor: isLight ? alpha(theme.palette.primary.main, 0.04) : 'rgba(255, 255, 255, 0.02)', border: `1px solid ${isLight ? theme.palette.divider : 'rgba(255, 255, 255, 0.05)'}`, borderRadius: 1 }}>
                    <Typography variant="caption" sx={{ fontSize: '0.55rem', fontWeight: 700, color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.4)', textTransform: 'uppercase', display: 'block' }}>Availability</Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.7rem', fontWeight: 800, color: cveInfo.availability_impact === 'HIGH' ? (isLight ? themeTokens.enterprise.severity.critical : '#ff003c') : cveInfo.availability_impact === 'LOW' ? (isLight ? themeTokens.enterprise.severity.high : '#ff9f00') : (isLight ? themeTokens.enterprise.severity.low : '#00ff62'), textTransform: 'uppercase' }}>{cveInfo.availability_impact || 'N/A'}</Typography>
                  </Box>
                </Grid>
              </Grid>

              {/* Description */}
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                  <Typography variant="subtitle2" sx={{ fontFamily: 'var(--r3-heading-font)', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: isLight ? themeTokens.enterprise.severity.unknown : '#7000ff' }}>
                    Description
                  </Typography>
                  <Tooltip title={cveInfo.ai_risk_assessment ? 'Regenerate AI description' : 'Generate AI description'} placement="top">
                    <IconButton
                      size="small"
                      onClick={handleGenerateCveDescription}
                      disabled={descGenerating}
                      sx={{
                        width: 18,
                        height: 18,
                        fontSize: '0.6rem',
                        fontWeight: 900,
                        color: isLight ? themeTokens.enterprise.severity.unknown : '#7000ff',
                        border: `1px solid ${isLight ? alpha(themeTokens.enterprise.severity.unknown as string, 0.4) : 'rgba(112, 0, 255, 0.4)'}`,
                        borderRadius: '50%',
                        p: 0,
                        '&:hover': { bgcolor: isLight ? alpha(themeTokens.enterprise.severity.unknown as string, 0.1) : 'rgba(112, 0, 255, 0.1)' },
                        '&:disabled': { opacity: 0.5 },
                      }}
                    >
                      {descGenerating ? <CircularProgress size={10} sx={{ color: 'inherit' }} /> : '?'}
                    </IconButton>
                  </Tooltip>
                </Box>
                {descGenError && (
                  <Typography variant="caption" sx={{ color: '#ff003c', fontFamily: 'Inter', fontSize: '0.7rem', display: 'block', mb: 0.5 }}>
                    {descGenError}
                  </Typography>
                )}
                <Typography variant="body2" sx={{ fontFamily: 'Inter', fontSize: '0.8rem', color: isLight ? theme.palette.text.primary : 'rgba(255,255,255,0.8)', lineHeight: 1.6 }}>
                  {cveInfo.summary || 'No description summary available. Click ? to generate with AI.'}
                </Typography>
              </Box>

              {/* References */}
              {cveInfo.references && cveInfo.references.length > 0 && (
                <Box>
                  <Divider sx={{ borderColor: isLight ? theme.palette.divider : 'rgba(0, 243, 255, 0.1)', mb: 1.5 }} />
                  <Typography variant="subtitle2" sx={{ fontFamily: 'var(--r3-heading-font)', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: isLight ? themeTokens.enterprise.severity.high : '#ff9f00', mb: 1 }}>
                    References
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75, maxHeight: 120, overflowY: 'auto', pr: 1 }}>
                    {cveInfo.references.map((ref: string, i: number) => (
                      <Box key={i} sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                        <Box sx={{ width: 4, height: 4, borderRadius: '50%', bgcolor: isLight ? themeTokens.enterprise.severity.high : '#ff9f00', mt: 0.8, flexShrink: 0 }} />
                        <Typography
                          component="a"
                          href={ref}
                          target="_blank"
                          rel="noopener noreferrer"
                          variant="body2"
                          sx={{
                            fontFamily: 'Inter',
                            fontSize: '0.75rem',
                            color: 'primary.main',
                            textDecoration: 'none',
                            wordBreak: 'break-all',
                            '&:hover': { textDecoration: 'underline' }
                          }}
                        >
                          {ref}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setCveDialogOpen(false)}
            size="small"
            sx={{
              fontFamily: 'var(--r3-heading-font)',
              fontSize: '0.65rem',
              fontWeight: 800,
              textTransform: 'uppercase',
              letterSpacing: 1,
              color: isLight ? theme.palette.primary.main : '#00f3ff',
              border: `1px solid ${isLight ? alpha(theme.palette.primary.main, 0.4) : 'rgba(0, 243, 255, 0.4)'}`,
              px: 2,
              '&:hover': { bgcolor: isLight ? alpha(theme.palette.primary.main, 0.1) : 'rgba(0, 243, 255, 0.1)' },
            }}
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

const getCvssColor = (score: number) => {
  if (score >= 9.0) return '#ff003c';
  if (score >= 7.0) return '#ff9f00';
  if (score >= 4.0) return '#fffc00';
  if (score > 0.0) return '#00ff62';
  return '#00f3ff';
};
