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
  ChevronDown
} from 'lucide-react';
import { useTargetSummary } from '../api';
import Chart from 'react-apexcharts';
import { GeoMap } from '../../dashboard/components/GeoMap';

// --- Tactical UI Components ---

const TacticalPanel: React.FC<{ title: string; icon?: any; children: React.ReactNode; sx?: any; subHeader?: string; action?: React.ReactNode }> = ({ title, icon: Icon, children, sx, subHeader, action }) => (
  <Paper sx={{ 
    height: '100%', 
    bgcolor: 'transparent', 
    backdropFilter: 'blur(10px)', 
    border: '1px solid rgba(0, 243, 255, 0.15)',
    borderRadius: 1.5,
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 4px 24px rgba(0,0,0,0.2)',
    ...sx 
  }}>
    <Box sx={{ 
      px: 2, 
      py: 1.5, 
      borderBottom: '1px solid rgba(0, 243, 255, 0.05)', 
      bgcolor: 'rgba(0, 243, 255, 0.02)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    }}>
      <Stack spacing={0.5}>
        <Stack direction="row" spacing={1} alignItems="center">
          {Icon && <Icon size={14} color="#00f3ff" />}
          <Typography sx={{ 
            fontSize: '0.7rem', 
            fontWeight: 800, 
            textTransform: 'uppercase', 
            letterSpacing: 1.5, 
            color: '#fff',
            fontFamily: 'Orbitron'
          }}>
            {title}
          </Typography>
        </Stack>
        {subHeader && (
          <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', fontWeight: 600 }}>
            {subHeader}
          </Typography>
        )}
      </Stack>
      {action}
    </Box>
    <Box sx={{ p: 2, flexGrow: 1, overflow: 'auto' }}>
      {children}
    </Box>
  </Paper>
);

const KPICard: React.FC<{ title: string; value: any; subValue?: string; color: string; info?: string; id?: string }> = ({ title, value, subValue, color, info, id }) => (
  <Paper id={id} sx={{ 
    p: 2, 
    borderRadius: 1.5, 
    bgcolor: 'transparent', 
    backdropFilter: 'blur(5px)',
    border: '1px solid rgba(255,255,255,0.1)',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    position: 'relative',
    transition: 'all 0.3s',
    '&:hover': {
      borderColor: `${color}60`,
      bgcolor: 'rgba(255,255,255,0.03)',
      transform: 'translateY(-2px)'
    }
  }}>
    <Box sx={{ position: 'absolute', top: 10, right: 10 }}>
      <MuiTooltip title={info || ""}>
        <Info size={12} color="rgba(255,255,255,0.3)" />
      </MuiTooltip>
    </Box>
    <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
      <Box sx={{ flexGrow: 1 }}>
        <Typography sx={{ fontSize: '0.65rem', fontWeight: 800, color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: 1, mb: 0.5 }}>
          {title}
        </Typography>
        <Typography sx={{ fontSize: '1.8rem', fontWeight: 900, color: color, fontFamily: 'Orbitron', lineHeight: 1.2 }}>
          {value}
        </Typography>
      </Box>
      {subValue && (
        <Box sx={{ minWidth: 'fit-content' }}>
          <Chip 
            label={subValue} 
            size="small" 
            sx={{ 
              height: 22, 
              fontSize: '0.65rem', 
              fontWeight: 800, 
              bgcolor: `${color}20`, 
              color: color, 
              border: `1px solid ${color}40`,
              borderRadius: 0.5
            }} 
          />
        </Box>
      )}
    </Stack>
  </Paper>
);

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
          BOOTING_SYSTEM_CORE...
        </Typography>
      </Box>
    );
  }

  if (error || !data) {
    return (
      <Box sx={{ height: '80vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="error">ERROR: DATA_FETCH_FAILED</Typography>
      </Box>
    );
  }

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
          <TacticalPanel title="Scan Timeline" icon={Activity}>
             <Box sx={{ p: 2 }}>
               <Typography component="div" sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)', mb: 2 }}>
                  Target <Chip label={data.target_info.name} size="small" sx={{ height: 16, fontSize: '0.6rem', bgcolor: 'rgba(0,243,255,0.1)', color: '#00f3ff' }} /> has been scanned <b>{data.scan_count}</b> times.
               </Typography>
               <List sx={{ p: 0 }}>
                 {data.recent_scans?.map((scan: any) => (
                   <Box key={scan.id} sx={{ mb: 2, pl: 2, borderLeft: '2px solid rgba(0, 243, 255, 0.2)', position: 'relative' }}>
                     <Box sx={{ position: 'absolute', left: -5, top: 0, width: 8, height: 8, borderRadius: '50%', bgcolor: '#00f3ff' }} />
                     <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                       <Typography sx={{ fontSize: '0.75rem', fontWeight: 900, color: '#fff' }}>{scan.engine_name}</Typography>
                       <Chip 
                          label={scan.scan_status === 2 ? 'Completed' : 'Scanning'} 
                          size="small" 
                          sx={{ height: 16, fontSize: '0.55rem', fontWeight: 900, bgcolor: scan.scan_status === 2 ? 'rgba(0, 255, 98, 0.1)' : 'rgba(0, 243, 255, 0.1)', color: scan.scan_status === 2 ? '#00ff62' : '#00f3ff' }} 
                       />
                     </Stack>
                     <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', display: 'block', mb: 1 }}>{scan.completed_ago}</Typography>
                     <Stack direction="row" spacing={1} alignItems="center">
                       <Typography sx={{ fontSize: '0.7rem', color: '#00f3ff', fontWeight: 700 }}>{scan.subdomain_count} Subdomains Discovered</Typography>
                       {scan.subdomain_diff !== 0 && (
                         <Stack direction="row" spacing={0.5} alignItems="center">
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

          <TacticalPanel title="Sub Scans" subHeader={`${data.subscans?.length || 0} Sub Scans`} icon={Layers}>
             <Box sx={{ p: 2 }}>
               <Stack spacing={1}>
                 {data.subscans?.slice(0, 8).map((scan: any) => (
                   <Box key={scan.id} sx={{ p: 1, bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(0, 243, 255, 0.05)', borderRadius: 1 }}>
                     <Typography sx={{ fontSize: '0.65rem', fontWeight: 800, color: '#00f3ff', textTransform: 'uppercase' }}>{scan.scan_type?.name}</Typography>
                     <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>Completed {scan.completed_ago}</Typography>
                     <Chip label="Task Completed" size="small" sx={{ height: 16, fontSize: '0.55rem', fontWeight: 900, bgcolor: 'rgba(0, 255, 98, 0.1)', color: '#00ff62', mt: 0.5 }} />
                   </Box>
                 ))}
               </Stack>
             </Box>
          </TacticalPanel>

          <TacticalPanel title="Related Domains" subHeader={`${data.related_domains?.length || 0} Domains related to ${data.target_info.name}`} icon={LinkIcon}>
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
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', lg: '1fr 1fr 1fr 1fr' }, gap: 2 }}>
            <KPICard title="Times target is scanned" value={data.scan_count} subValue={`${data.this_week_scan_count} Scans this week`} color="#00f3ff" info="The total times this target has been scanned." />
            <KPICard title="Subdomains Discovered" value={data.subdomain_count} subValue={`Alive Subdomains: ${data.alive_count}`} color="#00f3ff" info="Total subdomains identified by reNgine." />
            <KPICard title="Endpoints Discovered" value={data.endpoint_count} subValue={`Alive Endpoints: ${data.endpoint_alive_count}`} color="#00f3ff" info="Total endpoints discovered across all scans." />
            <KPICard title="Vulnerabilities Discovered" value={data.vulnerability_count} subValue={`${data.critical_count} Critical, ${data.high_count} High`} color="#ff003c" info="Total security vulnerabilities detected." />
          </Box>

          {/* MIDDLE ROW: Target Info & HTTP Chart */}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '7fr 5fr' }, gap: 2 }}>
            <TacticalPanel title="Target Information" icon={Activity} sx={{ minHeight: 400 }}>
               <Box sx={{ p: 2 }}>
                 <Tabs value={infoTab} onChange={(_, v) => setInfoTab(v)} sx={{ mb: 2, borderBottom: '1px solid rgba(255,255,255,0.05)', minHeight: 32 }}>
                   {['Domain Info', 'Whois', 'DNS Records', 'Nameservers', 'History'].map((l) => (
                     <Tab key={l} label={l} sx={{ fontSize: '0.65rem', fontWeight: 900, minHeight: 32, p: 1, color: 'rgba(255,255,255,0.4)', '&.Mui-selected': { color: '#00f3ff' } }} />
                   ))}
                 </Tabs>
                 
                 {infoTab === 0 && (
                   <Grid container spacing={3}>
                     <Grid item xs={4}><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Domain</Typography><Typography sx={{ fontSize: '0.8rem', fontWeight: 700, color: '#ff003c' }}>{data.target_info.name}</Typography></Grid>
                     <Grid item xs={4}><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Dnssec</Typography><Typography sx={{ fontSize: '0.8rem', fontWeight: 700 }}>{data.domain_info?.dnssec || 'N/A'}</Typography></Grid>
                     <Grid item xs={4}><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Geolocation</Typography><Typography sx={{ fontSize: '0.8rem', fontWeight: 700 }}>{data.domain_info?.geolocation_iso || 'N/A'}</Typography></Grid>
                     <Grid item xs={4}><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Created</Typography><Typography sx={{ fontSize: '0.7rem' }}>{data.domain_info?.created || 'N/A'}</Typography></Grid>
                     <Grid item xs={4}><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Updated</Typography><Typography sx={{ fontSize: '0.7rem' }}>{data.domain_info?.updated || 'N/A'}</Typography></Grid>
                     <Grid item xs={4}><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Expires</Typography><Typography sx={{ fontSize: '0.7rem' }}>{data.domain_info?.expires || 'N/A'}</Typography></Grid>
                     <Grid item xs={12}><Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', mb: 0.5 }}>Registrar</Typography><Typography sx={{ fontSize: '0.75rem', fontWeight: 700, color: '#00f3ff' }}>{data.domain_info?.registrar?.name || 'N/A'}</Typography></Grid>
                   </Grid>
                 )}
                 {infoTab === 1 && <Typography sx={{ p: 2, fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)' }}>Loading WHOIS Data...</Typography>}
                 {infoTab === 2 && (
                   <Stack spacing={1}>
                     {data.domain_info?.dns_records?.map((r: any, idx: number) => (
                       <Stack key={idx} direction="row" spacing={1} alignItems="center">
                         <Chip label={r.type.toUpperCase()} size="small" sx={{ height: 16, fontSize: '0.55rem', fontWeight: 900, bgcolor: 'rgba(0,243,255,0.1)', color: '#00f3ff' }} />
                         <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)' }}>{r.name}</Typography>
                       </Stack>
                     ))}
                   </Stack>
                 )}
               </Box>
            </TacticalPanel>
            <TacticalPanel title="HTTP Status Breakdown" icon={Activity} sx={{ minHeight: 400 }}>
              <Box sx={{ p: 2, height: 350 }}>
                <Chart 
                  options={{
                    chart: { type: 'donut', background: 'transparent' },
                    theme: { mode: 'dark' },
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
          <TacticalPanel title="Geographical Distribution of Assets" icon={Globe}>
            <Box sx={{ p: 2 }}>
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '3fr 1fr' }, gap: 2 }}>
                <Box sx={{ height: 500, bgcolor: 'rgba(0,0,0,0.2)', borderRadius: 1 }}>
                  <GeoMap data={data.asset_countries || []} />
                </Box>
                <TableContainer sx={{ maxHeight: 500 }}>
                  <Table size="small">
                    <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
                      <TableRow>
                        <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem', fontWeight: 900 }}>COUNTRY</TableCell>
                        <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem', fontWeight: 900 }}>ASSETS</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.asset_countries?.map((c: any) => (
                        <TableRow key={c.iso} sx={{ '&:hover': { bgcolor: 'rgba(0,243,255,0.05)' } }}>
                          <TableCell sx={{ fontSize: '0.7rem', color: '#fff' }}>{c.name}</TableCell>
                          <TableCell sx={{ fontSize: '0.7rem', color: '#00f3ff', fontWeight: 700 }}>{c.count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            </Box>
          </TacticalPanel>

          {/* Vulnerability Widgets */}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '5fr 7fr' }, gap: 2 }}>
             <TacticalPanel title="Vulnerability Severity" icon={ShieldAlert}>
               <Box sx={{ p: 2, height: 350 }}>
                 <Chart 
                    options={{
                      chart: { type: 'pie', background: 'transparent' },
                      theme: { mode: 'dark' },
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
             <TacticalPanel title="Vulnerability Highlights" icon={Shield}>
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
              <TacticalPanel title="Most Common CVE IDs" icon={BarChart2} sx={{ height: 280 }}>
                <Box sx={{ p: 1, height: '100%' }}>
                  <Chart 
                    options={{
                      chart: { type: 'bar', toolbar: { show: false } },
                      plotOptions: { bar: { horizontal: true, borderRadius: 2 } },
                      xaxis: { categories: data.most_common_cve?.map((c: any) => c.name) },
                      colors: ['#ff003c']
                    }} 
                    series={[{ data: data.most_common_cve?.map((c: any) => c.nused) }]} 
                    type="bar" 
                    height="100%" 
                  />
                </Box>
              </TacticalPanel>
              <TacticalPanel title="Most Common CWE IDs" icon={BarChart2} sx={{ height: 280 }}>
                <Box sx={{ p: 1, height: '100%' }}>
                  <Chart 
                    options={{
                      chart: { type: 'bar', toolbar: { show: false } },
                      plotOptions: { bar: { horizontal: true, borderRadius: 2 } },
                      xaxis: { categories: data.most_common_cwe?.map((c: any) => c.name) },
                      colors: ['#ff9f00']
                    }} 
                    series={[{ data: data.most_common_cwe?.map((c: any) => c.nused) }]} 
                    type="bar" 
                    height="100%" 
                  />
                </Box>
              </TacticalPanel>
              <TacticalPanel title="Most Common Tags" icon={BarChart2} sx={{ height: 280 }}>
                <Box sx={{ p: 1, height: '100%' }}>
                  <Chart 
                    options={{
                      chart: { type: 'bar', toolbar: { show: false } },
                      plotOptions: { bar: { horizontal: true, borderRadius: 2 } },
                      xaxis: { categories: data.most_common_tags?.map((c: any) => c.name) },
                      colors: ['#00ff62']
                    }} 
                    series={[{ data: data.most_common_tags?.map((c: any) => c.nused) }]} 
                    type="bar" 
                    height="100%" 
                  />
                </Box>
              </TacticalPanel>
          </Box>

          {/* Footer Info Cards */}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr 1fr' }, gap: 2 }}>
              <TacticalPanel title="IP Addresses" icon={Database} sx={{ height: 300 }}>
                 <Box sx={{ p: 2 }}>
                   <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                     {data.domain_info?.historical_ips?.map((ip: any) => (
                       <Chip key={ip.ip} label={ip.ip} size="small" sx={{ mb: 1, bgcolor: 'rgba(0,243,255,0.1)', color: '#00f3ff', border: '1px solid rgba(0,243,255,0.2)' }} />
                     ))}
                   </Stack>
                 </Box>
              </TacticalPanel>
              <TacticalPanel title="Discovered Ports" icon={Server} sx={{ height: 300 }}>
                 <Box sx={{ p: 2 }}>
                   <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                     {data.discovered_ports?.map((p: any) => (
                       <Chip key={p.number} label={`${p.number}/${p.service_name}`} size="small" sx={{ mb: 1, bgcolor: 'rgba(112,0,255,0.1)', color: '#7000ff', border: '1px solid rgba(112,0,255,0.2)' }} />
                     ))}
                   </Stack>
                 </Box>
              </TacticalPanel>
              <TacticalPanel title="Technologies" icon={Cpu} sx={{ height: 300 }}>
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

  const renderSubdomains = () => (
    <TacticalPanel title="All Discovered Subdomains" icon={Globe}>
       <TableContainer>
         <Table size="small">
           <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
             <TableRow>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>SUBDOMAIN</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>STATUS</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>IP ADDRESS</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>TITLE</TableCell>
             </TableRow>
           </TableHead>
           <TableBody>
             {(data.subdomains || []).map((s: any, idx: number) => (
               <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.05)' } }}>
                 <TableCell sx={{ color: '#fff', fontWeight: 700, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{s.name}</TableCell>
                 <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Chip label={s.http_status || 'N/A'} size="small" sx={{ height: 20, fontSize: '0.6rem', bgcolor: s.http_status === 200 ? 'rgba(0,255,98,0.1)' : 'rgba(255,255,255,0.05)', color: s.http_status === 200 ? '#00ff62' : '#fff' }} />
                 </TableCell>
                 <TableCell sx={{ color: 'rgba(255,255,255,0.5)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{s.ip_address || 'N/A'}</TableCell>
                 <TableCell sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{s.page_title || 'N/A'}</TableCell>
               </TableRow>
             ))}
             {(!data.subdomains || data.subdomains.length === 0) && (
               <TableRow>
                 <TableCell colSpan={4} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO SUBDOMAINS FOUND</TableCell>
               </TableRow>
             )}
           </TableBody>
         </Table>
       </TableContainer>
    </TacticalPanel>
  );

  const renderEndpoints = () => (
    <TacticalPanel title="All Discovered Endpoints (URLs)" icon={LinkIcon}>
       <TableContainer>
         <Table size="small">
           <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
             <TableRow>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>URL</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>STATUS</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>CONTENT TYPE</TableCell>
             </TableRow>
           </TableHead>
           <TableBody>
             {(data.endpoints || []).map((e: any, idx: number) => (
               <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.05)' } }}>
                 <TableCell sx={{ color: '#fff', borderBottom: '1px solid rgba(255,255,255,0.05)', maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <code style={{ fontSize: '0.7rem' }}>{e.url}</code>
                 </TableCell>
                 <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <Chip label={e.http_status || 'N/A'} size="small" sx={{ height: 20, fontSize: '0.6rem', bgcolor: e.http_status === 200 ? 'rgba(0,255,98,0.1)' : 'rgba(255,255,255,0.05)', color: e.http_status === 200 ? '#00ff62' : '#fff' }} />
                 </TableCell>
                 <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{e.content_type || 'N/A'}</TableCell>
               </TableRow>
             ))}
             {(!data.endpoints || data.endpoints.length === 0) && (
               <TableRow>
                 <TableCell colSpan={3} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO ENDPOINTS FOUND</TableCell>
               </TableRow>
             )}
           </TableBody>
         </Table>
       </TableContainer>
    </TacticalPanel>
  );

  const renderVulnerabilities = () => (
    <TacticalPanel title="Security Vulnerabilities" icon={Shield}>
       <TableContainer>
         <Table size="small">
           <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
             <TableRow>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>VULNERABILITY</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>SEVERITY</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>DESCRIPTION</TableCell>
             </TableRow>
           </TableHead>
           <TableBody>
             {(data.vulnerabilities || []).map((v: any, idx: number) => {
               const severityColor = v.severity === 'critical' ? '#ff003c' : v.severity === 'high' ? '#ff8c00' : v.severity === 'medium' ? '#fffc00' : '#00f3ff';
               return (
                 <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'rgba(255, 0, 60, 0.05)' } }}>
                   <TableCell sx={{ color: '#fff', fontWeight: 700, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{v.name}</TableCell>
                   <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <Chip 
                        label={v.severity?.toUpperCase()} 
                        size="small" 
                        sx={{ height: 20, fontSize: '0.6rem', fontWeight: 900, bgcolor: `${severityColor}20`, color: severityColor, border: `1px solid ${severityColor}40` }} 
                      />
                   </TableCell>
                   <TableCell sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', borderBottom: '1px solid rgba(255,255,255,0.05)', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {v.description}
                   </TableCell>
                 </TableRow>
               );
             })}
             {(!data.vulnerabilities || data.vulnerabilities.length === 0) && (
               <TableRow>
                 <TableCell colSpan={3} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO VULNERABILITIES FOUND</TableCell>
               </TableRow>
             )}
           </TableBody>
         </Table>
       </TableContainer>
    </TacticalPanel>
  );

  const renderMonitoring = () => (
    <TacticalPanel title={`Monitoring Discoveries for ${data.target_info.name}`} icon={Eye}>
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
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
          <Typography variant="h5" sx={{ fontWeight: 900, fontFamily: 'Orbitron', color: '#fff', letterSpacing: 2 }}>TARGET SUMMARY</Typography>
          <Stack direction="row" spacing={1} sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)' }}>
            <span>Targets</span> / <span>Target Summary</span> / <span style={{ color: '#00f3ff' }}>{data.target_info.name}</span>
          </Stack>
        </Stack>
      </Box>

      {/* Main Tabs */}
      <Box sx={{ mb: 3, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ minHeight: 40, '& .MuiTabs-indicator': { bgcolor: '#00f3ff', height: 3 } }}>
          {['HOME', 'SUBDOMAINS', 'URLS', 'VULNERABILITIES', 'MONITORING'].map((label) => (
            <Tab key={label} label={label} sx={{ fontSize: '0.75rem', fontWeight: 900, minHeight: 40, color: 'rgba(255,255,255,0.4)', letterSpacing: 1.5, '&.Mui-selected': { color: '#00f3ff' } }} />
          ))}
        </Tabs>
      </Box>

      {/* Tab Content */}
      <Box sx={{ mt: 2 }}>
        {activeTab === 0 && renderHome()}
        {activeTab === 1 && renderSubdomains()}
        {activeTab === 2 && renderEndpoints()}
        {activeTab === 3 && renderVulnerabilities()}
        {activeTab === 4 && renderMonitoring()}
      </Box>
    </Box>
  );
};
