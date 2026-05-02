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
  Timer,
  Settings,
  Camera,
  Folder,
  Eye,
  Mail,
  Users,
  Key
} from 'lucide-react';
import { useScanSummary } from '../api';
import Chart from 'react-apexcharts';
import { GeoMap } from '../../dashboard/components/GeoMap';
import { KpiCard } from '../../../components/KpiCard';
import { TacticalPanel } from '../../../components/TacticalPanel';

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

const StatusBadge: React.FC<{ status: number }> = ({ status }) => {
  const configs: any = {
    [-1]: { label: 'PENDING', color: '#ff9f00', icon: Clock },
    [0]: { label: 'FAILED', color: '#ff003c', icon: AlertTriangle },
    [1]: { label: 'RUNNING', color: '#00f3ff', icon: Activity },
    [2]: { label: 'COMPLETED', color: '#00ff62', icon: Shield },
    [3]: { label: 'ABORTED', color: '#ff003c', icon: AlertTriangle },
  };
  const config = configs[status] || { label: 'UNKNOWN', color: '#fff', icon: Info };
  const Icon = config.icon;
  
  return (
    <Box sx={{ 
      display: 'inline-flex', 
      alignItems: 'center',
      gap: 1,
      px: 3, 
      py: 1, 
      borderRadius: '20px', 
      bgcolor: 'transparent', 
      border: `1px solid ${config.color}40`,
      color: config.color,
      fontSize: '0.9rem',
      fontWeight: 900,
      fontFamily: 'Orbitron',
      textShadow: `0 0 10px ${config.color}40`,
      boxShadow: `inset 0 0 10px ${config.color}10`
    }}>
      <Icon size={18} />
      {config.label}
    </Box>
  );
};

const TimelineItem: React.FC<{ activity: any }> = ({ activity }) => {
  const statusConfig: any = {
    'SUCCESS': { color: '#00ff62', label: 'Completed' },
    'RUNNING': { color: '#00f3ff', label: 'In Progress' },
    'FAILED': { color: '#ff003c', label: 'Failed' },
    'ABORTED': { color: '#ff003c', label: 'Aborted' },
    'PENDING': { color: '#ff9f00', label: 'Pending' }
  };
  const config = statusConfig[activity.status] || { color: '#fff', label: activity.status };

  return (
    <Box sx={{ position: 'relative', pl: 5, pb: 4, '&:last-child': { pb: 0 } }}>
      {/* Vertical Line */}
      <Box sx={{ 
        position: 'absolute', 
        left: 6, 
        top: 10, 
        bottom: -4, 
        width: 2, 
        bgcolor: 'rgba(255,255,255,0.05)',
        zIndex: 1
      }} />
      
      {/* Dot - Ring Style */}
      <Box sx={{ 
        position: 'absolute', 
        left: 0, 
        top: 4, 
        width: 14, 
        height: 14, 
        borderRadius: '50%', 
        border: `2px solid ${config.color}`,
        bgcolor: 'transparent',
        boxShadow: activity.status === 'RUNNING' ? `0 0 10px ${config.color}` : 'none',
        zIndex: 2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        {activity.status === 'RUNNING' && (
          <Box sx={{ 
            width: 4, 
            height: 4, 
            borderRadius: '50%', 
            bgcolor: config.color,
            animation: 'pulse 1.5s infinite' 
          }} />
        )}
      </Box>

      <Stack spacing={0.5}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <Typography sx={{ fontSize: '0.85rem', fontWeight: 800, color: '#fff' }}>
            {activity.title}
          </Typography>
          <Box sx={{ 
            px: 1, 
            py: 0.1, 
            borderRadius: 1, 
            bgcolor: 'rgba(0,255,98,0.1)', 
            border: '1px solid rgba(0,255,98,0.2)',
            color: '#00ff62',
            fontSize: '0.6rem',
            fontWeight: 800
          }}>
            {config.label}
          </Box>
        </Stack>
        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)', fontWeight: 600 }}>
          {new Date(activity.time).toLocaleString()}
        </Typography>
        {activity.error_message && (
          <Typography sx={{ fontSize: '0.65rem', color: '#ff003c', bgcolor: 'rgba(255,0,60,0.1)', p: 1, borderRadius: 0.5, border: '1px solid rgba(255,0,60,0.2)', mt: 1 }}>
            ERROR: {activity.error_message}
          </Typography>
        )}
      </Stack>
    </Box>
  );
};

const SubScanWidget: React.FC<{ subscans: any[] }> = ({ subscans }) => {
  return (
    <Stack spacing={1.5}>
      {subscans?.map((sub: any) => (
        <Box key={sub.id} sx={{ p: 1.5, borderRadius: 1, bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
           <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography sx={{ fontSize: '0.7rem', fontWeight: 900, color: '#00f3ff' }}>{sub.engine_name}</Typography>
              <StatusBadge status={sub.status} />
           </Stack>
           <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
              STARTED: {new Date(sub.start_scan_date).toLocaleString()}
           </Typography>
        </Box>
      ))}
      {(!subscans || subscans.length === 0) && (
        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.2)', textAlign: 'center', py: 2 }}>NO SUB SCANS FOUND</Typography>
      )}
    </Stack>
  );
};

const MostCommonVulns: React.FC<{ vulns: any[] }> = ({ vulns }) => (
  <TacticalPanel title="Most Common Vulnerabilities" icon={<ShieldAlert size={14} />}>
    <Stack spacing={1.5}>
      {vulns?.slice(0, 5).map((v: any, idx: number) => (
        <Box key={idx} sx={{ p: 1.5, borderRadius: 1, bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)', transition: 'all 0.2s', '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' } }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography sx={{ fontSize: '0.75rem', fontWeight: 800, color: '#fff' }}>{v.name}</Typography>
            <SeverityBadge severity={v.severity} />
          </Stack>
          <Typography sx={{ fontSize: '0.7rem', color: '#00f3ff', fontWeight: 900, mt: 0.5, fontFamily: 'Orbitron' }}>{v.count} OCCURRENCES</Typography>
        </Box>
      ))}
      {(!vulns || vulns.length === 0) && (
        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.2)', textAlign: 'center', py: 4 }}>NO COMMON VULNERABILITIES</Typography>
      )}
    </Stack>
  </TacticalPanel>
);

const ReconNotes: React.FC<{ notes: any[] }> = ({ notes }) => (
  <TacticalPanel title="Recon Notes / Tasks" icon={<FileText size={14} />}>
    <Stack spacing={1.5}>
      {notes?.map((n: any) => (
        <Box key={n.id} sx={{ p: 1.5, borderRadius: 1, bgcolor: n.is_done ? 'rgba(0,255,98,0.02)' : 'rgba(255,255,255,0.03)', border: `1px solid ${n.is_important ? 'rgba(255,159,0,0.3)' : 'rgba(255,255,255,0.05)'}` }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
             <Typography sx={{ fontSize: '0.75rem', fontWeight: 800, color: n.is_done ? 'rgba(255,255,255,0.4)' : '#fff', textDecoration: n.is_done ? 'line-through' : 'none' }}>{n.title}</Typography>
             {n.is_important && <Chip label="IMPORTANT" size="small" sx={{ height: 16, fontSize: '0.5rem', bgcolor: 'rgba(255,159,0,0.1)', color: '#ff9f00' }} />}
          </Stack>
          <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', mt: 0.5 }}>{n.description}</Typography>
        </Box>
      ))}
      {(!notes || notes.length === 0) && (
        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.2)', textAlign: 'center', py: 4 }}>NO RECON NOTES FOUND</Typography>
      )}
    </Stack>
  </TacticalPanel>
);

const VulnHighlights: React.FC<{ highlights: any[] }> = ({ highlights }) => (
  <TacticalPanel title="Vulnerability Highlights" icon={<ShieldAlert size={14} />}>
    <Stack spacing={1.5}>
      {highlights?.slice(0, 5).map((v: any, idx: number) => (
        <Box key={idx} sx={{ p: 1.5, borderRadius: 1, bgcolor: 'rgba(255,0,60,0.02)', border: '1px solid rgba(255,0,60,0.1)', transition: 'all 0.2s', '&:hover': { bgcolor: 'rgba(255,0,60,0.04)' } }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography sx={{ fontSize: '0.75rem', fontWeight: 800, color: '#fff' }}>{v.name}</Typography>
            <SeverityBadge severity={v.severity} />
          </Stack>
          <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', mt: 0.5, wordBreak: 'break-all', fontFamily: 'monospace' }}>{v.http_url}</Typography>
        </Box>
      ))}
      {(!highlights || highlights.length === 0) && (
        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.2)', textAlign: 'center', py: 4 }}>NO VULNERABILITY HIGHLIGHTS</Typography>
      )}
    </Stack>
  </TacticalPanel>
);

export const ScanDetailPage = () => {
  const { projectSlug, scanId } = useParams({ from: '/$projectSlug/scan/detail/$scanId' });
  const { data, isLoading } = useScanSummary(projectSlug, parseInt(scanId));
  const [activeTab, setActiveTab] = useState(0);
  const [infoTab, setInfoTab] = useState(0);

  if (isLoading || !data) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress sx={{ color: '#00f3ff' }} />
      </Box>
    );
  }

  const tabs = [
    { label: 'HOME', icon: Activity },
    { label: 'SUBDOMAINS', icon: Globe },
    { label: 'BUCKETS', icon: Database, show: data.buckets_count > 0 },
    { label: 'SCREENSHOTS', icon: Camera, show: data.scan_info.tasks?.includes('screenshot') },
    { label: 'DIRECTORIES', icon: Folder, show: data.scan_info.tasks?.includes('dir_file_fuzz') },
    { label: 'URLS', icon: LinkIcon },
    { label: 'VULNERABILITIES', icon: ShieldAlert, show: data.vulnerability_count > 0 },
    { label: 'EXPLOITS', icon: Zap, show: data.exploitable_count > 0 },
    { label: 'OSINT', icon: Search, show: data.scan_info.tasks?.includes('osint') },
    { label: 'LEAKS', icon: Shield, show: data.secret_leaks_count > 0 },
    { label: 'RECON NOTES', icon: FileText },
    { label: 'VISUALIZATION', icon: BarChart2 },
  ].filter(t => t.show !== false);

  const renderSidebar = () => (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <TacticalPanel title="Scan Status" icon={<Activity size={14} />}>
         <Box sx={{ p: 2 }}>
           <Stack spacing={4}>
             <Box sx={{ textAlign: 'center' }}>
               <StatusBadge status={data.scan_info.scan_status} />
             </Box>
             
             <Box>
               <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', mb: 1.5, textTransform: 'uppercase', letterSpacing: 1.5, fontWeight: 700 }}>Current Progress</Typography>
               <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                 <Box sx={{ flexGrow: 1, position: 'relative' }}>
                    <LinearProgress 
                      variant="determinate" 
                      value={data.scan_info.scan_status === 2 ? 100 : data.scan_info.progress} 
                      sx={{ 
                        height: 6, 
                        borderRadius: 3, 
                        bgcolor: 'rgba(255,255,255,0.05)', 
                        '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff', boxShadow: '0 0 15px #00f3ff' } 
                      }} 
                    />
                 </Box>
                 <Typography sx={{ fontSize: '1rem', fontWeight: 900, color: '#00f3ff', fontFamily: 'Orbitron' }}>
                    {data.scan_info.scan_status === 2 ? '100' : data.scan_info.progress}%
                 </Typography>
               </Box>
             </Box>
             
             <Box sx={{ height: '1px', bgcolor: 'rgba(255,255,255,0.05)', mx: -2 }} />

             <Grid container spacing={3}>
                <Grid item xs={6}>
                   <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', mb: 1, fontWeight: 700 }}>ENGINE</Typography>
                   <Stack direction="row" spacing={1} alignItems="center">
                      <Cpu size={16} color="#00f3ff" />
                      <Typography sx={{ fontSize: '0.9rem', fontWeight: 800, color: '#fff' }}>{data.scan_info.engine_name}</Typography>
                   </Stack>
                </Grid>
                <Grid item xs={6}>
                   <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', mb: 1, fontWeight: 700 }}>DURATION</Typography>
                   <Stack direction="row" spacing={1} alignItems="center">
                      <Timer size={16} color="#fffc00" />
                      <Typography sx={{ fontSize: '0.9rem', fontWeight: 800, color: '#fff' }}>{Math.floor(data.scan_info.duration / 60)}m {data.scan_info.duration % 60}s</Typography>
                   </Stack>
                </Grid>
             </Grid>
           </Stack>
         </Box>
      </TacticalPanel>

      <TacticalPanel title="Configurations" icon={<Settings size={14} />}>
         <Box sx={{ p: 1 }}>
           <Stack spacing={1.5}>
             <Box>
               <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', mb: 0.5 }}>STARTING PATH</Typography>
               <Typography sx={{ fontSize: '0.7rem', fontWeight: 700, wordBreak: 'break-all', color: '#fff' }}>{data.scan_info.cfg_starting_point_path || '/'}</Typography>
             </Box>
             <Box>
               <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', mb: 0.5 }}>IMPORTED SUBDOMAINS</Typography>
               {data.scan_info.cfg_imported_subdomains?.length > 0 ? (
                 <Stack direction="row" spacing={0.5} flexWrap="wrap">
                   {data.scan_info.cfg_imported_subdomains.map((s: string) => <Chip key={s} label={s} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'rgba(0,243,255,0.1)', color: '#00f3ff', mb: 0.5 }} />)}
                 </Stack>
               ) : <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.2)' }}>None</Typography>}
             </Box>
             <Box>
               <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', mb: 0.5 }}>OUT OF SCOPE</Typography>
               {data.scan_info.cfg_out_of_scope_subdomains?.length > 0 ? (
                 <Stack direction="row" spacing={0.5} flexWrap="wrap">
                   {data.scan_info.cfg_out_of_scope_subdomains.map((s: string) => <Chip key={s} label={s} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'rgba(255,0,60,0.1)', color: '#ff003c', mb: 0.5 }} />)}
                 </Stack>
               ) : <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.2)' }}>None</Typography>}
             </Box>
           </Stack>
         </Box>
      </TacticalPanel>

      <TacticalPanel title="Timeline" icon={<History size={14} />}>
         <Box sx={{ p: 1, maxHeight: 400, overflow: 'auto' }}>
           <Stack>
             {data.timeline?.map((activity: any, idx: number) => (
               <TimelineItem key={idx} activity={activity} />
             ))}
             {(!data.timeline || data.timeline.length === 0) && (
               <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.2)', textAlign: 'center', py: 4 }}>NO ACTIVITY LOGS</Typography>
             )}
           </Stack>
         </Box>
      </TacticalPanel>

      <TacticalPanel title="Recent Scans" icon={<Activity size={14} />}>
         <Box sx={{ p: 1 }}>
           <Stack spacing={1}>
             {data.recent_scans?.map((scan: any) => (
               <Box 
                 key={scan.id} 
                 component={RouterLink}
                 to={`/${projectSlug}/scans/detail/${scan.id}`}
                 sx={{ 
                   p: 1.5, 
                   borderRadius: 1, 
                   bgcolor: scan.id === parseInt(scanId || '0') ? 'rgba(0, 243, 255, 0.05)' : 'transparent',
                   border: `1px solid ${scan.id === parseInt(scanId || '0') ? 'rgba(0, 243, 255, 0.2)' : 'rgba(255,255,255,0.05)'}`,
                   textDecoration: 'none',
                   transition: 'all 0.2s',
                   '&:hover': { bgcolor: 'rgba(255,255,255,0.03)', borderColor: 'rgba(255,255,255,0.1)' }
                 }}
               >
                 <Stack direction="row" justifyContent="space-between" alignItems="center">
                   <Typography sx={{ fontSize: '0.7rem', fontWeight: 800, color: '#fff' }}>{scan.engine_name}</Typography>
                   <SeverityBadge severity={scan.highest_severity === 'critical' ? 4 : scan.highest_severity === 'high' ? 3 : 0} />
                 </Stack>
                 <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', mt: 0.5 }}>{scan.completed_ago}</Typography>
               </Box>
             ))}
           </Stack>
         </Box>
      </TacticalPanel>

      <TacticalPanel title="Sub Scan History" icon={<Activity size={14} />}>
         <Box sx={{ p: 1 }}>
            <SubScanWidget subscans={data.subscans} />
         </Box>
      </TacticalPanel>
    </Box>
  );

  const renderHomeContent = () => (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Row 1: Squares (Widgets) */}
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
           <Box sx={{ height: '400px' }}>
              <MostCommonVulns vulns={data.most_common_vulnerability} />
           </Box>
        </Grid>
        <Grid item xs={12} md={4}>
           <Box sx={{ height: '400px' }}>
              <VulnHighlights highlights={data.vulnerability_highlights} />
           </Box>
        </Grid>
        <Grid item xs={12} md={4}>
           <Box sx={{ height: '400px' }}>
              <ReconNotes notes={data.todo_notes} />
           </Box>
        </Grid>
      </Grid>

      {/* Row 2: Target Information and HTTP Status Charts */}
      <Grid container spacing={2}>
        <Grid item xs={12} md={8}>
          <TacticalPanel title="Target Information" icon={<Activity size={14} />}>
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
               {infoTab === 1 && (
                 <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                   <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.7)', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                     {data.domain_info?.whois_data || 'No WHOIS data available.'}
                   </Typography>
                 </Box>
               )}
               {infoTab === 2 && (
                 <Stack spacing={1}>
                   {data.domain_info?.dns_records?.map((r: any, idx: number) => (
                     <Stack key={idx} direction="row" spacing={1} alignItems="center">
                       <Chip label={r.type.toUpperCase()} size="small" sx={{ height: 16, fontSize: '0.55rem', fontWeight: 900, bgcolor: 'rgba(0,243,255,0.1)', color: '#00f3ff' }} />
                       <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)' }}>{r.name} {"->"} {r.value}</Typography>
                     </Stack>
                   ))}
                 </Stack>
               )}
               {infoTab === 3 && (
                 <Stack spacing={1}>
                   {data.domain_info?.nameservers?.map((ns: string, idx: number) => (
                     <Stack key={idx} direction="row" spacing={1} alignItems="center">
                       <Globe size={14} color="#00f3ff" />
                       <Typography sx={{ fontSize: '0.7rem', color: '#fff' }}>{ns}</Typography>
                     </Stack>
                   ))}
                 </Stack>
               )}
             </Box>
          </TacticalPanel>
        </Grid>
        <Grid item xs={12} md={4}>
           <TacticalPanel title="HTTP Status Breakdown" icon={<Activity size={14} />}>
             <Box sx={{ p: 2, height: '100%', minHeight: 300 }}>
               <Chart 
                 options={{
                   chart: { type: 'donut', background: 'transparent' },
                   theme: { mode: 'dark' },
                   stroke: { show: false },
                   dataLabels: { enabled: false },
                   legend: { position: 'bottom', fontSize: '10px', labels: { colors: 'rgba(255,255,255,0.7)' } },
                   colors: ['#00ff62', '#ff003c', '#00f3ff', '#7000ff', '#fffc00']
                 }} 
                 series={data.http_status_breakdown.map((s: any) => s.count)} 
                 type="donut" 
                 height={300} 
               />
             </Box>
           </TacticalPanel>
        </Grid>
      </Grid>

      {/* Row 3: GeoMap */}
      <TacticalPanel title="Geographical Distribution" icon={<Globe size={14} />}>
        <Box sx={{ p: 0 }}>
          <GeoMap data={data.asset_countries || []} disableCard={true} />
        </Box>
      </TacticalPanel>
    </Box>
  );
  const renderBuckets = () => (
    <TacticalPanel title="S3 Buckets Discovered" icon={<Database size={14} />}>
       <TableContainer>
         <Table size="small">
           <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
             <TableRow>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>BUCKET NAME</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>PUBLIC READ</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>PUBLIC WRITE</TableCell>
             </TableRow>
           </TableHead>
           <TableBody>
             {(data.buckets || []).map((b: any, idx: number) => (
               <TableRow key={idx}>
                 <TableCell sx={{ color: '#fff', fontWeight: 700 }}>{b.name}</TableCell>
                 <TableCell>
                    <Chip label={b.public_read ? 'YES' : 'NO'} size="small" color={b.public_read ? 'error' : 'default'} />
                 </TableCell>
                 <TableCell>
                    <Chip label={b.public_write ? 'YES' : 'NO'} size="small" color={b.public_write ? 'error' : 'default'} />
                 </TableCell>
               </TableRow>
             ))}
             {(!data.buckets || data.buckets.length === 0) && (
               <TableRow>
                 <TableCell colSpan={3} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO BUCKETS FOUND</TableCell>
               </TableRow>
             )}
           </TableBody>
         </Table>
       </TableContainer>
    </TacticalPanel>
  );

  const renderOSINT = () => (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
         <TacticalPanel title="Employees/People Found" icon={<Users size={14} />}>
            <TableContainer>
              <Table size="small">
                <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
                  <TableRow>
                    <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>NAME</TableCell>
                    <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>DESIGNATION</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                   {/* This would be populated from data.employees if available */}
                   <TableRow>
                     <TableCell colSpan={2} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO EMPLOYEE DATA FOUND</TableCell>
                   </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
         </TacticalPanel>
         <TacticalPanel title="Discovered Email Addresses" icon={<Mail size={14} />}>
            <TableContainer>
              <Table size="small">
                <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
                  <TableRow>
                    <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>EMAIL</TableCell>
                    <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>EXPOSED</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                   {/* This would be populated from data.emails if available */}
                   <TableRow>
                     <TableCell colSpan={2} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO EMAIL DATA FOUND</TableCell>
                   </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
         </TacticalPanel>
      </Box>
      <TacticalPanel title="Dorking Results" icon={<Search size={14} />}>
         <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography sx={{ color: 'rgba(255,255,255,0.2)' }}>OSINT MODULE DATA COMING SOON</Typography>
         </Box>
      </TacticalPanel>
    </Box>
  );

  const renderLeaks = () => (
    <TacticalPanel title="Credential & Leak Intelligence" icon={<Shield size={14} />}>
       <TableContainer>
         <Table size="small">
           <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
             <TableRow>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>TOOL</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>TYPE</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>SOURCE</TableCell>
               <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>MATCH</TableCell>
             </TableRow>
           </TableHead>
           <TableBody>
              {/* Leaks data mapping would go here */}
              <TableRow>
                 <TableCell colSpan={4} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO SECRETS OR LEAKS DETECTED</TableCell>
              </TableRow>
           </TableBody>
         </Table>
       </TableContainer>
    </TacticalPanel>
  );

  const renderExploits = () => (
    <TacticalPanel title="Potential Exploits & Payloads" icon={<Zap size={14} />}>
       <TableContainer>
         <Table size="small">
           <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
             <TableRow>
               <TableCell sx={{ color: '#fffc00', fontWeight: 900 }}>TARGET</TableCell>
               <TableCell sx={{ color: '#fffc00', fontWeight: 900 }}>EXPLOIT TYPE</TableCell>
               <TableCell sx={{ color: '#fffc00', fontWeight: 900 }}>PAYLOAD</TableCell>
             </TableRow>
           </TableHead>
           <TableBody>
              <TableRow>
                 <TableCell colSpan={3} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO POTENTIAL EXPLOITS IDENTIFIED</TableCell>
              </TableRow>
           </TableBody>
         </Table>
       </TableContainer>
    </TacticalPanel>
  );

  const renderSubdomains = () => (
    <TacticalPanel title="Discovered Subdomains" icon={<Globe size={14} />}>
      <TableContainer>
        <Table size="small">
          <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
            <TableRow>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>SUBDOMAIN</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>IP ADDRESS</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>STATUS</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>PORT</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data.subdomains || []).map((s: any, idx: number) => (
              <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' } }}>
                <TableCell sx={{ color: '#fff', fontWeight: 700 }}>{s.name}</TableCell>
                <TableCell sx={{ color: 'rgba(255,255,255,0.7)', fontFamily: 'monospace' }}>{s.ip || 'N/A'}</TableCell>
                <TableCell>
                  <Chip 
                    label={s.http_status || '200'} 
                    size="small" 
                    sx={{ 
                      height: 20, 
                      fontSize: '0.65rem', 
                      bgcolor: (s.http_status >= 400) ? 'rgba(255,0,60,0.1)' : 'rgba(0,255,98,0.1)',
                      color: (s.http_status >= 400) ? '#ff003c' : '#00ff62'
                    }} 
                  />
                </TableCell>
                <TableCell sx={{ color: 'rgba(255,255,255,0.5)' }}>{s.port || '80'}</TableCell>
              </TableRow>
            ))}
            {(!data.subdomains || data.subdomains.length === 0) && (
              <TableRow>
                <TableCell colSpan={4} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO SUBDOMAINS DISCOVERED</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </TacticalPanel>
  );

  const renderEndpoints = () => (
    <TacticalPanel title="Discovered Endpoints" icon={<LinkIcon size={14} />}>
      <TableContainer>
        <Table size="small">
          <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
            <TableRow>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>URL / ENDPOINT</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>STATUS</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>TECH</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data.endpoints || []).map((e: any, idx: number) => (
              <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' } }}>
                <TableCell sx={{ color: '#fff', fontWeight: 600, wordBreak: 'break-all' }}>{e.http_url}</TableCell>
                <TableCell>
                  <Chip label={e.status_code || '200'} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.6rem' }} />
                </TableCell>
                <TableCell>
                   <Stack direction="row" spacing={0.5}>
                     {e.technologies?.slice(0, 2).map((t: string) => (
                       <Chip key={t} label={t} size="small" sx={{ height: 16, fontSize: '0.55rem', bgcolor: 'rgba(255,255,255,0.05)' }} />
                     ))}
                   </Stack>
                </TableCell>
              </TableRow>
            ))}
            {(!data.endpoints || data.endpoints.length === 0) && (
              <TableRow>
                <TableCell colSpan={3} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO ENDPOINTS DISCOVERED</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </TacticalPanel>
  );

  const renderVulnerabilities = () => (
    <TacticalPanel title="Security Vulnerabilities" icon={<ShieldAlert size={14} />}>
      <TableContainer>
        <Table size="small">
          <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
            <TableRow>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>VULNERABILITY</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>SEVERITY</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 900 }}>TARGET</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data.vulnerabilities || []).map((v: any, idx: number) => (
              <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' } }}>
                <TableCell sx={{ color: '#fff', fontWeight: 700 }}>{v.name}</TableCell>
                <TableCell>
                  <SeverityBadge severity={v.severity} />
                </TableCell>
                <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>{v.http_url}</TableCell>
              </TableRow>
            ))}
            {(!data.vulnerabilities || data.vulnerabilities.length === 0) && (
              <TableRow>
                <TableCell colSpan={3} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO VULNERABILITIES DETECTED</TableCell>
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
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 900, fontFamily: 'Orbitron', color: '#fff', letterSpacing: 2 }}>SCAN_DETAIL</Typography>
            <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', fontWeight: 600 }}>IDENTIFIER: {scanId} | TARGET: {data.target_info.name}</Typography>
          </Box>
          <Stack direction="row" spacing={1} sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>
            <span>SCANS</span> / <span>DETAIL</span> / <span style={{ color: '#00f3ff' }}>{data.target_info.name}</span>
          </Stack>
        </Stack>
      </Box>

      {/* Tab Bar Integration - Now spanning full width at the top */}
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
                <Stack direction="row" spacing={1} alignItems="center">
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

      {/* MAIN TWO-COLUMN LAYOUT (Sidebar Left, Content Right) */}
      <Box sx={{ display: 'flex', gap: 3, alignItems: 'flex-start', flexWrap: { xs: 'wrap', lg: 'nowrap' } }}>
        
        {/* LEFT COLUMN: Scan Metadata & Timeline */}
        <Box sx={{ width: { xs: '100%', lg: '320px' }, flexShrink: 0, position: { lg: 'sticky' }, top: 70 }}>
           <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
             {renderSidebar()}
           </Box>
        </Box>

        {/* RIGHT COLUMN: Discovery Content */}
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          {/* Tab Content Display */}
          <Box sx={{ minHeight: '60vh' }}>
            {tabs[activeTab]?.label === 'HOME' ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                
                {/* Top Row: Discovery Metrics (The 4 KPIs) - Compact Squares */}
                <Box sx={{ 
                  display: 'grid', 
                  gridTemplateColumns: { 
                    xs: 'repeat(2, 1fr)', 
                    md: 'repeat(4, 1fr)' 
                  }, 
                  gap: 2,
                  maxWidth: 900 // Constrain the total width to keep squares reasonably sized
                }}>
                   <KpiCard 
                     title="SUBDOMAINS" 
                     value={data.subdomain_count} 
                     subtitle={`${data.alive_count} ACTIVE`} 
                     color="#7000ff"
                     icon={Layers}
                     sx={{ aspectRatio: '1/1', height: '100%' }}
                   />
                   <KpiCard 
                     title="ENDPOINTS" 
                     value={data.endpoint_count} 
                     subtitle={`${data.endpoint_alive_count} ALIVE`} 
                     color="#ff00f7"
                     icon={Target}
                     sx={{ aspectRatio: '1/1', height: '100%' }}
                   />
                   <KpiCard 
                     title="VULNS" 
                     value={data.vulnerability_count} 
                     subtitle={`${data.critical_count} CRITICAL`} 
                     color="#ff003c"
                     icon={ShieldAlert}
                     sx={{ aspectRatio: '1/1', height: '100%' }}
                   />
                   <KpiCard 
                     title="OSINT" 
                     value={data.secret_leaks_count} 
                     subtitle="SENSITIVE DATA" 
                     color="#fffc00"
                     icon={Key}
                     sx={{ aspectRatio: '1/1', height: '100%' }}
                   />
                </Box>

                {/* Discovery Modules (Target Info, etc.) */}
                {renderHomeContent()}
              </Box>
            ) : (
              /* Discovery-Specific Tab Content */
              <Box>
                {tabs[activeTab]?.label === 'SUBDOMAINS' && renderSubdomains()}
                {tabs[activeTab]?.label === 'URLS' && renderEndpoints()}
                {tabs[activeTab]?.label === 'VULNERABILITIES' && renderVulnerabilities()}
                {tabs[activeTab]?.label === 'BUCKETS' && renderBuckets()}
                {tabs[activeTab]?.label === 'OSINT' && renderOSINT()}
                {tabs[activeTab]?.label === 'LEAKS' && renderLeaks()}
                {tabs[activeTab]?.label === 'RECON NOTES' && <ReconNotes notes={data.todo_notes} />}
                {tabs[activeTab]?.label === 'EXPLOITS' && renderExploits()}
                
                {!['HOME', 'SUBDOMAINS', 'URLS', 'VULNERABILITIES', 'BUCKETS', 'OSINT', 'LEAKS', 'EXPLOITS', 'RECON NOTES'].includes(tabs[activeTab]?.label) && (
                  <Box sx={{ p: 4, textAlign: 'center', border: '1px dashed rgba(255,255,255,0.1)', borderRadius: 2 }}>
                    <Typography sx={{ color: 'rgba(255,255,255,0.3)', fontFamily: 'Orbitron', fontSize: '0.8rem' }}>MODULE_STAGING_AREA: {tabs[activeTab]?.label}</Typography>
                    <Typography sx={{ color: 'rgba(255,255,255,0.2)', fontSize: '0.65rem', mt: 1 }}>SYNCHRONIZING DATA FROM LEGACY INTERFACE...</Typography>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        </Box>
      </Box>
    </Box>
  );
};
