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
  ListItemIcon,
  LinearProgress
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
  History,
  Eye,
  Settings,
  Cpu as EngineIcon,
  Timer
} from 'lucide-react';
import { useScanSummary } from '../api';
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

export const ScanDetailPage = () => {
  const { projectSlug, scanId } = useParams({ strict: false });
  const { data, isLoading, error } = useScanSummary(projectSlug || 'default', parseInt(scanId || '0'));
  const [activeTab, setActiveTab] = useState(0);
  const theme = useTheme();

  if (isLoading) {
    return (
      <Box sx={{ height: '80vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3 }}>
        <CircularProgress size={60} thickness={2} sx={{ color: '#00f3ff' }} />
        <Typography sx={{ color: '#00f3ff', fontFamily: 'Orbitron', letterSpacing: 4, fontSize: '0.8rem' }}>
          BOOTING_SCAN_CORE...
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
          <TacticalPanel title="Scan Status" icon={Activity}>
             <Box sx={{ p: 2 }}>
               <Stack spacing={2}>
                 <Box>
                   <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', mb: 1, textTransform: 'uppercase' }}>Current Progress</Typography>
                   <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                     <Box sx={{ flexGrow: 1 }}>
                        <LinearProgress variant="determinate" value={data.scan_info.progress} sx={{ height: 8, borderRadius: 4, bgcolor: 'rgba(255,255,255,0.05)', '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff', boxShadow: '0 0 10px #00f3ff' } }} />
                     </Box>
                     <Typography sx={{ fontSize: '0.75rem', fontWeight: 900, color: '#00f3ff', fontFamily: 'Orbitron' }}>{data.scan_info.progress}%</Typography>
                   </Box>
                 </Box>
                 
                 <Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />

                 <Grid container spacing={2}>
                    <Grid item xs={6}>
                       <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', mb: 0.5 }}>ENGINE</Typography>
                       <Stack direction="row" spacing={1} alignItems="center">
                          <EngineIcon size={14} color="#00f3ff" />
                          <Typography sx={{ fontSize: '0.75rem', fontWeight: 800 }}>{data.scan_info.engine_name}</Typography>
                       </Stack>
                    </Grid>
                    <Grid item xs={6}>
                       <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', mb: 0.5 }}>DURATION</Typography>
                       <Stack direction="row" spacing={1} alignItems="center">
                          <Timer size={14} color="#fffc00" />
                          <Typography sx={{ fontSize: '0.75rem', fontWeight: 800 }}>{Math.floor(data.scan_info.duration / 60)}m {data.scan_info.duration % 60}s</Typography>
                       </Stack>
                    </Grid>
                 </Grid>
               </Stack>
             </Box>
          </TacticalPanel>

          <TacticalPanel title="Configurations" icon={Settings}>
             <Box sx={{ p: 2 }}>
               <Stack spacing={1.5}>
                 <Box>
                   <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', mb: 0.5 }}>STARTING PATH</Typography>
                   <Typography sx={{ fontSize: '0.7rem', fontWeight: 700, wordBreak: 'break-all' }}>{data.scan_info.cfg_starting_point_path || 'Not Defined'}</Typography>
                 </Box>
                 <Box>
                   <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', mb: 0.5 }}>IMPORTED SUBDOMAINS</Typography>
                   <Chip label={data.scan_info.cfg_imported_subdomains} size="small" sx={{ height: 20, fontSize: '0.65rem', bgcolor: 'rgba(0,243,255,0.1)', color: '#00f3ff' }} />
                 </Box>
                 <Box>
                   <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', mb: 0.5 }}>EXCLUDED PATHS</Typography>
                   <Chip label={data.scan_info.cfg_excluded_paths} size="small" sx={{ height: 20, fontSize: '0.65rem', bgcolor: 'rgba(255,0,60,0.1)', color: '#ff003c' }} />
                 </Box>
               </Stack>
             </Box>
          </TacticalPanel>

          <TacticalPanel title="Scan Activity Logs" icon={Terminal}>
             <Box sx={{ p: 2, maxHeight: 400, overflow: 'auto' }}>
               <Stack spacing={2}>
                 {data.timeline?.map((item: any, idx: number) => (
                   <Box key={idx} sx={{ position: 'relative', pl: 2, borderLeft: '1px solid rgba(0, 243, 255, 0.2)' }}>
                     <Box sx={{ position: 'absolute', left: -4, top: 0, width: 7, height: 7, borderRadius: '50%', bgcolor: item.status === 'SUCCESS' ? '#00ff62' : '#00f3ff' }} />
                     <Typography sx={{ fontSize: '0.7rem', fontWeight: 800, color: '#fff' }}>{item.title}</Typography>
                     <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>{new Date(item.time).toLocaleTimeString()}</Typography>
                   </Box>
                 ))}
                 {(!data.timeline || data.timeline.length === 0) && (
                   <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.2)', textAlign: 'center', py: 4 }}>NO ACTIVITY LOGS RECORDED</Typography>
                 )}
               </Stack>
             </Box>
          </TacticalPanel>
        </Box>

        {/* COLUMN 2: MAIN CONTENT */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* TOP KPIs ROW */}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', lg: '1fr 1fr 1fr 1fr' }, gap: 2 }}>
            <KPICard title="Subdomains Found" value={data.subdomain_count} subValue={`Alive: ${data.alive_count}`} color="#00f3ff" info="Subdomains identified in this scan." />
            <KPICard title="Endpoints Found" value={data.endpoint_count} subValue={`Alive: ${data.endpoint_alive_count}`} color="#00f3ff" info="Endpoints discovered in this scan." />
            <KPICard title="Vulnerabilities" value={data.vulnerability_count} subValue={`${data.critical_count} Critical`} color="#ff003c" info="Vulnerabilities detected in this scan." />
            <KPICard title="Total Assets" value={data.subdomain_count + data.endpoint_count} color="#fffc00" info="Total unique assets identified." />
          </Box>

          {/* MIDDLE ROW: Charts */}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '7fr 5fr' }, gap: 2 }}>
            <TacticalPanel title="Vulnerability Breakdown" icon={ShieldAlert}>
               <Box sx={{ p: 2, height: 350 }}>
                 <Chart 
                    options={{
                      chart: { type: 'bar', background: 'transparent', toolbar: { show: false } },
                      theme: { mode: 'dark' },
                      plotOptions: { bar: { columnWidth: '45%', borderRadius: 4 } },
                      xaxis: { categories: ['Critical', 'High', 'Medium', 'Low', 'Info'] },
                      colors: ['#ff003c', '#ff9f00', '#fffc00', '#00ff62', '#00f3ff'],
                      grid: { borderColor: 'rgba(255,255,255,0.05)' }
                    }}
                    series={[{ name: 'Findings', data: [data.critical_count, data.high_count, data.medium_count, data.low_count, data.info_count] }]}
                    type="bar"
                    height="100%"
                 />
               </Box>
            </TacticalPanel>
            <TacticalPanel title="HTTP Status Distribution" icon={Activity}>
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
          <TacticalPanel title="Geographical Asset Distribution" icon={Globe}>
            <Box sx={{ p: 1 }}>
              <GeoMap data={data.asset_countries || []} disableCard={true} />
            </Box>
          </TacticalPanel>

          {/* Vulnerability Highlights */}
          <TacticalPanel title="Latest Vulnerability Findings" icon={Shield}>
             <TableContainer>
               <Table size="small">
                 <TableHead>
                   <TableRow>
                     <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem' }}>NAME</TableCell>
                     <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem' }}>SEVERITY</TableCell>
                     <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem' }}>DISCOVERED</TableCell>
                   </TableRow>
                 </TableHead>
                 <TableBody>
                   {data.vulnerability_highlights?.map((v: any, idx: number) => (
                     <TableRow key={idx}>
                       <TableCell sx={{ fontSize: '0.7rem', color: '#fff' }}>{v.name}</TableCell>
                       <TableCell><SeverityBadge severity={v.severity} /></TableCell>
                       <TableCell sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>{new Date(v.discovered_date).toLocaleDateString()}</TableCell>
                     </TableRow>
                   ))}
                   {(!data.vulnerability_highlights || data.vulnerability_highlights.length === 0) && (
                      <TableRow>
                        <TableCell colSpan={3} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO VULNERABILITIES DISCOVERED</TableCell>
                      </TableRow>
                   )}
                 </TableBody>
               </Table>
             </TableContainer>
          </TacticalPanel>

          {/* Footer Info Cards */}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr 1fr' }, gap: 2 }}>
              <TacticalPanel title="Target IPs" icon={Database} sx={{ height: 300 }}>
                 <Box sx={{ p: 2 }}>
                   <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                     {data.domain_info?.historical_ips?.map((ip: any) => (
                       <Chip key={ip.ip} label={ip.ip} size="small" sx={{ mb: 1, bgcolor: 'rgba(0,243,255,0.1)', color: '#00f3ff' }} />
                     ))}
                   </Stack>
                 </Box>
              </TacticalPanel>
              <TacticalPanel title="Service Ports" icon={Server} sx={{ height: 300 }}>
                 <Box sx={{ p: 2 }}>
                   <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                     {data.discovered_ports?.map((p: any) => (
                       <Chip key={p.number} label={`${p.number}/${p.service_name}`} size="small" sx={{ mb: 1, bgcolor: 'rgba(112,0,255,0.1)', color: '#7000ff' }} />
                     ))}
                   </Stack>
                 </Box>
              </TacticalPanel>
              <TacticalPanel title="Tech Stack" icon={Cpu} sx={{ height: 300 }}>
                 <Box sx={{ p: 2 }}>
                   <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                     {data.discovered_technologies?.map((t: any) => (
                       <Chip key={t.name} label={t.name} size="small" sx={{ mb: 1, bgcolor: 'rgba(255,252,0,0.1)', color: '#fffc00' }} />
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
    <TacticalPanel title="Discovered Subdomains" icon={Globe}>
       <TableContainer>
         <Table size="small">
           <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
             <TableRow>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>SUBDOMAIN</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>STATUS</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>TITLE</TableCell>
             </TableRow>
           </TableHead>
           <TableBody>
             {(data.subdomains || []).map((s: any, idx: number) => (
               <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.05)' } }}>
                 <TableCell sx={{ color: '#fff', fontWeight: 700 }}>{s.name}</TableCell>
                 <TableCell>
                    <Chip label={s.http_status || 'N/A'} size="small" sx={{ height: 20, fontSize: '0.6rem', bgcolor: s.http_status === 200 ? 'rgba(0,255,98,0.1)' : 'rgba(255,255,255,0.05)', color: s.http_status === 200 ? '#00ff62' : '#fff' }} />
                 </TableCell>
                 <TableCell sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>{s.page_title || 'N/A'}</TableCell>
               </TableRow>
             ))}
           </TableBody>
         </Table>
       </TableContainer>
    </TacticalPanel>
  );

  const renderEndpoints = () => (
    <TacticalPanel title="Discovered Endpoints" icon={LinkIcon}>
       <TableContainer>
         <Table size="small">
           <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
             <TableRow>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>URL</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>STATUS</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>TYPE</TableCell>
             </TableRow>
           </TableHead>
           <TableBody>
             {(data.endpoints || []).map((e: any, idx: number) => (
               <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.05)' } }}>
                 <TableCell sx={{ color: '#fff', maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <code style={{ fontSize: '0.7rem' }}>{e.url}</code>
                 </TableCell>
                 <TableCell>
                    <Chip label={e.http_status || 'N/A'} size="small" sx={{ height: 20, fontSize: '0.6rem', bgcolor: e.http_status === 200 ? 'rgba(0,255,98,0.1)' : 'rgba(255,255,255,0.05)', color: e.http_status === 200 ? '#00ff62' : '#fff' }} />
                 </TableCell>
                 <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>{e.content_type || 'N/A'}</TableCell>
               </TableRow>
             ))}
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
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>VULNERABILITY</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>SEVERITY</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>DESCRIPTION</TableCell>
             </TableRow>
           </TableHead>
           <TableBody>
             {(data.vulnerabilities || []).map((v: any, idx: number) => (
                <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'rgba(255, 0, 60, 0.05)' } }}>
                  <TableCell sx={{ color: '#fff', fontWeight: 700 }}>{v.name}</TableCell>
                  <TableCell><SeverityBadge severity={v.severity} /></TableCell>
                  <TableCell sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>{v.description}</TableCell>
                </TableRow>
             ))}
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
          <Typography variant="h5" sx={{ fontWeight: 900, fontFamily: 'Orbitron', color: '#fff', letterSpacing: 2 }}>SCAN DETAILS</Typography>
          <Stack direction="row" spacing={1} sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)' }}>
            <span>Scans</span> / <span>Detail</span> / <span style={{ color: '#00f3ff' }}>{data.target_info.name}</span>
          </Stack>
        </Stack>
      </Box>

      {/* Main Tabs */}
      <Box sx={{ mb: 3, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ minHeight: 40, '& .MuiTabs-indicator': { bgcolor: '#00f3ff', height: 3 } }}>
          {['HOME', 'SUBDOMAINS', 'URLS', 'VULNERABILITIES'].map((label) => (
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
      </Box>
    </Box>
  );
};
