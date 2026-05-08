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
  LinearProgress,
  FormControlLabel,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  Slide,
  Backdrop
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
  Bug,
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
  Key,
  X,
  Copy,
  RefreshCw,
  GitBranch
} from 'lucide-react';
import { useScanSummary, useActivityLogs, useFetchWhois } from '../api';
import Chart from 'react-apexcharts';
import { GeoMap } from '../../dashboard/components/GeoMap';
import { KpiCard } from '../../../components/KpiCard';
import { SubdomainsTab } from './SubdomainsTab';
import { DirectoriesTab } from './DirectoriesTab';
import { EndpointsTab } from './EndpointsTab';
import { TacticalPanel } from '../../../components/TacticalPanel';
import { VulnerabilityTable } from '../../vulnerabilities/components/VulnerabilityTable';
import { SecretLeaksTab } from './SecretLeaksTab';
import { AttackSurfaceTab } from './AttackSurfaceTab';
import VisualizationTab from './VisualizationTab';
import { ScreenshotsTab } from './ScreenshotsTab';
import { ScanReportModal } from './ScanReportModal';
import { StartScanModal } from './StartScanModal';
import { OsintTab } from './OsintTab';
import { AttackPathsTab } from './AttackPathsTab';
import { usePlugins } from '../../plugins/api/pluginsApi';
import PluginComponent from '../../plugins/components/PluginComponent';
import PluginComponentLoader from '../../plugins/components/PluginComponentLoader';

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
    [1]: { label: 'PENDING', color: '#00f3ff', icon: Activity },
    [2]: { label: 'SUCCESS', color: '#00ff62', icon: Shield },
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

const formatTimeAgo = (date: string) => {
  if (!date) return 'N/A';
  const now = new Date();
  const past = new Date(date);
  const diffMs = now.getTime() - past.getTime();
  const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
  const days = Math.floor(diffHrs / 24);
  const hrs = diffHrs % 24;

  if (days > 0) return `${days} days, ${hrs} hours ago`;
  return `${hrs} hours ago`;
};

const TaskOverlay: React.FC<{
  open: boolean;
  onClose: () => void;
  activityId: number | null;
  activityTitle: string;
}> = ({ open, onClose, activityId, activityTitle }) => {
  const { data: logs, isLoading } = useActivityLogs(activityId);
  const [selectedLog, setSelectedLog] = useState<any>(null);

  // Set first log as selected when logs load
  React.useEffect(() => {
    if (logs && logs.length > 0 && !selectedLog) {
      setSelectedLog(logs[0]);
    }
  }, [logs]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="lg"
      slotProps={{
        paper: {
          sx: {
            bgcolor: '#0a0a0a',
            backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 2,
            minHeight: '70vh'
          }
        }
      }}
    >
      <DialogTitle sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <Stack direction="row" sx={{ spacing: 2, alignItems: "center" }}>
          <Terminal size={20} color="#00f3ff" />
          <Typography sx={{ color: '#fff', fontWeight: 900, fontSize: '1rem', letterSpacing: 1 }}>
            {activityTitle}
          </Typography>
        </Stack>
        <IconButton onClick={onClose} size="small" sx={{ color: 'rgba(255,255,255,0.5)', '&:hover': { color: '#fff', bgcolor: 'rgba(255,255,255,0.05)' } }}>
          <X size={20} />
        </IconButton>
      </DialogTitle>
      <DialogContent sx={{ p: 0, overflow: 'hidden' }}>
        <Grid container sx={{ height: '60vh' }}>
          {/* Command List */}
          <Grid size={{ xs: 4 }} sx={{ borderRight: '1px solid rgba(255,255,255,0.05)', height: '100%', overflowY: 'auto' }}>
            {isLoading ? (
              <Box sx={{ p: 4, textAlign: 'center' }}>
                <CircularProgress size={24} sx={{ color: '#00f3ff' }} />
              </Box>
            ) : logs && logs.length > 0 ? (
              <List sx={{ p: 0 }}>
                {logs.map((log: any) => (
                  <ListItem
                    key={log.id}
                    component="div"
                    onClick={() => setSelectedLog(log)}
                    sx={{
                      cursor: 'pointer',
                      borderBottom: '1px solid rgba(255,255,255,0.03)',
                      py: 2,
                      bgcolor: selectedLog?.id === log.id ? 'rgba(0,243,255,0.05)' : 'transparent',
                      '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' }
                    }}
                  >
                    <ListItemText
                      primary={
                        <Typography sx={{ fontSize: '0.8rem', color: selectedLog?.id === log.id ? '#00f3ff' : '#fff', fontWeight: 700, mb: 0.5, fontFamily: 'monospace' }}>
                          {log.command.split(' ')[0]}
                        </Typography>
                      }
                      secondary={
                        <Typography noWrap sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
                          {log.command}
                        </Typography>
                      }
                    />
                    <ChevronRight size={14} color={selectedLog?.id === log.id ? '#00f3ff' : 'rgba(255,255,255,0.2)'} />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Box sx={{ p: 4, textAlign: 'center', opacity: 0.5 }}>
                <Typography sx={{ fontSize: '0.8rem' }}>No commands logged yet.</Typography>
              </Box>
            )}
          </Grid>
          {/* Command Output */}
          <Grid size={{ xs: 8 }} sx={{ height: '100%', overflowY: 'auto', bgcolor: '#050505' }}>
            {selectedLog ? (
              <Box sx={{ p: 2 }}>
                <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography sx={{ fontSize: '0.7rem', color: '#00f3ff', fontWeight: 900, textTransform: 'uppercase', letterSpacing: 1 }}>Command Execution Output</Typography>
                  <Button
                    size="small"
                    startIcon={<Copy size={12} />}
                    onClick={() => navigator.clipboard.writeText(selectedLog.output)}
                    sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.6rem', border: '1px solid rgba(255,255,255,0.1)', '&:hover': { color: '#fff', border: '1px solid #00f3ff' } }}
                  >
                    Copy Output
                  </Button>
                </Stack>
                <Box sx={{
                  p: 2,
                  bgcolor: 'rgba(0,0,0,0.5)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  borderRadius: 1,
                  fontFamily: 'monospace',
                  fontSize: '0.75rem',
                  color: 'rgba(255,255,255,0.8)',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all'
                }}>
                  {selectedLog.output || "No output captured yet..."}
                </Box>
              </Box>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 2, opacity: 0.3 }}>
                <Terminal size={48} />
                <Typography sx={{ fontSize: '0.8rem', fontWeight: 700 }}>Select a command to view output</Typography>
              </Box>
            )}
          </Grid>
        </Grid>
      </DialogContent>
    </Dialog>
  );
};

const TimelineItem: React.FC<{ activity: any, onClick?: () => void }> = ({ activity, onClick }) => {
  const statusConfig: any = {
    'SUCCESS': { color: '#00ff62', label: 'Completed' },
    'RUNNING': { color: '#00f3ff', label: 'In Progress' },
    'FAILED': { color: '#ff003c', label: 'Failed' },
    'ABORTED': { color: '#ff003c', label: 'Aborted' },
    'PENDING': { color: '#ff9f00', label: 'Pending' }
  };
  const config = statusConfig[activity.status] || { color: '#fff', label: activity.status };

  return (
    <Box
      onClick={activity.has_commands ? onClick : undefined}
      sx={{
        position: 'relative',
        pl: 5,
        pb: 4,
        '&:last-child': { pb: 0 },
        cursor: activity.has_commands ? 'pointer' : 'default',
        '&:hover': activity.has_commands ? {
          '& .timeline-content': { bgcolor: 'rgba(255,255,255,0.03)' }
        } : {}
      }}
    >
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
            opacity: 0.8
          }} />
        )}
      </Box>

      <Stack spacing={0.5} className="timeline-content" sx={{ p: 1, borderRadius: 1, transition: 'background-color 0.2s' }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
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
          {activity.has_commands && (
            <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 0.5 }}>
              • Click to view details <ChevronRight size={10} />
            </Typography>
          )}
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

const SubScanWidget: React.FC<{ subscans: any[], targetName: string }> = ({ subscans, targetName }) => {
  return (
    <Stack spacing={1.5}>
      <Typography sx={{ fontSize: '0.75rem', fontWeight: 900, color: '#ff00ff', mb: 1, textTransform: 'uppercase', letterSpacing: 1.5 }}>
        SUB SCAN HISTORY FOR <Box component="span" sx={{ px: 0.5, bgcolor: 'rgba(255,0,255,0.1)', border: '1px solid rgba(255,0,255,0.2)', borderRadius: 0.5, color: '#ff00ff' }}>{targetName}</Box>
      </Typography>
      {subscans?.map((sub: any) => (
        <Box key={sub.id} sx={{ p: 1.5, borderRadius: 1, bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)', position: 'relative', overflow: 'hidden' }}>
          <Box sx={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 2, bgcolor: sub.status === 2 ? '#00ff62' : '#ffc107' }} />
          <Stack spacing={1}>
            <Typography sx={{ fontSize: '0.75rem', fontWeight: 900, color: '#00f3ff', textTransform: 'uppercase' }}>
              {sub.engine} ON {sub.subdomain_name}
            </Typography>
            <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
              <StatusBadge status={sub.status} />
            </Stack>
            <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>
              {sub.completed_ago} Took {sub.time_taken}
            </Typography>
          </Stack>
        </Box>
      ))}
      {(!subscans || subscans.length === 0) && (
        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.2)', textAlign: 'center', py: 2 }}>NO SUB SCANS FOUND</Typography>
      )}
    </Stack>
  );
};

const VulnerabilityBreakdown: React.FC<{ counts: any, exploitable: number }> = ({ counts, exploitable }) => {
  const series = [counts.critical, counts.high, counts.medium, counts.low, counts.info, counts.unknown, exploitable];
  const labels = ['Critical', 'High', 'Medium', 'Low', 'Info', 'Unknown', 'Exploitable'];
  const colors = ['#ff003c', '#ff5722', '#ff9800', '#ffeb3b', '#2196f3', '#9e9e9e', '#00ff62'];

  return (
    <TacticalPanel title="Vulnerability Breakdown" icon={<Bug size={14} />} sx={{ height: '100%', '& .MuiCardContent-root': { pb: '10px !important' } }}>
      <Box sx={{ p: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3, textAlign: 'center', width: '100%', px: 1 }}>
          {labels.map((l, i) => (
            <Box key={l} sx={{ flex: 1 }}>
              <Typography sx={{ fontSize: '0.6rem', color: colors[i], fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1 }}>{l.substring(0, 4)}</Typography>
              <Typography sx={{ fontSize: '0.85rem', fontWeight: 900, color: colors[i] }}>{series[i] || 0}</Typography>
            </Box>
          ))}
        </Box>
        <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Chart
            options={{
              chart: { type: 'donut', background: 'transparent' },
              theme: { mode: 'dark' as any },
              stroke: { show: false },
              labels: labels,
              dataLabels: { enabled: false },
              legend: { show: true, position: 'bottom', fontSize: '10px', labels: { colors: 'rgba(255,255,255,0.7)' } },
              colors: colors,
              plotOptions: {
                pie: {
                  donut: {
                    size: '65%',
                    labels: {
                      show: true,
                      total: {
                        show: true,
                        label: 'Total',
                        color: 'rgba(255,255,255,0.4)',
                        fontSize: '12px',
                        formatter: () => counts.total.toString()
                      },
                      value: { color: '#fff', fontSize: '20px', fontWeight: 900 }
                    }
                  }
                }
              }
            }}
            series={series}
            type="donut"
            width="100%"
            height={260}
          />
        </Box>
      </Box>
    </TacticalPanel>
  );
};

const VulnHighlights: React.FC<{ highlights: any[] }> = ({ highlights }) => (
  <TacticalPanel title="Vulnerability Highlights" icon={<Bug size={14} />} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
    <TableContainer sx={{ flex: 1, overflow: 'auto', maxHeight: 380 }}>
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow sx={{ '& th': { borderBottom: '2px solid #7000ff', bgcolor: '#12121c', color: '#00f3ff', fontSize: '0.7rem', fontWeight: 900, py: 1.5 } }}>
            <TableCell>TYPE</TableCell>
            <TableCell>VULNERABILITY</TableCell>
            <TableCell>SEVERITY</TableCell>
            <TableCell>VULNERABLE URL</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(highlights || []).map((v: any, idx: number) => (
            <TableRow key={idx} sx={{ '& td': { borderBottom: '1px solid rgba(255,255,255,0.05)', py: 2 } }}>
              <TableCell>
                <Box sx={{
                  bgcolor: 'rgba(33,150,243,0.1)',
                  color: '#2196f3',
                  fontSize: '0.6rem',
                  fontWeight: 900,
                  px: 1,
                  py: 0.5,
                  borderRadius: 0.5,
                  display: 'inline-block',
                  textTransform: 'lowercase'
                }}>
                  {v.severity === 0 ? 'info' : 'vuln'}
                </Box>
              </TableCell>
              <TableCell>
                <Typography sx={{ fontSize: '0.75rem', fontWeight: 800, color: '#fff', mb: 0.5 }}>{v.name}</Typography>
                <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
                  Discovered: {formatTimeAgo(v.discovered_date)}
                </Typography>
              </TableCell>
              <TableCell>
                <SeverityBadge severity={v.severity} />
              </TableCell>
              <TableCell>
                <Typography sx={{
                  fontSize: '0.7rem',
                  color: '#ff003c',
                  fontWeight: 600,
                  wordBreak: 'break-all'
                }}>
                  {v.http_url}
                </Typography>
              </TableCell>
            </TableRow>
          ))}
          {(!highlights || highlights.length === 0) && (
            <TableRow>
              <TableCell colSpan={4} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)' }}>NO VULNERABILITY HIGHLIGHTS</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  </TacticalPanel>
);

const MostVulnerableSubdomain: React.FC<{ vulnerabilities: any[], sx?: any }> = ({ vulnerabilities, sx = {} }) => {
  const [ignoreInfo, setIgnoreInfo] = useState(false);

  const filteredVulns = ignoreInfo ? vulnerabilities.filter(v => v.severity > 0) : vulnerabilities;

  const subdomainCounts = filteredVulns.reduce((acc: Record<string, number>, v: any) => {
    const host = new URL(v.http_url).hostname;
    acc[host] = (acc[host] || 0) + 1;
    return acc;
  }, {});

  const sorted = Object.entries(subdomainCounts).sort((a: any, b: any) => b[1] - a[1]);
  const mostVulnerable = sorted[0];

  return (
    <TacticalPanel
      title="MOST VULNERABLE SUBDOMAIN"
      icon={<ShieldAlert size={14} color="#ff003c" />}
      sx={{ height: '100%', ...sx }}
      headerAction={
        <FormControlLabel
          control={<Checkbox size="small" checked={ignoreInfo} onChange={(e) => setIgnoreInfo(e.target.checked)} sx={{ color: 'rgba(255,255,255,0.4)', '&.Mui-checked': { color: '#00f3ff' } }} />}
          label={<Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.6)', fontWeight: 800 }}>Ignore Info Vulnerabilities</Typography>}
        />
      }
    >
      <Box sx={{ p: 2 }}>
        {mostVulnerable ? (
          <Box sx={{ bgcolor: 'rgba(255,0,60,0.05)', border: '1px solid rgba(255,0,60,0.1)', p: 2, borderRadius: 1 }}>
            <Typography sx={{ fontSize: '1rem', fontWeight: 900, color: '#ff003c', mb: 1 }}>{mostVulnerable[0]}</Typography>
            <Typography sx={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)' }}>Total Vulnerabilities: <Box component="span" sx={{ color: '#ff003c', fontWeight: 900 }}>{String(mostVulnerable[1])}</Box></Typography>
          </Box>
        ) : (
          <Box sx={{ bgcolor: 'rgba(255,252,0,0.1)', border: '1px solid rgba(255,252,0,0.2)', p: 2, borderRadius: 1 }}>
            <Typography sx={{ fontSize: '0.75rem', color: '#fffc00', fontWeight: 700, mb: 1 }}>Could not find most vulnerable targets.</Typography>
            <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,252,0,0.6)' }}>Once the vulnerability scan is performed, reNgine will identify the most vulnerable targets.</Typography>
          </Box>
        )}
      </Box>
    </TacticalPanel>
  );
};

const MostCommonVulnsWidget: React.FC<{ vulnerabilities: any[], sx?: any }> = ({ vulnerabilities = [], sx = {} }) => {
  const [ignoreInfo, setIgnoreInfo] = useState(false);
  const filtered = ignoreInfo ? vulnerabilities.filter(v => v.severity !== 0 && v.severity !== 'Info') : vulnerabilities;

  // Calculate common vulns from the full vulnerabilities list to ensure Info vulns are included
  const commonMap = filtered.reduce((acc: any, v: any) => {
    acc[v.name] = acc[v.name] || { name: v.name, count: 0, severity: v.severity };
    acc[v.name].count += 1;
    return acc;
  }, {});

  const data = Object.values(commonMap).sort((a: any, b: any) => b.count - a.count).slice(0, 10);

  return (
    <TacticalPanel
      title="MOST COMMON VULNERABILITIES"
      icon={<Bug size={14} color="#ff003c" />}
      sx={{ height: '100%', ...sx }}
      headerAction={
        <FormControlLabel
          control={<Checkbox size="small" checked={ignoreInfo} onChange={(e) => setIgnoreInfo(e.target.checked)} sx={{ color: 'rgba(255,255,255,0.4)', '&.Mui-checked': { color: '#00f3ff' } }} />}
          label={<Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.6)', fontWeight: 800 }}>Ignore Info Vulnerabilities</Typography>}
        />
      }
    >
      <TableContainer sx={{ flex: 1, overflow: 'auto' }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ '& th': { borderBottom: '2px solid rgba(255,255,255,0.05)', color: '#00f3ff', fontSize: '0.65rem', fontWeight: 900 } }}>
              <TableCell>VULNERABILITY NAME</TableCell>
              <TableCell align="center">COUNT</TableCell>
              <TableCell align="right">SEVERITY</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.map((v: any, i: number) => (
              <TableRow key={i} sx={{ '& td': { borderBottom: '1px solid rgba(255,255,255,0.03)', py: 1 } }}>
                <TableCell sx={{ color: '#ff00ff', fontSize: '0.7rem', fontWeight: 800 }}>{v.name}</TableCell>
                <TableCell align="center">
                  <Box sx={{ display: 'inline-block', px: 1, border: '1px solid #ff003c', color: '#ff003c', borderRadius: 0.5, fontSize: '0.65rem', fontWeight: 900 }}>
                    {v.count}
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <SeverityBadge severity={typeof v.severity === 'string' ? (v.severity === 'Critical' ? 4 : v.severity === 'High' ? 3 : v.severity === 'Medium' ? 2 : v.severity === 'Low' ? 1 : 0) : v.severity} />
                </TableCell>
              </TableRow>
            ))}
            {data.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} align="center" sx={{ py: 4, color: 'rgba(255,255,255,0.2)', fontSize: '0.7rem' }}>NO VULNERABILITIES FOUND</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </TacticalPanel>
  );
};

const ImportantSubdomainsWidget: React.FC<{ subdomains: any[], sx?: any }> = ({ subdomains = [], sx = {} }) => (
  <TacticalPanel title="IMPORTANT SUBDOMAINS" icon={<Box sx={{ width: 14, height: 14, bgcolor: '#ff00ff', borderRadius: 0.5, color: '#fff', fontSize: '8px', fontWeight: 900, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{subdomains.length}</Box>} sx={{ height: '100%', ...sx }}>
    <Box sx={{ p: 2 }}>
      {subdomains.length > 0 ? (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {subdomains.map((s: any, i: number) => (
            <Box key={i} sx={{ px: 1.5, py: 0.5, bgcolor: 'rgba(0,243,255,0.05)', border: '1px solid rgba(0,243,255,0.1)', borderRadius: 1, color: '#00f3ff', fontSize: '0.7rem', fontWeight: 700 }}>
              {s.name}
            </Box>
          ))}
        </Box>
      ) : (
        <Typography sx={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.3)', fontStyle: 'italic' }}>No subdomains marked as important!</Typography>
      )}
    </Box>
  </TacticalPanel>
);

const ReconNotesWidget: React.FC<{ notes: any[], sx?: any }> = ({ notes = [], sx = {} }) => (
  <TacticalPanel
    title="RECON NOTE/TODO"
    icon={<Box sx={{ width: 14, height: 14, bgcolor: '#2196f3', borderRadius: 0.5, color: '#fff', fontSize: '8px', fontWeight: 900, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{notes.length}</Box>}
    headerAction={<Plus size={14} color="#00f3ff" style={{ cursor: 'pointer' }} />}
    sx={{ height: '100%', ...sx }}
  >
    <Box sx={{ p: 2 }}>
      {notes.length > 0 ? (
        <Stack spacing={1}>
          {notes.map((n: any) => (
            <Box key={n.id} sx={{ p: 1, bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 1, display: 'flex', gap: 1.5 }}>
              <Checkbox size="small" checked={n.is_done} sx={{ color: 'rgba(255,255,255,0.2)', p: 0 }} />
              <Box>
                <Typography sx={{ fontSize: '0.75rem', fontWeight: 800, color: n.is_done ? 'rgba(255,255,255,0.3)' : '#fff', textDecoration: n.is_done ? 'line-through' : 'none' }}>{n.title}</Typography>
                <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>{n.description}</Typography>
              </Box>
            </Box>
          ))}
        </Stack>
      ) : (
        <Box>
          <Typography sx={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', fontWeight: 700 }}>No todos or notes...</Typography>
          <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.2)' }}>You can add todo for individual subdomains or you can also add using + symbol above.</Typography>
        </Box>
      )}
    </Box>
  </TacticalPanel>
);

const IpAddressesWidget: React.FC<{ subdomains: any[], sx?: any }> = ({ subdomains = [], sx = {} }) => {
  const ips = Array.from(new Set(subdomains.map(s => s.origin_ip).filter(ip => ip && ip !== '0.0.0.0')));
  return (
    <TacticalPanel title="IP ADDRESSES" icon={<Box sx={{ width: 14, height: 14, bgcolor: '#7000ff', borderRadius: 0.5, color: '#fff', fontSize: '8px', fontWeight: 900, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{ips.length}</Box>} sx={{ height: '100%', ...sx }}>
      <Box sx={{ p: 2 }}>
        <Typography sx={{ fontSize: '0.6rem', color: '#fffc00', textAlign: 'right', mb: 1, fontWeight: 700 }}>*IP Addresses highlighted with yellow are CDN IP</Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {ips.map((ip, i) => (
            <Box key={i} sx={{ px: 1, py: 0.4, bgcolor: 'rgba(33,150,243,0.1)', border: '1px solid rgba(33,150,243,0.2)', borderRadius: 0.5, color: '#2196f3', fontSize: '0.65rem', fontWeight: 800 }}>
              {ip}
            </Box>
          ))}
        </Box>
      </Box>
    </TacticalPanel>
  );
};

const DiscoveredPortsWidget: React.FC<{ ports: any[], sx?: any }> = ({ ports = [], sx = {} }) => (
  <TacticalPanel title="DISCOVERED PORTS" icon={<Box sx={{ width: 14, height: 14, bgcolor: '#7000ff', borderRadius: 0.5, color: '#fff', fontSize: '8px', fontWeight: 900, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{ports.length}</Box>} sx={{ height: '100%', ...sx }}>
    <Box sx={{ p: 2 }}>
      <Typography sx={{ fontSize: '0.6rem', color: '#fffc00', textAlign: 'right', mb: 1, fontWeight: 700 }}>*Ports highlighted with red are uncommon Ports</Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        {ports.map((p, i) => (
          <Box key={i} sx={{ px: 1, py: 0.4, bgcolor: p.is_uncommon ? 'rgba(255,0,60,0.1)' : 'rgba(33,150,243,0.1)', border: `1px solid ${p.is_uncommon ? 'rgba(255,0,60,0.2)' : 'rgba(33,150,243,0.2)'}`, borderRadius: 0.5, color: p.is_uncommon ? '#ff003c' : '#2196f3', fontSize: '0.65rem', fontWeight: 800 }}>
            {p.number}/{p.service_name}
          </Box>
        ))}
      </Box>
    </Box>
  </TacticalPanel>
);

const DiscoveredTechWidget: React.FC<{ techs: any[], sx?: any }> = ({ techs = [], sx = {} }) => (
  <TacticalPanel title="DISCOVERED TECHNOLOGIES" icon={<Box sx={{ width: 14, height: 14, bgcolor: '#7000ff', borderRadius: 0.5, color: '#fff', fontSize: '8px', fontWeight: 900, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{techs.length}</Box>} sx={{ height: '100%', ...sx }}>
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        {techs.map((t, i) => (
          <Box key={i} sx={{ px: 1, py: 0.4, bgcolor: 'rgba(33,150,243,0.1)', border: '1px solid rgba(33,150,243,0.2)', borderRadius: 0.5, color: '#2196f3', fontSize: '0.65rem', fontWeight: 800 }}>
            {t.name}
          </Box>
        ))}
      </Box>
    </Box>
  </TacticalPanel>
);

export const ScanDetailPage = () => {
  const { projectSlug, scanId } = useParams({ from: '/$projectSlug/scan/detail/$scanId' });
  const { data, isLoading } = useScanSummary(projectSlug, parseInt(scanId));
  const fetchWhois = useFetchWhois(projectSlug, parseInt(scanId));
  const { data: plugins } = usePlugins();
  const [activeTab, setActiveTab] = useState(0);
  const [infoTab, setInfoTab] = useState(0);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [startScanTargets, setStartScanTargets] = useState<{ ids: number[]; names: string[] } | null>(null);
  const [taskOverlayOpen, setTaskOverlayOpen] = useState(false);
  const [selectedActivity, setSelectedActivity] = useState<{ id: number; title: string } | null>(null);

  const handleTimelineItemClick = (activity: any) => {
    setSelectedActivity({ id: activity.id, title: activity.title });
    setTaskOverlayOpen(true);
  };

  if (isLoading || !data) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress sx={{ color: '#00f3ff' }} />
      </Box>
    );
  }

  const baseTabs = [
    { label: 'HOME', icon: Activity },
    { label: 'SUBDOMAINS', icon: Globe },
    { label: 'BUCKETS', icon: Database, show: data.buckets_count > 0 },
    { label: 'SCREENSHOTS', icon: Camera, show: data.scan_info.tasks?.includes('screenshot') },
    { label: 'DIRECTORIES', icon: Folder, show: data.scan_info.tasks?.includes('dir_file_fuzz') },
    { label: 'URLS', icon: LinkIcon },
    { label: 'VULNERABILITIES', icon: ShieldAlert, show: data.vulnerability_count > 0 },
    { label: 'EXPLOITS', icon: Zap, show: data.exploitable_count > 0 },
    { label: 'OSINT', icon: Search, show: data.scan_info.tasks?.includes('osint') },
    { label: 'LEAKS', icon: Shield },
    { label: 'ATTACK PATHS', icon: GitBranch, show: data.vulnerability_count > 0 },
    { label: 'ATTACK SURFACE', icon: MapIcon },
    { label: 'RECON NOTES', icon: FileText },
    { label: 'VISUALIZATION', icon: BarChart2 },
  ].filter(t => t.show !== false);

  // Inject Plugin Tabs
  const pluginTabs: any[] = [];
  if (Array.isArray(plugins)) {
    plugins.forEach(plugin => {
      if (plugin.is_enabled && plugin.manifest?.ui?.tabs && Array.isArray(plugin.manifest.ui.tabs)) {
        plugin.manifest.ui.tabs.forEach((tab: any) => {
          pluginTabs.push({
            label: tab.label,
            icon: Zap, // Default icon for plugins, could be dynamic
            isPlugin: true,
            pluginSlug: plugin.slug,
            componentFile: tab.file
          });
        });
      }
    });
  }

  const tabs = [...baseTabs, ...pluginTabs];

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
              <Grid size={{ xs: 6 }}>
                <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', mb: 1, fontWeight: 700 }}>ENGINE</Typography>
                <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                  <Cpu size={16} color="#00f3ff" />
                  <Typography sx={{ fontSize: '0.9rem', fontWeight: 800, color: '#fff' }}>{data.scan_info.engine_name}</Typography>
                </Stack>
              </Grid>
              <Grid size={{ xs: 6 }}>
                <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', mb: 1, fontWeight: 700 }}>DURATION</Typography>
                <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
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
                <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
                  {data.scan_info.cfg_imported_subdomains.map((s: string) => <Chip key={s} label={s} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'rgba(0,243,255,0.1)', color: '#00f3ff', mb: 0.5 }} />)}
                </Stack>
              ) : <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.2)' }}>None</Typography>}
            </Box>
            <Box>
              <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', mb: 0.5 }}>OUT OF SCOPE</Typography>
              {data.scan_info.cfg_out_of_scope_subdomains?.length > 0 ? (
                <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
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
            <Box sx={{ position: 'relative' }}>
              {data.timeline?.map((activity: any, idx: number) => (
                <TimelineItem
                  key={idx}
                  activity={activity}
                  onClick={() => handleTimelineItemClick(activity)}
                />
              ))}
            </Box>
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
                <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
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
          <SubScanWidget subscans={data.subscans} targetName={data.target_info.name} />
        </Box>
      </TacticalPanel>
    </Box>
  );

  const renderHomeContent = () => (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, width: '100%' }}>
      {/* Row 1: Target Information and HTTP Status Charts (MOVED UP) */}
      <Grid container spacing={2} sx={{ alignItems: 'stretch', width: '100%', m: 0 }}>
        <Grid size={{ xs: 12, md: 6 }} sx={{ display: 'flex' }}>
          <TacticalPanel title="Target Information" icon={<Activity size={14} />} sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ p: 2, flex: 1 }}>
              <Tabs value={infoTab} onChange={(_, v) => setInfoTab(v)} sx={{ mb: 2, borderBottom: '1px solid rgba(255,255,255,0.05)', minHeight: 32 }}>
                {['Domain Info', 'Whois', 'DNS Records', 'Nameservers', 'History'].map((l) => (
                  <Tab key={l} label={l} sx={{ fontSize: '0.65rem', fontWeight: 900, minHeight: 32, p: 1, color: 'rgba(255,255,255,0.4)', '&.Mui-selected': { color: '#00f3ff' } }} />
                ))}
              </Tabs>

              {infoTab === 0 && (
                <Grid container spacing={3}>
                  {/* Column 1: ID & Origin */}
                  <Grid size={{ xs: 6 }}>
                    <Stack spacing={2.5}>
                      <Box>
                        <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', mb: 0.2, textTransform: 'uppercase', letterSpacing: 1 }}>Domain</Typography>
                        <Typography sx={{ fontSize: '0.8rem', fontWeight: 800, color: '#ff003c', fontFamily: 'Orbitron', wordBreak: 'break-all' }}>{data.target_info.name}</Typography>
                      </Box>
                      <Box>
                        <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', mb: 0.2, textTransform: 'uppercase', letterSpacing: 1 }}>Dnssec</Typography>
                        <Typography sx={{ fontSize: '0.8rem', fontWeight: 700, color: '#fff' }}>{data.domain_info?.dnssec || 'N/A'}</Typography>
                      </Box>
                      <Box>
                        <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', mb: 0.2, textTransform: 'uppercase', letterSpacing: 1 }}>Geolocation</Typography>
                        <Typography sx={{ fontSize: '0.8rem', fontWeight: 700, color: '#fff' }}>{data.domain_info?.geolocation_iso || 'N/A'}</Typography>
                      </Box>
                      <Box>
                        <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', mb: 0.2, textTransform: 'uppercase', letterSpacing: 1 }}>Created</Typography>
                        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)' }}>{data.domain_info?.created?.split('T')[0] || 'N/A'}</Typography>
                      </Box>
                    </Stack>
                  </Grid>

                  {/* Column 2: Maintenance & Registrar */}
                  <Grid size={{ xs: 6 }}>
                    <Stack spacing={2.5}>
                      <Box>
                        <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', mb: 0.2, textTransform: 'uppercase', letterSpacing: 1 }}>Updated</Typography>
                        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)' }}>{data.domain_info?.updated?.split('T')[0] || 'N/A'}</Typography>
                      </Box>
                      <Box>
                        <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', mb: 0.2, textTransform: 'uppercase', letterSpacing: 1 }}>Expires</Typography>
                        <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)' }}>{data.domain_info?.expires?.split('T')[0] || 'N/A'}</Typography>
                      </Box>
                      <Box>
                        <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', mb: 0.2, textTransform: 'uppercase', letterSpacing: 1 }}>Registrar</Typography>
                        <Typography sx={{ fontSize: '0.8rem', fontWeight: 700, color: '#00f3ff' }}>{data.domain_info?.registrar?.name || 'N/A'}</Typography>
                      </Box>
                    </Stack>
                  </Grid>
                </Grid>
              )}
              {infoTab === 1 && (
                <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                  {!data.domain_info?.whois_data ? (
                    <Box sx={{ p: 4, textAlign: 'center' }}>
                      <Typography sx={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.4)', mb: 2 }}>
                        No WHOIS data available for this target.
                      </Typography>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={fetchWhois.isPending ? <CircularProgress size={12} /> : <Search size={12} />}
                        disabled={fetchWhois.isPending}
                        onClick={() => fetchWhois.mutate(data.target_info.name)}
                        sx={{
                          color: '#00f3ff',
                          borderColor: 'rgba(0,243,255,0.3)',
                          fontSize: '0.65rem',
                          fontWeight: 900,
                          '&:hover': {
                            borderColor: '#00f3ff',
                            bgcolor: 'rgba(0,243,255,0.05)'
                          }
                        }}
                      >
                        {fetchWhois.isPending ? 'FETCHING...' : 'FETCH WHOIS DATA'}
                      </Button>
                    </Box>
                  ) : (
                    <Box>
                      <Stack direction="row" sx={{ justifyContent: 'flex-end', mb: 1 }}>
                        <Button
                          size="small"
                          startIcon={fetchWhois.isPending ? <CircularProgress size={10} /> : <RefreshCw size={10} />}
                          disabled={fetchWhois.isPending}
                          onClick={() => fetchWhois.mutate(data.target_info.name)}
                          sx={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.6rem', '&:hover': { color: '#00f3ff' } }}
                        >
                          Refresh
                        </Button>
                      </Stack>
                      <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.7)', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                        {data.domain_info?.whois_data}
                      </Typography>
                    </Box>
                  )}
                </Box>
              )}
              {infoTab === 2 && (
                <Stack spacing={1}>
                  {data.domain_info?.dns_records?.map((r: any, idx: number) => (
                    <Stack key={idx} direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                      <Chip label={r.type.toUpperCase()} size="small" sx={{ height: 16, fontSize: '0.55rem', fontWeight: 900, bgcolor: 'rgba(0,243,255,0.1)', color: '#00f3ff' }} />
                      <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)' }}>{r.name} {"->"} {r.value}</Typography>
                    </Stack>
                  ))}
                </Stack>
              )}
              {infoTab === 3 && (
                <Stack spacing={1}>
                  {data.domain_info?.nameservers?.map((ns: string, idx: number) => (
                    <Stack key={idx} direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                      <Globe size={14} color="#00f3ff" />
                      <Typography sx={{ fontSize: '0.7rem', color: '#fff' }}>{ns}</Typography>
                    </Stack>
                  ))}
                </Stack>
              )}
            </Box>
          </TacticalPanel>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }} sx={{ display: 'flex' }}>
          <TacticalPanel title="HTTP Status Breakdown" icon={<Activity size={14} />} sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', justifyContent: 'center', flex: 1 }}>
              <Chart
                options={{
                  chart: { type: 'donut', background: 'transparent' },
                  theme: { mode: 'dark' as any },
                  labels: (data?.http_status_breakdown || []).slice().sort((a: any, b: any) => a.http_status - b.http_status).map((s: any) => `HTTP ${s.http_status}`),
                  colors: ['#00ff62', '#ff003c', '#00f3ff', '#7000ff', '#fffc00', '#ff8000', '#0080ff', '#8000ff'],
                  stroke: { show: false },
                  dataLabels: { enabled: false },
                  legend: { 
                    position: 'right', 
                    horizontalAlign: 'left',
                    labels: { colors: 'rgba(255,255,255,0.7)' },
                    itemMargin: { vertical: 2 }
                  },
                  plotOptions: { pie: { donut: { size: '70%' } } }
                }}
                series={(data?.http_status_breakdown || []).slice().sort((a: any, b: any) => a.http_status - b.http_status).map((s: any) => s.count)}
                type="donut"
                width="100%"
                height={300}
              />
            </Box>
          </TacticalPanel>
        </Grid>
      </Grid>

      {/* Row 2: GeoMap (MOVED UP) */}
      <TacticalPanel title="Geographical Distribution" icon={<Globe size={14} />}>
        <Box sx={{ p: 0 }}>
          <GeoMap data={data.asset_countries || []} disableCard={true} />
        </Box>
      </TacticalPanel>

      {/* Row 3: Vulnerability Distribution & Highlights */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' }, gap: 2, mb: 2, width: '100%' }}>
        <VulnerabilityBreakdown
          counts={{
            critical: data.critical_count,
            high: data.high_count,
            medium: data.medium_count,
            low: data.low_count,
            info: data.info_count,
            unknown: data.unknown_count,
            total: data.vulnerability_count
          }}
          exploitable={data.exploitable_count}
        />
        <VulnHighlights highlights={data.vulnerability_highlights} />
      </Box>

      {/* Row 4: Vulnerability Deep Dive */}
      <Grid container spacing={2} sx={{ mb: 2, width: '100%', m: 0 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <MostVulnerableSubdomain vulnerabilities={data.vulnerabilities} sx={{ height: '100%' }} />
        </Grid>
        <Grid size={{ xs: 12, md: 8 }}>
          <MostCommonVulnsWidget vulnerabilities={data.vulnerabilities} sx={{ height: '100%' }} />
        </Grid>
      </Grid>

      {/* Row 5: Contextual Assets */}
      <Grid container spacing={2} sx={{ mb: 2, width: '100%', m: 0 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <ImportantSubdomainsWidget subdomains={data.important_subdomains} sx={{ height: '100%' }} />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <ReconNotesWidget notes={data.todo_notes} sx={{ height: '100%' }} />
        </Grid>
      </Grid>

      {/* Row 6: Infrastructure & Fingerprinting */}
      <Grid container spacing={2} sx={{ width: '100%', m: 0 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <IpAddressesWidget subdomains={data.subdomains} sx={{ height: '100%' }} />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <DiscoveredPortsWidget ports={data.discovered_ports} sx={{ height: '100%' }} />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <DiscoveredTechWidget techs={data.discovered_technologies} sx={{ height: '100%' }} />
        </Grid>
      </Grid>
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
    <OsintTab data={data} />
  );

  const renderLeaks = () => (
    <SecretLeaksTab projectSlug={projectSlug} scanId={parseInt(scanId)} />
  );

  const renderAttackSurface = () => (
    <AttackSurfaceTab projectSlug={projectSlug} scanId={parseInt(scanId)} />
  );

  const renderVisualization = () => (
    <VisualizationTab projectSlug={projectSlug} scanId={parseInt(scanId)} />
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
    <SubdomainsTab projectSlug={projectSlug} scanId={parseInt(scanId)} />
  );

  const renderEndpoints = () => (
    <EndpointsTab projectSlug={projectSlug} scanId={parseInt(scanId)} matchedGfCounts={data.matched_gf_count} />
  );
  const renderDirectories = () => (
    <DirectoriesTab projectSlug={projectSlug} scanId={parseInt(scanId)} />
  );

  const renderVulnerabilities = () => (
    <TacticalPanel title="VULNERABILITY INTELLIGENCE" icon={<ShieldAlert size={18} color="#00f3ff" />}>
      <PluginComponent
        name="VulnerabilityTable"
        default={VulnerabilityTable}
        projectSlug={projectSlug}
        scanId={parseInt(scanId)}
      />
    </TacticalPanel>
  );

  return (
    <Box sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box sx={{ mt: 0.5 }}>
            <Typography variant="h5" sx={{ fontWeight: 900, fontFamily: 'Orbitron', color: '#fff', letterSpacing: 2 }}>SCAN DETAIL</Typography>
            <Typography sx={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', fontWeight: 600 }}>IDENTIFIER: {scanId} | TARGET: {data.target_info.name}</Typography>
          </Box>
          <Stack spacing={1} sx={{ alignItems: 'flex-end' }}>
            <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
              <Button
                variant="contained"
                startIcon={<RefreshCw size={16} />}
                onClick={() => setStartScanTargets({ ids: [data.target_info.id], names: [data.target_info.name] })}
                sx={{
                  bgcolor: 'rgba(0, 255, 98, 0.1)',
                  color: '#00ff62',
                  border: '1px solid rgba(0, 255, 98, 0.3)',
                  fontFamily: 'Orbitron',
                  fontSize: '0.65rem',
                  fontWeight: 900,
                  px: 2,
                  '&:hover': { bgcolor: 'rgba(0, 255, 98, 0.2)' }
                }}
              >
                RESCAN
              </Button>
              <Button
                variant="contained"
                startIcon={<FileText size={16} />}
                onClick={() => setReportModalOpen(true)}
                sx={{
                  bgcolor: 'rgba(0, 243, 255, 0.1)',
                  color: '#00f3ff',
                  border: '1px solid rgba(0, 243, 255, 0.3)',
                  fontFamily: 'Orbitron',
                  fontSize: '0.65rem',
                  fontWeight: 900,
                  px: 2,
                  '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)' }
                }}
              >
                GENERATE REPORT
              </Button>
              <Button
                variant="contained"
                component={RouterLink}
                to={`/${projectSlug}/stress_testing/${scanId}`}
                startIcon={<Zap size={16} />}
                sx={{
                  bgcolor: 'rgba(255, 0, 255, 0.1)',
                  color: '#ff00ff',
                  border: '1px solid rgba(255, 0, 255, 0.3)',
                  fontFamily: 'Orbitron',
                  fontSize: '0.65rem',
                  fontWeight: 900,
                  px: 2,
                  '&:hover': { bgcolor: 'rgba(255, 0, 255, 0.2)' }
                }}
              >
                STRESS TEST
              </Button>
            </Stack>
            <Stack direction="row" spacing={1} sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>
              <span>SCANS</span> / <span>DETAIL</span> / <span style={{ color: '#00f3ff' }}>{data.target_info.name}</span>
            </Stack>
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

      {/* MAIN TWO-COLUMN LAYOUT (Sidebar Left, Content Right) */}
      <Box sx={{
        display: 'grid',
        gridTemplateColumns: tabs[activeTab]?.label === 'HOME'
          ? { xs: '1fr', lg: '320px 1fr' }
          : '1fr',
        gap: 3,
        alignItems: 'start',
        width: '100%',
        minWidth: 0
      }}>

        {/* LEFT COLUMN: Scan Metadata & Timeline (Only on HOME tab) */}
        {tabs[activeTab]?.label === 'HOME' && (
          <Box sx={{
            position: { lg: 'sticky' },
            top: 70,
            transition: 'all 0.3s ease',
            minWidth: 0
          }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              {renderSidebar()}
            </Box>
          </Box>
        )}

        {/* RIGHT COLUMN: Discovery Content */}
        <Box sx={{ minWidth: 0, width: '100%' }}>
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
                  width: '100%'
                }}>
                  <KpiCard
                    title="SUBDOMAINS"
                    value={data.subdomain_count}
                    subtitle={`${data.alive_count} ACTIVE`}
                    color="#7000ff"
                    icon={Layers}
                    sx={{ height: '100%' }}
                  />
                  <KpiCard
                    title="ENDPOINTS"
                    value={data.endpoint_count}
                    subtitle={`${data.endpoint_alive_count} ALIVE`}
                    color="#ff00f7"
                    icon={Target}
                    sx={{ height: '100%' }}
                  />
                  <KpiCard
                    title="VULNS"
                    value={data.vulnerability_count}
                    subtitle={`${data.critical_count} CRITICAL`}
                    color="#ff003c"
                    icon={Bug}
                    sx={{ height: '100%' }}
                  />
                  <KpiCard
                    title="OSINT"
                    value={data.secret_leaks_count}
                    subtitle="SENSITIVE DATA"
                    color="#fffc00"
                    icon={Key}
                    sx={{ height: '100%' }}
                  />
                </Box>

                {/* Discovery Modules (Target Info, etc.) */}
                {renderHomeContent()}
              </Box>
            ) : (
              /* Discovery-Specific Tab Content */
              <Box>
                {tabs[activeTab]?.label === 'SUBDOMAINS' && renderSubdomains()}
                {tabs[activeTab]?.label === 'DIRECTORIES' && renderDirectories()}
                {tabs[activeTab]?.label === 'URLS' && renderEndpoints()}
                {tabs[activeTab]?.label === 'VULNERABILITIES' && renderVulnerabilities()}
                {tabs[activeTab]?.label === 'BUCKETS' && renderBuckets()}
                {tabs[activeTab]?.label === 'SCREENSHOTS' && <ScreenshotsTab projectSlug={projectSlug} scanId={parseInt(scanId)} />}
                {tabs[activeTab]?.label === 'OSINT' && renderOSINT()}
                {tabs[activeTab]?.label === 'LEAKS' && renderLeaks()}
                {tabs[activeTab]?.label === 'ATTACK SURFACE' && renderAttackSurface()}
                {tabs[activeTab]?.label === 'VISUALIZATION' && renderVisualization()}
                {tabs[activeTab]?.label === 'RECON NOTES' && <ReconNotesWidget notes={data.todo_notes} />}
                {tabs[activeTab]?.label === 'ATTACK PATHS' && <AttackPathsTab scanId={parseInt(scanId)} />}
                {tabs[activeTab]?.label === 'EXPLOITS' && renderExploits()}

                {tabs[activeTab]?.isPlugin && tabs[activeTab]?.pluginSlug && tabs[activeTab]?.componentFile && (
                  <PluginComponentLoader
                    pluginSlug={tabs[activeTab].pluginSlug}
                    componentFile={tabs[activeTab].componentFile}
                    scanId={parseInt(scanId)}
                    projectSlug={projectSlug}
                  />
                )}

                {!['HOME', 'SUBDOMAINS', 'DIRECTORIES', 'URLS', 'VULNERABILITIES', 'BUCKETS', 'SCREENSHOTS', 'OSINT', 'LEAKS', 'EXPLOITS', 'RECON NOTES', 'ATTACK SURFACE', 'VISUALIZATION', 'ATTACK PATHS'].includes(tabs[activeTab]?.label) && !tabs[activeTab]?.isPlugin && (
                  <Box sx={{ p: 4, textAlign: 'center', border: '1px dashed rgba(255,255,255,0.1)', borderRadius: 2 }}>
                    <Typography sx={{ color: 'rgba(255,255,255,0.3)', fontFamily: 'Orbitron', fontSize: '0.8rem' }}>MODULE STAGING AREA: {tabs[activeTab]?.label}</Typography>
                    <Typography sx={{ color: 'rgba(255,255,255,0.2)', fontSize: '0.65rem', mt: 1 }}>SYNCHRONIZING DATA FROM LEGACY INTERFACE...</Typography>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        </Box>
      </Box>
      <ScanReportModal
        open={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
        scanId={parseInt(scanId)}
      />

      <TaskOverlay
        open={taskOverlayOpen}
        onClose={() => setTaskOverlayOpen(false)}
        activityId={selectedActivity?.id || null}
        activityTitle={selectedActivity?.title || ''}
      />

      {startScanTargets && (
        <StartScanModal
          open={!!startScanTargets}
          onClose={() => setStartScanTargets(null)}
          domainIds={startScanTargets.ids}
          domainNames={startScanTargets.names}
          projectSlug={projectSlug}
        />
      )}
    </Box>
  );
};
