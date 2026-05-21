import React, { useState } from 'react';
import { useParams, Link as RouterLink } from '@tanstack/react-router';
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  Button,
  IconButton,
  Stack,
  Chip,
  Tab,
  Tabs,
  Paper,
  Divider,
  useTheme,
  CircularProgress,
  Tooltip as MuiTooltip,
  List,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Avatar,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material';
import {
  Activity,
  Globe,
  Shield,
  Server,
  Zap,
  Terminal,
  AlertTriangle,
  Target,
  Map as MapIcon,
  ChevronRight,
  Clock,
  ExternalLink,
  Info,
  Layers,
  Search,
  Database,
  Cpu,
  MoreHorizontal,
  Plus,
  Link as LinkIcon,
  FileText,
  BarChart2,
  ShieldAlert,
  ChevronUp,
  ChevronDown,
  Eye,
  Folder,
  Camera,
  BarChart2 as BarChartIcon
} from 'lucide-react';
import { useTargetSummary } from '../api';
import Chart from 'react-apexcharts';
import { GeoMap } from '../../dashboard/components/GeoMap';
import { KpiCard } from '../../../components/KpiCard';
import { TacticalPanel } from '../../../components/TacticalPanel';
import { SubdomainsTab } from '../../scans/components/SubdomainsTab';
import { EndpointsTab } from '../../scans/components/EndpointsTab';
import { DirectoriesTab } from '../../scans/components/DirectoriesTab';
import { VulnerabilityTable } from '../../vulnerabilities/components/VulnerabilityTable';
import PluginComponent from '../../plugins/components/PluginComponent';
import VisualizationTab from '../../scans/components/VisualizationTab';
import { AttackSurfaceTab } from '../../scans/components/AttackSurfaceTab';


const SeverityBadge: React.FC<{ severity: number }> = ({ severity }) => {
  const configs: any = {
    4: { label: 'CRITICAL', color: '#ff003c' },
    3: { label: 'HIGH', color: '#ff9f00' },
    2: { label: 'MEDIUM', color: '#fffc00' },
    1: { label: 'LOW', color: '#00ff62' },
    0: { label: 'INFO', color: '#00f3ff' },
    [-1]: { label: 'UNKNOWN', color: '#7000ff' }
  };
  const config = configs[severity] || configs[-1];
  return (
    <Box sx={{
      display: 'inline-flex',
      px: 1,
      py: 0.2,
      borderRadius: 0.5,
      bgcolor: `${config.color}20`,
      border: `1px solid ${config.color}50`,
      color: config.color,
      fontSize: '0.6rem',
      fontWeight: 900
    }}>
      {config.label}
    </Box>
  );
};

export const TargetSummary = () => {
  const { projectSlug, targetId } = useParams({ strict: false });
  const { data, isLoading, error } = useTargetSummary(projectSlug || 'default', parseInt(targetId || '0'));
  const [activeTab, setActiveTab] = useState(0);
  const [infoTab, setInfoTab] = useState(0);
  const theme = useTheme();

  if (isLoading) {
    return (
      <Box sx={{ height: '80vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3 }}>
        <CircularProgress size={60} thickness={2} sx={{ color: '#00f3ff' }} />
        <Typography sx={{ color: '#00f3ff', fontFamily: 'Orbitron', letterSpacing: 4, fontSize: '0.8rem' }}>
          BOOTING SYSTEM CORE...
        </Typography>
      </Box>
    );
  }

  if (error || !data) {
    return (
      <Box sx={{ height: '80vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="error">ERROR: DATA FETCH FAILED</Typography>
      </Box>
    );
  }

  const tabs = [
    { label: 'HOME', icon: Activity },
    { label: 'SUBDOMAINS', icon: Globe },
    { label: 'DIRECTORIES', icon: Folder },
    { label: 'URLS', icon: LinkIcon },
    { label: 'VULNERABILITIES', icon: ShieldAlert },
    { label: 'ATTACK SURFACE', icon: MapIcon },
    { label: 'MONITORING', icon: Eye },
    { label: 'VISUALIZATION', icon: BarChart2 },
  ];

  const renderHome = () => (
    <Box sx={{ flexGrow: 1 }}>
      <Box sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: '300px 1fr', lg: '350px 1fr' },
        gap: 3,
        alignItems: 'start'
      }}>
        {/* COLUMN 1: SIDEBAR */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <TacticalPanel title="Scan Timeline" icon={<Activity size={14} />}>
            <Box sx={{ p: 2 }}>
              <Typography component="div" sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)', mb: 2 }}>
                Target <Chip label={data.target_info.name} size="small" sx={{ height: 16, fontSize: '0.6rem', bgcolor: 'rgba(0,243,255,0.1)', color: '#00f3ff' }} /> has been scanned <b>{data.scan_count}</b> times.
              </Typography>
              <List sx={{ p: 0 }}>
                {data.recent_scans?.map((scan: any) => (
                  <Box key={scan.id} sx={{ mb: 2, pl: 2, borderLeft: '2px solid rgba(0, 243, 255, 0.2)', position: 'relative' }}>
                    <Box sx={{ position: 'absolute', left: -5, top: 0, width: 8, height: 8, borderRadius: '50%', bgcolor: '#00f3ff' }} />
                    <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                      <Typography sx={{ fontSize: '0.75rem', fontWeight: 900, color: '#fff' }}>{scan.engine_name}</Typography>
                      <Chip
                        label={scan.scan_status === 2 ? 'Completed' : 'Scanning'}
                        size="small"
                        sx={{ height: 16, fontSize: '0.55rem', fontWeight: 900, bgcolor: scan.scan_status === 2 ? 'rgba(0, 255, 98, 0.1)' : 'rgba(0, 243, 255, 0.1)', color: scan.scan_status === 2 ? '#00ff62' : '#00f3ff' }}
                      />
                    </Stack>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', display: 'block', mb: 1 }}>{scan.completed_ago}</Typography>
                    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                      <Typography sx={{ fontSize: '0.7rem', color: '#00f3ff', fontWeight: 700 }}>{scan.subdomain_count} Subdomains Discovered</Typography>
                      {scan.subdomain_diff !== 0 && (
                        <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center' }}>
                          {scan.subdomain_diff > 0 ? <ChevronUp size={12} color="#00ff62" /> : <ChevronDown size={12} color="#ff003c" />}
                          <Typography sx={{ fontSize: '0.65rem', fontWeight: 900, color: scan.subdomain_diff > 0 ? '#00ff62' : '#ff003c' }}>{Math.abs(scan.subdomain_diff)}</Typography>
                        </Stack>
                      )}
                    </Stack>
                  </Box>
                ))}
              </List>
            </Box>
          </TacticalPanel>

          <TacticalPanel 
            title="Sub Scans" 
            icon={<Layers size={14} />}
            headerAction={
              <Box sx={{ 
                px: 1, 
                py: 0.2, 
                bgcolor: 'rgba(112, 0, 255, 0.15)', 
                border: '1px solid rgba(112, 0, 255, 0.3)', 
                borderRadius: 0.5 
              }}>
                <Typography sx={{ fontSize: '0.65rem', fontWeight: 900, color: '#7000ff' }}>{data.subscans?.length || 0}</Typography>
              </Box>
            }
          >
            <Box sx={{ p: 1 }}>
              <Stack spacing={2}>
                {data.subscans?.slice(0, 8).map((scan: any) => (
                  <Box 
                    key={scan.id} 
                    sx={{ 
                      bgcolor: 'rgba(255, 255, 255, 0.02)', 
                      border: '1px solid rgba(255, 255, 255, 0.05)', 
                      borderRadius: 1.5, 
                      overflow: 'hidden'
                    }}
                  >
                    {/* Item Header */}
                    <Box sx={{ bgcolor: 'rgba(0, 243, 255, 0.08)', px: 1.5, py: 1, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>
                      <Typography sx={{ fontSize: '0.5rem', fontWeight: 720, color: '#00f3ff', textTransform: 'uppercase', letterSpacing: 1, opacity: 0.8 }}>
                        {(scan.engine || scan.type || 'SCAN').replace(/_/g, ' ')} ON
                      </Typography>
                      <Typography sx={{ fontSize: '0.65rem', fontWeight: 820, color: '#00f3ff', fontFamily: 'Orbitron' }}>
                        {(scan.subdomain_name || data.target_info.name).toUpperCase()}
                      </Typography>
                    </Box>

                    {/* Item Body */}
                    <Box sx={{ p: 1.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography sx={{ fontSize: '0.7rem', color: '#fff', fontWeight: 500, mb: 0.2 }}>
                          Task Completed {scan.completed_ago}
                        </Typography>
                        <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', fontWeight: 600 }}>
                          Took {scan.time_taken || '0 minutes'}
                        </Typography>
                      </Box>
                      <Chip 
                        label="Task Completed" 
                        size="small" 
                        sx={{ 
                          height: 20, 
                          fontSize: '0.55rem', 
                          fontWeight: 900, 
                          bgcolor: 'transparent', 
                          color: '#00ff62', 
                          border: '1px solid rgba(0, 255, 98, 0.3)',
                          borderRadius: 0.5
                        }} 
                      />
                    </Box>
                  </Box>
                ))}
                {(!data.subscans || data.subscans.length === 0) && (
                  <Typography sx={{ textAlign: 'center', py: 4, color: 'rgba(255,255,255,0.2)', fontSize: '0.7rem' }}>
                    NO SUB SCANS IDENTIFIED
                  </Typography>
                )}
              </Stack>
            </Box>
          </TacticalPanel>

          <TacticalPanel title="Related Domains" icon={<LinkIcon size={14} />}>
            <Box sx={{ p: 2 }}>
              <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                {data.related_domains?.map((d: string) => (
                  <Chip
                    key={d}
                    label={d}
                    size="small"
                    variant="outlined"
                    sx={{ mb: 1, borderColor: 'rgba(0, 243, 255, 0.2)', color: '#00f3ff', fontSize: '0.65rem', fontWeight: 700, '&:hover': { bgcolor: 'rgba(0,243,255,0.1)' } }}
                  />
                ))}
                {data.related_domains?.length === 0 && <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.2)', py: 2 }}>NO RELATED DOMAINS FOUND</Typography>}
              </Stack>
            </Box>
          </TacticalPanel>
        </Box>

        {/* COLUMN 2: MAIN CONTENT */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* TOP KPIs ROW */}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' }, gap: 2 }}>
            <KpiCard
              title="TOTAL SCANS"
              value={data.scan_count}
              subtitle={`${data.this_week_scan_count} THIS WEEK`}
              color="#00f3ff"
              icon={Activity}
              sx={{ height: 180 }}
            />
            <KpiCard
              title="SUBDOMAINS"
              value={data.subdomain_count}
              subtitle={`${data.alive_count} ALIVE`}
              color="#7000ff"
              icon={Layers}
              sx={{ height: 180 }}
            />
            <KpiCard
              title="ENDPOINTS"
              value={data.endpoint_count}
              subtitle={`${data.endpoint_alive_count} ALIVE`}
              color="#ff00f7"
              icon={Target}
              sx={{ height: 180 }}
            />
            <KpiCard
              title="VULNERABILITIES"
              value={data.vulnerability_count}
              subtitle={`${data.critical_count} CRITICAL`}
              color="#ff003c"
              icon={ShieldAlert}
              sx={{ height: 180 }}
            />
          </Box>

          {/* MIDDLE ROW: Target Info & HTTP Chart */}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '7fr 5fr' }, gap: 2 }}>
            <TacticalPanel title="Target Information" icon={<Activity size={14} />} sx={{ minHeight: 400 }}>
              <Box sx={{ p: 2 }}>
                <Tabs value={infoTab} onChange={(_, v) => setInfoTab(v)} sx={{ mb: 2, borderBottom: '1px solid rgba(255,255,255,0.05)', minHeight: 32 }}>
                  {['Domain Info', 'Whois', 'DNS Records', 'Nameservers', 'History'].map((l) => (
                    <Tab key={l} label={l} sx={{ fontSize: '0.65rem', fontWeight: 900, minHeight: 32, p: 1, color: 'rgba(255,255,255,0.4)', '&.Mui-selected': { color: '#00f3ff' } }} />
                  ))}
                </Tabs>

                {infoTab === 0 && (
                  <Box sx={{ 
                    display: 'grid', 
                    gridTemplateColumns: 'repeat(3, 1fr)', 
                    gap: 3 
                  }}>
                    <Box><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Domain</Typography><Typography sx={{ fontSize: '0.8rem', fontWeight: 700, color: '#ff003c' }}>{data.target_info.name}</Typography></Box>
                    <Box><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Dnssec</Typography><Typography sx={{ fontSize: '0.8rem', fontWeight: 700 }}>{data.domain_info?.dnssec || 'N/A'}</Typography></Box>
                    <Box><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Geolocation</Typography><Typography sx={{ fontSize: '0.8rem', fontWeight: 700 }}>{data.domain_info?.geolocation_iso || 'N/A'}</Typography></Box>
                    <Box><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Created</Typography><Typography sx={{ fontSize: '0.7rem' }}>{data.domain_info?.created || 'N/A'}</Typography></Box>
                    <Box><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Updated</Typography><Typography sx={{ fontSize: '0.7rem' }}>{data.domain_info?.updated || 'N/A'}</Typography></Box>
                    <Box><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Expires</Typography><Typography sx={{ fontSize: '0.7rem' }}>{data.domain_info?.expires || 'N/A'}</Typography></Box>
                    <Box sx={{ gridColumn: 'span 3' }}><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Registrar</Typography><Typography sx={{ fontSize: '0.75rem', fontWeight: 700, color: '#00f3ff' }}>{data.domain_info?.registrar?.name || 'N/A'}</Typography></Box>
                  </Box>
                )}
                {infoTab === 1 && <Typography sx={{ p: 2, fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)' }}>Loading WHOIS Data...</Typography>}
                {infoTab === 2 && (
                  <Stack spacing={1}>
                    {data.domain_info?.dns_records?.map((r: any, idx: number) => (
                      <Stack key={idx} direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                        <Chip label={r.type.toUpperCase()} size="small" sx={{ height: 16, fontSize: '0.55rem', fontWeight: 900, bgcolor: 'rgba(0,243,255,0.1)', color: '#00f3ff' }} />
                        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)' }}>{r.name}</Typography>
                      </Stack>
                    ))}
                  </Stack>
                )}
              </Box>
            </TacticalPanel>
            <TacticalPanel title="HTTP Status Breakdown" icon={<Activity size={14} />} sx={{ minHeight: 400 }}>
              <Box sx={{ p: 2, height: 350 }}>
                <Chart
                  options={{
                    chart: { type: 'donut', background: 'transparent' },
                    theme: { mode: 'dark' as any },
                    stroke: { show: false },
                    dataLabels: { enabled: false },
                    legend: { position: 'bottom', fontSize: '10px', labels: { colors: '#fff' } },
                    colors: ['#00ff62', '#ff003c', '#00f3ff', '#7000ff', '#fffc00']
                  }}
                  series={data.http_status_breakdown.map((s: any) => s.count)}
                  type="donut"
                  height="100%"
                />
              </Box>
            </TacticalPanel>
          </Box>

          {/* Geo Map Section */}
          <GeoMap data={data.asset_countries || []} />

          {/* Vulnerability Widgets */}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '5fr 7fr' }, gap: 2 }}>
            <TacticalPanel title="Vulnerability Severity" icon={<ShieldAlert size={14} />}>
              <Box sx={{ p: 2, height: 350 }}>
                <Chart
                  options={{
                    chart: { type: 'pie', background: 'transparent' },
                    theme: { mode: 'dark' as any },
                    labels: ['Critical', 'High', 'Medium', 'Low', 'Info'],
                    colors: ['#ff003c', '#ff8c00', '#fffc00', '#00f3ff', 'rgba(255,255,255,0.2)'],
                    legend: { position: 'bottom', labels: { colors: '#fff' } }
                  }}
                  series={[data.critical_count || 0, data.high_count || 0, data.medium_count || 0, data.low_count || 0, data.info_count || 0]}
                  type="pie"
                  height="100%"
                />
              </Box>
            </TacticalPanel>
            <TacticalPanel title="Vulnerability Highlights" icon={<Shield size={14} />}>
              <TableContainer sx={{ p: 1 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem' }}>NAME</TableCell>
                      <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem' }}>SEVERITY</TableCell>
                      <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem' }}>DATE</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.vulnerability_highlights?.map((v: any, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell sx={{ fontSize: '0.7rem', color: '#fff', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>{v.name}</TableCell>
                        <TableCell><SeverityBadge severity={v.severity} /></TableCell>
                        <TableCell sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>{v.discovered_date}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </TacticalPanel>
          </Box>

          {/* Infrastructure Widgets */}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr 1fr' }, gap: 2 }}>
            <TacticalPanel title="Most Common CVE IDs" icon={<BarChart2 size={14} />} sx={{ height: 280 }}>
              <Box sx={{ p: 1, height: '100%' }}>
                <Chart
                  options={{
                    chart: { type: 'bar', toolbar: { show: false } },
                    plotOptions: { bar: { horizontal: true, borderRadius: 2 } },
                    xaxis: { categories: data.most_common_cve?.map((c: any) => c.name) },
                    colors: ['#ff003c']
                  }}
                  series={[{ data: data.most_common_cve?.map((c: any) => c.count || c.nused) }]}
                  type="bar"
                  height="100%"
                />
              </Box>
            </TacticalPanel>
            <TacticalPanel title="Most Common CWE IDs" icon={<BarChart2 size={14} />} sx={{ height: 280 }}>
              <Box sx={{ p: 1, height: '100%' }}>
                <Chart
                  options={{
                    chart: { type: 'bar', toolbar: { show: false } },
                    plotOptions: { bar: { horizontal: true, borderRadius: 2 } },
                    xaxis: { categories: data.most_common_cwe?.map((c: any) => c.name) },
                    colors: ['#ff9f00']
                  }}
                  series={[{ data: data.most_common_cwe?.map((c: any) => c.count || c.nused) }]}
                  type="bar"
                  height="100%"
                />
              </Box>
            </TacticalPanel>
            <TacticalPanel title="Most Common Tags" icon={<BarChart2 size={14} />} sx={{ height: 280 }}>
              <Box sx={{ p: 1, height: '100%' }}>
                <Chart
                  options={{
                    chart: { type: 'bar', toolbar: { show: false } },
                    plotOptions: { bar: { horizontal: true, borderRadius: 2 } },
                    xaxis: { categories: data.most_common_tags?.map((c: any) => c.name) },
                    colors: ['#00ff62']
                  }}
                  series={[{ data: data.most_common_tags?.map((c: any) => c.count || c.nused) }]}
                  type="bar"
                  height="100%"
                />
              </Box>
            </TacticalPanel>
          </Box>

          {/* Footer Info Cards */}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr 1fr' }, gap: 2 }}>
            <TacticalPanel title="IP Ranges & Scope" icon={<Database size={14} />} sx={{ height: 300 }}>
              <Box sx={{ p: 2 }}>
                {data.target_info?.in_scope_ips && data.target_info.in_scope_ips.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="overline" sx={{ color: 'rgba(0, 243, 255, 0.6)', fontWeight: 900, display: 'block', mb: 1, letterSpacing: 1 }}>
                      MANUAL IN-SCOPE RANGES
                    </Typography>
                    <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                      {data.target_info.in_scope_ips.map((ip: string) => (
                        <Chip key={ip} label={ip} size="small" sx={{ mb: 1, bgcolor: 'rgba(0, 243, 255, 0.15)', color: '#00f3ff', border: '1px solid rgba(0, 243, 255, 0.3)', fontWeight: 800, fontFamily: 'monospace' }} />
                      ))}
                    </Stack>
                  </Box>
                )}
                <Typography variant="overline" sx={{ color: 'rgba(255, 255, 255, 0.3)', fontWeight: 900, display: 'block', mb: 1, letterSpacing: 1 }}>
                  HISTORICAL RESOLVED IPS
                </Typography>
                <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                  {data.domain_info?.historical_ips?.map((ip: any) => (
                    <Chip key={ip.ip} label={ip.ip} size="small" sx={{ mb: 1, bgcolor: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.7)', border: '1px solid rgba(255,255,255,0.1)' }} />
                  ))}
                  {(!data.domain_info?.historical_ips || data.domain_info.historical_ips.length === 0) && (
                    <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.2)', py: 1 }}>NO RESOLVED IPS</Typography>
                  )}
                </Stack>
              </Box>
            </TacticalPanel>
            <TacticalPanel title="Discovered Ports" icon={<Server size={14} />} sx={{ height: 300 }}>
              <Box sx={{ p: 2 }}>
                <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                  {data.discovered_ports?.map((p: any) => (
                    <Chip key={p.number} label={`${p.number}/${p.service_name}`} size="small" sx={{ mb: 1, bgcolor: 'rgba(112,0,255,0.1)', color: '#7000ff', border: '1px solid rgba(112,0,255,0.2)' }} />
                  ))}
                </Stack>
              </Box>
            </TacticalPanel>
            <TacticalPanel title="Technologies" icon={<Cpu size={14} />} sx={{ height: 300 }}>
              <Box sx={{ p: 2 }}>
                <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                  {data.discovered_technologies?.map((t: any) => (
                    <Chip key={t.name} label={t.name} size="small" sx={{ mb: 1, bgcolor: 'rgba(255,252,0,0.1)', color: '#fffc00', border: '1px solid rgba(255,252,0,0.2)' }} />
                  ))}
                </Stack>
              </Box>
            </TacticalPanel>
          </Box>
        </Box>
      </Box>
    </Box>
  );

  const renderMonitoring = () => (
    <TacticalPanel title={`Monitoring Discoveries for ${data.target_info.name}`} icon={<Eye size={14} />}>
      <TableContainer>
        <Table size="small">
          <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
            <TableRow>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>TYPE</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>DISCOVERY</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>DATE</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data.monitoring_discoveries || []).map((m: any, idx: number) => (
              <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.05)' } }}>
                <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <Chip
                    label={m.discovery_type?.toUpperCase()}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: '0.6rem',
                      fontWeight: 900,
                      bgcolor: m.discovery_type === 'subdomain' ? 'rgba(0,255,98,0.1)' : 'rgba(255,252,0,0.1)',
                      color: m.discovery_type === 'subdomain' ? '#00ff62' : '#fffc00'
                    }}
                  />
                </TableCell>
                <TableCell sx={{ color: '#fff', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <code style={{ fontSize: '0.7rem' }}>{m.content?.name || m.content?.url}</code>
                </TableCell>
                <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  {m.discovered_at}
                </TableCell>
              </TableRow>
            ))}
            {(!data.monitoring_discoveries || data.monitoring_discoveries.length === 0) && (
              <TableRow>
                <TableCell colSpan={3} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO MONITORING DISCOVERIES FOUND</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </TacticalPanel>
  );

  return (
    <Box sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 900, fontFamily: 'Orbitron', color: '#fff', letterSpacing: 2 }}>TARGET SUMMARY</Typography>
            <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', fontWeight: 600 }}>IDENTIFIER: {targetId} | TARGET: {data.target_info.name}</Typography>
          </Box>
          <Stack direction="row" spacing={1} sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>
            <span>TARGETS</span> / <span>SUMMARY</span> / <span style={{ color: '#00f3ff' }}>{data.target_info.name}</span>
          </Stack>
        </Stack>
      </Box>

      {/* Tab Bar Integration */}
      <Box sx={{ mb: 3, borderBottom: '1px solid rgba(255,255,255,0.05)', position: 'sticky', top: 0, bgcolor: 'rgba(10,10,15,0.9)', zIndex: 10, backdropFilter: 'blur(10px)', borderRadius: '0 0 12px 12px' }}>
        <Tabs 
          value={activeTab} 
          onChange={(_, v) => setActiveTab(v)} 
          variant="scrollable"
          scrollButtons="auto"
          sx={{ 
            minHeight: 50, 
            '& .MuiTabs-indicator': { bgcolor: '#00f3ff', height: 3, boxShadow: '0 0 15px #00f3ff' },
            '& .MuiTabs-scrollButtons': { color: '#00f3ff' }
          }}
        >
          {tabs.map((tab, idx) => (
            <Tab 
              key={idx} 
              label={
                <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                  <tab.icon size={14} />
                  <span>{tab.label}</span>
                </Stack>
              } 
              sx={{ 
                fontSize: '0.65rem', 
                fontWeight: 900, 
                minHeight: 50, 
                color: 'rgba(255,255,255,0.4)', 
                letterSpacing: 1.5, 
                fontFamily: 'Orbitron',
                px: 3,
                '&.Mui-selected': { color: '#00f3ff' } 
              }} 
            />
          ))}
        </Tabs>
      </Box>

      {/* Tab Content */}
      <Box sx={{ mt: 2 }}>
        {tabs[activeTab]?.label === 'HOME' && renderHome()}
        {tabs[activeTab]?.label === 'SUBDOMAINS' && <SubdomainsTab projectSlug={projectSlug || 'default'} targetId={parseInt(targetId || '0')} />}
        {tabs[activeTab]?.label === 'DIRECTORIES' && <DirectoriesTab projectSlug={projectSlug || 'default'} targetId={parseInt(targetId || '0')} />}
        {tabs[activeTab]?.label === 'URLS' && <EndpointsTab projectSlug={projectSlug || 'default'} targetId={parseInt(targetId || '0')} />}
        {tabs[activeTab]?.label === 'VULNERABILITIES' && <PluginComponent 
      name="VulnerabilityTable" 
      default={VulnerabilityTable} 
      projectSlug={projectSlug || 'default'} 
      targetId={parseInt(targetId || '0')} 
    />}
        {tabs[activeTab]?.label === 'ATTACK SURFACE' && <AttackSurfaceTab projectSlug={projectSlug || 'default'} targetId={parseInt(targetId || '0')} />}
        {tabs[activeTab]?.label === 'MONITORING' && renderMonitoring()}
        {tabs[activeTab]?.label === 'VISUALIZATION' && <VisualizationTab projectSlug={projectSlug || 'default'} targetId={parseInt(targetId || '0')} />}
      </Box>
    </Box>
  );
};
