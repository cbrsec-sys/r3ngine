import React, { useState, useMemo, useEffect } from 'react';
import { useParams, Link as RouterLink } from '@tanstack/react-router';
import { 
  Box, 
  Grid, 
  Typography, 
  Button, 
  IconButton, 
  CircularProgress,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  OutlinedInput,
  Chip,
  useTheme,
  alpha,
  Tooltip,
  Tabs,
  Tab,
  Switch,
  FormControlLabel,
  Divider,
  Fab,
  Checkbox
} from '@mui/material';
import { 
  Play, 
  Square, 
  Settings as SettingsIcon,
  Activity,
  Zap,
  AlertTriangle,
  ArrowLeft,
  Server,
  Terminal,
  Clock,
  FileText,
  Download,
  Wifi,
  WifiOff,
  Sliders,
  Trash2
} from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import { useStressStore } from '../store/stressStore';
import { useStressTelemetry } from '../hooks/useStressTelemetry';
import { KpiCard } from '../components/KpiCard';
import { TacticalPanel } from '../components/TacticalPanel';
import axios from 'axios';

export const StressTestingPage: React.FC = () => {
  const theme = useTheme();
  const { projectSlug, scanId } = useParams({ from: '/$projectSlug/stress_testing/$scanId' });
  const { 
    isScanning, 
    wsStatus,
    telemetryData, 
    setScanning,
    clearTelemetry
  } = useStressStore();
  
  useStressTelemetry(scanId);

  const [isStopping, setIsStopping] = useState(false);
  const [openSettings, setOpenSettings] = useState(false);
  
  // Settings Config containing base concurrency/duration and list of active tools
  const [config, setConfig] = useState({
    concurrency: 50,
    duration: "30s",
    uses_tools: ["k6", "wrk"]
  });

  // Current active tool tab
  const [activeTab, setActiveTab] = useState<string>("k6");

  // Tool configuration dialog state
  const [openToolConfig, setOpenToolConfig] = useState(false);

  const [endpoints, setEndpoints] = useState<any[]>([]);
  const [selectedEndpoints, setSelectedEndpoints] = useState<string[]>([]);

  useEffect(() => {
    if (projectSlug && scanId) {
      axios.get(`/api/listEndpoints/`, {
        params: {
          project: projectSlug,
          scan_history: scanId,
        }
      })
      .then(response => {
        const results = response.data.results || response.data || [];
        setEndpoints(results);
      })
      .catch(error => {
        console.error("Failed to load endpoints for stress testing", error);
      });
    }
  }, [projectSlug, scanId]);

  // Tool-specific configurations (persisted per tool)
  const [toolConfigs, setToolConfigs] = useState<Record<string, any>>({
    k6: {
      vus: 50,
      duration: "30s",
      attack_type: "http_get", // "http_get" | "slowloris"
      rps: "",
      insecure_skip_tls: true,
      no_connection_reuse: false,
      http_debug: ""
    },
    wrk: {
      threads: "2",
      connections: 50,
      duration: "30s",
      latency: true,
      timeout: "",
      headers: []
    },
    hping3: {
      attack_mode: "syn", // "syn" | "udp" | "icmp"
      port: "80",
      rate: "fast", // "fast" | "faster" | "flood"
      data_size: ""
    },
    locust: {
      users: 50,
      spawn_rate: 10,
      run_time: "30s",
      loglevel: "ERROR"
    }
  });

  const [reportTemplate, setReportTemplate] = useState('modern');
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [openReportDialog, setOpenReportDialog] = useState(false);

  // Dynamic tabs rendering based on selected uses_tools config
  const activeTools = useMemo(() => {
    return config.uses_tools.length > 0 ? config.uses_tools : ["k6"];
  }, [config.uses_tools]);

  // Handle setting active tab if selected tab is removed
  React.useEffect(() => {
    if (!activeTools.includes(activeTab)) {
      setActiveTab(activeTools[0]);
    }
  }, [activeTools, activeTab]);

  // Isolated telemetry data filtered by active tool tab
  const filteredTelemetry = useMemo(() => {
    return telemetryData.filter(d => !d.tool || d.tool.toLowerCase() === activeTab.toLowerCase());
  }, [telemetryData, activeTab]);

  const handleStart = async () => {
    clearTelemetry();
    setScanning(true);

    // Merge global settings into target active tool configs
    const updatedToolConfigs = { ...toolConfigs };
    
    // Concurrency/duration mappings
    if (updatedToolConfigs.k6) {
      updatedToolConfigs.k6.vus = config.concurrency;
      updatedToolConfigs.k6.duration = config.duration;
    }
    if (updatedToolConfigs.wrk) {
      updatedToolConfigs.wrk.connections = config.concurrency;
      updatedToolConfigs.wrk.duration = config.duration;
    }
    if (updatedToolConfigs.locust) {
      updatedToolConfigs.locust.users = config.concurrency;
      updatedToolConfigs.locust.run_time = config.duration;
    }

    const startPayload: any = {
      action: 'start',
      config: {
        concurrency: config.concurrency,
        duration: config.duration,
        uses_tools: config.uses_tools.length > 0 ? config.uses_tools : [activeTab],
        selected_endpoints: selectedEndpoints,
      }
    };

    // Add configs for each selected tool
    const toolsToRun = config.uses_tools.length > 0 ? config.uses_tools : [activeTab];
    toolsToRun.forEach((tool: string) => {
      if (updatedToolConfigs[tool]) {
        startPayload.config[`${tool}_config`] = updatedToolConfigs[tool];
      }
    });

    try {
      await axios.post(`/api/stress/${scanId}/control/`, startPayload);
    } catch (error) {
      console.error("Failed to start stress test", error);
      setScanning(false);
    }
  };

  const handleStop = async () => {
    setIsStopping(true);
    try {
      await axios.post(`/api/stress/${scanId}/control/`, { action: 'stop' });
      setScanning(false);
    } catch (error) {
      console.error("Failed to stop stress test", error);
    } finally {
      setIsStopping(false);
    }
  };
  
  const handleGenerateReport = async () => {
    setIsGeneratingReport(true);
    try {
      const response = await axios.get(`/scan/create_report/${scanId}`, {
        params: {
          report_type: 'stress_test',
          report_template: reportTemplate === 'cyber_pro' ? 'stress_cyber_pro' : 'stress_modern'
        }
      });
      if (response.data.status) {
        alert("Stress Test Report generation started!");
      }
    } catch (error) {
      console.error("Failed to generate report", error);
    } finally {
      setIsGeneratingReport(false);
      setOpenReportDialog(false);
    }
  };

  // ECharts Configurations
  const latencyOption = useMemo(() => {
    let data = filteredTelemetry
      .filter(p => (p.avg_latency || p.latency) && p.timestamp)
      .map(p => [p.timestamp * 1000, p.avg_latency || p.latency]);

    const commandPoint = filteredTelemetry.find(p => p.type === 'command');
    if (commandPoint && commandPoint.timestamp) {
      const startTime = commandPoint.timestamp * 1000;
      if (data.length > 0 && !data.some(d => d[0] === startTime)) {
        data = [[startTime, undefined], ...data];
      }
    }

    return {
      backgroundColor: 'transparent',
      animation: false,
      title: { 
        text: 'REAL-TIME LATENCY (ms)', 
        textStyle: { 
          color: theme.palette.primary.main, 
          fontFamily: 'Orbitron', 
          fontSize: 12,
          fontWeight: 800,
          letterSpacing: 1
        } 
      },
      tooltip: { 
        trigger: 'axis',
        backgroundColor: 'rgba(5, 5, 10, 0.95)',
        borderColor: alpha(theme.palette.primary.main, 0.3),
        textStyle: { color: '#fff', fontSize: 11, fontFamily: 'monospace' },
        borderWidth: 1,
        borderRadius: 4
      },
      grid: { top: 60, bottom: 40, left: 50, right: 20 },
      xAxis: { 
        type: 'time',
        splitLine: { show: false },
        axisLine: { lineStyle: { color: alpha(theme.palette.text.primary, 0.1) } },
        axisLabel: { color: alpha(theme.palette.text.primary, 0.4), fontSize: 10 }
      },
      yAxis: { 
        type: 'value',
        splitLine: { lineStyle: { color: alpha(theme.palette.text.primary, 0.05) } },
        axisLine: { show: false },
        axisLabel: { color: alpha(theme.palette.text.primary, 0.4), fontSize: 10 }
      },
      series: [{
        name: 'Avg Latency',
        type: 'line',
        smooth: true,
        showSymbol: true,
        symbolSize: 6,
        data: data,
        itemStyle: { color: theme.palette.primary.main },
        lineStyle: { width: 3, shadowBlur: 10, shadowColor: alpha(theme.palette.primary.main, 0.5) },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: alpha(theme.palette.primary.main, 0.25) }, 
              { offset: 1, color: 'rgba(0, 0, 0, 0)' }
            ]
          }
        }
      }]
    };
  }, [filteredTelemetry, theme.palette.primary.main]);

  const rpsOption = useMemo(() => {
    let data = filteredTelemetry
      .filter(p => p.throughput_rps && p.timestamp)
      .map(p => [p.timestamp * 1000, p.throughput_rps]);

    const commandPoint = filteredTelemetry.find(p => p.type === 'command');
    if (commandPoint && commandPoint.timestamp) {
      const startTime = commandPoint.timestamp * 1000;
      if (data.length > 0 && !data.some(d => d[0] === startTime)) {
        data = [[startTime, undefined], ...data];
      }
    }

    return {
      backgroundColor: 'transparent',
      animation: false,
      title: { 
        text: 'THROUGHPUT (RPS)', 
        textStyle: { 
          color: '#6be6c1', 
          fontFamily: 'Orbitron', 
          fontSize: 12,
          fontWeight: 800,
          letterSpacing: 1
        } 
      },
      tooltip: { 
        trigger: 'axis',
        backgroundColor: 'rgba(5, 5, 10, 0.95)',
        borderColor: 'rgba(107, 230, 193, 0.3)',
        textStyle: { color: '#fff', fontSize: 11, fontFamily: 'monospace' },
        borderWidth: 1
      },
      grid: { top: 60, bottom: 40, left: 50, right: 20 },
      xAxis: { 
        type: 'time', 
        splitLine: { show: false },
        axisLine: { lineStyle: { color: alpha(theme.palette.text.primary, 0.1) } },
        axisLabel: { color: alpha(theme.palette.text.primary, 0.4), fontSize: 10 }
      },
      yAxis: { 
        type: 'value', 
        splitLine: { lineStyle: { color: alpha(theme.palette.text.primary, 0.05) } },
        axisLabel: { color: alpha(theme.palette.text.primary, 0.4), fontSize: 10 }
      },
      series: [{
        name: 'RPS',
        type: 'line',
        smooth: true,
        showSymbol: true,
        symbolSize: 6,
        data: data,
        itemStyle: { color: '#6be6c1' },
        lineStyle: { width: 3 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(107, 230, 193, 0.2)' }, 
              { offset: 1, color: 'rgba(0, 0, 0, 0)' }
            ]
          }
        }
      }]
    };
  }, [filteredTelemetry]);

  const heatmapOption = useMemo(() => {
    if (filteredTelemetry.length === 0) return { backgroundColor: 'transparent' };

    const validPoints = filteredTelemetry.filter(p => p.endpoint && p.timestamp);
    const endpoints = Array.from(new Set(validPoints.map(p => p.endpoint)));
    const timestamps = Array.from(new Set(validPoints.map(p => Math.floor(p.timestamp / 5) * 5))).sort();
    
    const heatmapData = validPoints.map(p => [
      timestamps.indexOf(Math.floor(p.timestamp / 5) * 5),
      endpoints.indexOf(p.endpoint),
      p.avg_latency || p.latency || 0
    ]).filter(d => d[0] !== -1 && d[1] !== -1);

    return {
      backgroundColor: 'transparent',
      animation: false,
      tooltip: { position: 'top' },
      grid: { height: '80%', top: '10%', right: '18%' },
      xAxis: { 
        type: 'category', 
        data: timestamps.map(t => {
          const date = new Date(t * 1000);
          return isNaN(date.getTime()) ? '??' : date.toLocaleTimeString();
        }),
        splitArea: { show: true }
      },
      yAxis: { 
        type: 'category', 
        data: endpoints.map(e => e.split('/').pop() || e),
        splitArea: { show: true }
      },
      visualMap: {
        min: 0,
        max: 1000,
        calculable: true,
        orient: 'vertical',
        right: '2%',
        top: 'center',
        inRange: { color: ['#10b981', '#facc15', '#ef4444'] }
      },
      series: [{
        name: 'Latency',
        type: 'heatmap',
        data: heatmapData,
        label: { show: false },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
      }]
    };
  }, [filteredTelemetry]);

  const getStatusConfig = () => {
    switch (wsStatus) {
      case 'connected': return { label: 'PIPELINE READY', color: '#10b981', icon: <Wifi size={14} />, pulse: true };
      case 'connecting': return { label: 'ESTABLISHING LINK...', color: '#facc15', icon: <Wifi size={14} />, pulse: true };
      case 'error': return { label: 'SIGNAL ERROR', color: '#ef4444', icon: <WifiOff size={14} />, pulse: false };
      default: return { label: 'PIPELINE OFFLINE', color: alpha('#fff', 0.3), icon: <WifiOff size={14} />, pulse: false };
    }
  };

  const statusConfig = getStatusConfig();

  // Handle side panel config updates dynamically
  const handleToolConfigChange = (toolName: string, key: string, value: any) => {
    setToolConfigs(prev => ({
      ...prev,
      [toolName]: {
        ...prev[toolName],
        [key]: value
      }
    }));
  };

  // Find the latest valid metrics by scanning backwards through filtered telemetry
  const latestMetrics = useMemo(() => {
    const metrics = {
      avg_latency: 0,
      throughput_rps: 0,
      error_rate: 0
    };
    
    // Find latest avg_latency or latency
    for (let i = filteredTelemetry.length - 1; i >= 0; i--) {
      const p = filteredTelemetry[i];
      if (p.avg_latency !== undefined || p.latency !== undefined) {
        metrics.avg_latency = p.avg_latency || p.latency || 0;
        break;
      }
    }

    // Find latest throughput_rps
    for (let i = filteredTelemetry.length - 1; i >= 0; i--) {
      const p = filteredTelemetry[i];
      if (p.throughput_rps !== undefined) {
        metrics.throughput_rps = p.throughput_rps;
        break;
      }
    }

    // Find latest error_rate
    for (let i = filteredTelemetry.length - 1; i >= 0; i--) {
      const p = filteredTelemetry[i];
      if (p.error_rate !== undefined) {
        metrics.error_rate = p.error_rate;
        break;
      }
    }

    return metrics;
  }, [filteredTelemetry]);

  return (
    <Box sx={{ p: { xs: 2, md: 4 } }}>
      {/* Header */}
      <Box sx={{ display: 'flex', flexDirection: { xs: 'column', lg: 'row' }, justifyContent: 'space-between', alignItems: { xs: 'flex-start', lg: 'center' }, gap: 3, mb: 6 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <IconButton 
            component={RouterLink} 
            to={`/${projectSlug}/scans`} 
            sx={{ 
              color: 'rgba(255,255,255,0.5)', 
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 2,
              '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.05), borderColor: theme.palette.primary.main }
            }}
          >
            <ArrowLeft size={20} />
          </IconButton>
          <Box>
            <Typography variant="h4" sx={{ 
              fontFamily: 'Orbitron', 
              fontWeight: 900, 
              color: '#fff', 
              letterSpacing: 4,
              textShadow: `0 0 20px ${alpha(theme.palette.primary.main, 0.3)}`
            }}>
              ADAPTIVE STRESS ANALYSIS
            </Typography>
            <Typography variant="body2" sx={{ color: alpha(theme.palette.primary.main, 0.7), fontFamily: 'Orbitron', fontSize: 10, letterSpacing: 2 }}>
              LIVE TELEMETRY PIPELINE // SCAN ID: {scanId}
            </Typography>
          </Box>
        </Box>
        
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          <Tooltip title={wsStatus === 'error' ? 'WebSocket connection failed. Retrying...' : 'Telemetry Pipeline Status'}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1.5, 
              px: 2, 
              py: 0.8,
              borderRadius: '20px',
              bgcolor: alpha(statusConfig.color, 0.1),
              border: `1px solid ${alpha(statusConfig.color, 0.2)}`,
              transition: 'all 0.3s ease'
            }}>
              <Box sx={{ 
                display: 'flex', 
                color: statusConfig.color,
                animation: statusConfig.pulse ? 'pulse 2s infinite' : 'none',
                '@keyframes pulse': {
                  '0%': { opacity: 1, transform: 'scale(1)' },
                  '50%': { opacity: 0.5, transform: 'scale(0.9)' },
                  '100%': { opacity: 1, transform: 'scale(1)' }
                }
              }}>
                {statusConfig.icon}
              </Box>
              <Typography sx={{ 
                fontFamily: 'Orbitron', 
                fontSize: 9, 
                fontWeight: 900, 
                color: statusConfig.color,
                letterSpacing: 1
              }}>
                {statusConfig.label}
              </Typography>
            </Box>
          </Tooltip>

          <Button 
            variant="outlined" 
            sx={{ 
              borderColor: alpha(theme.palette.text.primary, 0.1), 
              color: alpha(theme.palette.text.primary, 0.7),
              fontFamily: 'Orbitron',
              fontSize: '0.75rem',
              fontWeight: 700
            }}
            startIcon={<SettingsIcon size={16} />}
            onClick={() => setOpenSettings(true)}
          >
            ACTIVE TOOLS
          </Button>

          <Button 
            variant="outlined" 
            sx={{ 
              borderColor: alpha(theme.palette.primary.main, 0.2), 
              color: theme.palette.primary.main,
              fontFamily: 'Orbitron',
              fontSize: '0.75rem',
              fontWeight: 700
            }}
            startIcon={<Sliders size={16} />}
            onClick={() => setOpenToolConfig(true)}
          >
            {`CONFIGURE ${activeTab.toUpperCase()}`}
          </Button>

          <Button 
            variant="contained" 
            sx={{ 
              background: `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
              fontFamily: 'Orbitron',
              fontSize: '0.75rem',
              fontWeight: 900,
              px: 3,
              boxShadow: `0 0 20px ${alpha(theme.palette.primary.main, 0.4)}`,
              '&:hover': {
                boxShadow: `0 0 30px ${alpha(theme.palette.primary.main, 0.6)}`,
              },
              '&:disabled': { opacity: 0.3 }
            }}
            startIcon={<Play size={18} />}
            onClick={handleStart}
            disabled={isScanning}
          >
            EXECUTE TEST
          </Button>

          <Button 
            variant="contained" 
            sx={{ 
              background: 'linear-gradient(135deg, rgba(20, 15, 30, 0.75) 0%, rgba(10, 10, 15, 0.95) 100%)',
              backdropFilter: 'blur(25px) saturate(180%)',
              border: '1px solid rgba(255, 255, 255, 0.06)',
              color: '#8ba4c0',
              fontFamily: 'Orbitron',
              fontSize: '0.75rem',
              fontWeight: 900,
              px: 3,
              boxShadow: 'inset 0 0 15px rgba(0, 0, 0, 0.5)',
              '&:hover': {
                background: 'linear-gradient(135deg, rgba(30, 20, 45, 0.85) 0%, rgba(15, 15, 25, 0.98) 100%)',
                borderColor: 'rgba(0, 240, 255, 0.4)',
                color: '#fff',
                boxShadow: 'inset 0 0 15px rgba(0, 0, 0, 0.3), 0 0 10px rgba(0, 240, 255, 0.4)',
              }
            }}
            startIcon={<FileText size={18} />}
            onClick={() => setOpenReportDialog(true)}
          >
            GENERATE REPORT
          </Button>

          <Button 
            variant="contained" 
            sx={{ 
              background: '#ff003c', 
              fontFamily: 'Orbitron',
              fontSize: '0.75rem',
              fontWeight: 900,
              px: 3,
              '&:hover': { bgcolor: '#cc0030' }
            }}
            startIcon={isStopping ? <CircularProgress size={16} color="inherit" /> : <Square size={18} />}
            onClick={handleStop}
            disabled={!isScanning || isStopping}
          >
            KILL SWITCH
          </Button>
        </Box>
      </Box>

      {/* Dynamic Tabs Navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'rgba(255,255,255,0.05)', mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Tabs 
          value={activeTab} 
          onChange={(_, val) => setActiveTab(val)}
          textColor="primary"
          indicatorColor="primary"
          sx={{
            '& .MuiTabs-indicator': { height: 3, borderRadius: '3px 3px 0 0' },
            '& .MuiTab-root': {
              fontFamily: 'Orbitron',
              fontWeight: 700,
              fontSize: '0.85rem',
              color: 'rgba(255,255,255,0.4)',
              minWidth: 100,
              letterSpacing: 2,
              '&.Mui-selected': { color: '#00f3ff' }
            }
          }}
        >
          {activeTools.map((tool) => (
            <Tab key={tool} label={tool.toUpperCase()} value={tool} />
          ))}
        </Tabs>

        {isScanning && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CircularProgress size={14} color="primary" />
            <Typography variant="caption" sx={{ fontFamily: 'monospace', color: theme.palette.primary.main, fontWeight: 700 }}>
              TEST RUNNING IN BACKGROUND
            </Typography>
          </Box>
        )}
      </Box>

      {/* Main Grid: Sliding collapsible configurations next to charts (Approach 1) */}
      <Grid container spacing={4}>
        {/* KPI Panel Row */}
        <Grid size={{ xs: 12 }}>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 3 }}>
              <KpiCard 
                title="LATENCY AVG"
                value={latestMetrics.avg_latency}
                icon={Activity}
                color={theme.palette.primary.main}
                subtitle="Milliseconds"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <KpiCard 
                title="THROUGHPUT"
                value={latestMetrics.throughput_rps}
                icon={Zap}
                color="#6be6c1"
                subtitle="Req / Sec"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <KpiCard 
                title="ERROR RATE"
                value={latestMetrics.error_rate * 100}
                icon={AlertTriangle}
                color="#ff003c"
                subtitle="Percentage %"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <KpiCard 
                title="CONCURRENCY"
                value={config.concurrency}
                icon={Server}
                color="#facc15"
                subtitle="Virtual Users"
              />
            </Grid>
          </Grid>
        </Grid>

        {/* Left Column: ECharts Graphs (Latency, Throughput, Saturation stacked) */}
        <Grid size={{ xs: 12, lg: 6 }}>
          <Grid container spacing={4}>
            <Grid size={{ xs: 12 }}>
              <TacticalPanel 
                title={`${activeTab.toUpperCase()} LATENCY METRICS`} 
                icon={<Activity size={18} color={theme.palette.primary.main} />}
              >
                <ReactECharts key={`latency-${activeTab}`} option={latencyOption} style={{ height: '350px' }} theme="dark" notMerge={true} />
              </TacticalPanel>
            </Grid>

            <Grid size={{ xs: 12 }}>
              <TacticalPanel 
                title={`${activeTab.toUpperCase()} THROUGHPUT LOAD`} 
                icon={<Zap size={18} color="#6be6c1" />}
              >
                <ReactECharts key={`rps-${activeTab}`} option={rpsOption} style={{ height: '350px' }} theme="dark" notMerge={true} />
              </TacticalPanel>
            </Grid>

            <Grid size={{ xs: 12 }}>
              <TacticalPanel title={`${activeTab.toUpperCase()} ENDPOINT SATURATION`} icon={<Server size={18} color="#facc15" />}>
                <ReactECharts key={`heatmap-${activeTab}`} option={heatmapOption} style={{ height: '350px' }} theme="dark" notMerge={true} />
              </TacticalPanel>
            </Grid>
          </Grid>
        </Grid>

        {/* Right Column: Telemetry Log (50% Width, matching height of stacked graphs) */}
        <Grid size={{ xs: 12, lg: 6 }}>
          <TacticalPanel 
            title={`${activeTab.toUpperCase()} TELEMETRY LOG`} 
            icon={<Terminal size={18} color={theme.palette.primary.main} />}
            headerAction={
              <Button
                variant="outlined"
                size="small"
                startIcon={<Trash2 size={12} />}
                onClick={clearTelemetry}
                sx={{
                  borderColor: alpha(theme.palette.error.main, 0.35),
                  color: theme.palette.error.main,
                  fontFamily: 'Orbitron',
                  fontSize: '0.65rem',
                  fontWeight: 800,
                  px: 1.5,
                  py: 0.5,
                  borderRadius: '6px',
                  '&:hover': {
                    borderColor: theme.palette.error.main,
                    bgcolor: alpha(theme.palette.error.main, 0.1),
                    boxShadow: `0 0 10px ${alpha(theme.palette.error.main, 0.35)}`
                  }
                }}
              >
                CLEAR LOGS
              </Button>
            }
            sx={{ 
              height: { xs: '500px', lg: '1240px' }, 
              maxHeight: { xs: '500px', lg: '1240px' }, 
              display: 'flex', 
              flexDirection: 'column',
              '& .MuiCardContent-root': { 
                height: '100%', 
                display: 'flex', 
                flexDirection: 'column', 
                flexGrow: 1,
                pb: '16px !important',
                overflow: 'hidden'
              } 
            }}
          >
            <Box 
              sx={{ 
                flexGrow: 1, 
                overflowY: 'auto', 
                bgcolor: 'rgba(0,0,0,0.3)', 
                p: 1.5, 
                borderRadius: 2, 
                height: '100%', 
                minHeight: '400px',
                display: 'flex',
                flexDirection: 'column'
              }}
            >
              <List dense sx={{ flexGrow: 1 }}>
                {filteredTelemetry.slice(-150).reverse().map((p, i) => {
                  if (p.type === 'command') {
                    return (
                      <ListItem 
                        key={i} 
                        sx={{ 
                          bgcolor: alpha('#00f3ff', 0.05), 
                          borderLeft: '3px solid #00f3ff',
                          borderBottom: `1px solid ${alpha(theme.palette.text.primary, 0.05)}`,
                          mb: 0.5,
                          py: 1
                        }}
                      >
                        <ListItemIcon sx={{ minWidth: 30, color: '#00f3ff' }}>
                          <Terminal size={14} />
                        </ListItemIcon>
                        <ListItemText 
                          primary={`[SYSTEM EXEC] > ${p.command}`}
                          secondary={`Tool: ${p.tool ? p.tool.toUpperCase() : 'N/A'} | Target: ${p.endpoint || 'N/A'}`}
                          slotProps={{
                            primary: { sx: { fontSize: 10, color: '#00f3ff', fontFamily: 'monospace', fontWeight: 700, wordBreak: 'break-all' } },
                            secondary: { sx: { fontSize: 9, color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' } }
                          }}
                        />
                      </ListItem>
                    );
                  } else if (p.type === 'log') {
                    return (
                      <ListItem 
                        key={i} 
                        sx={{ 
                          borderBottom: `1px solid ${alpha(theme.palette.text.primary, 0.02)}`,
                          py: 0.2
                        }}
                      >
                        <ListItemText 
                          primary={p.line}
                          slotProps={{
                            primary: { sx: { fontSize: 9, color: 'rgba(255,255,255,0.85)', fontFamily: 'monospace', whiteSpace: 'pre-wrap', pl: 3.5 } }
                          }}
                        />
                      </ListItem>
                    );
                  } else {
                    return (
                      <ListItem key={i} sx={{ borderBottom: `1px solid ${alpha(theme.palette.text.primary, 0.05)}` }}>
                        <ListItemIcon sx={{ minWidth: 30 }}>
                          <Clock size={12} color={alpha(theme.palette.text.primary, 0.3)} />
                        </ListItemIcon>
                        <ListItemText 
                          primary={`${p.tool ? p.tool.toUpperCase() : 'N/A'} -> ${(p.endpoint || '').split('/').pop()}`}
                          secondary={`Latency: ${p.avg_latency || p.latency || 0}ms | Throughput: ${p.throughput_rps || 0} RPS`}
                          slotProps={{
                            primary: { sx: { fontSize: 10, color: '#fff', fontFamily: 'monospace', fontWeight: 600 } },
                            secondary: { sx: { fontSize: 9, color: alpha(theme.palette.text.primary, 0.4), fontFamily: 'monospace' } }
                          }}
                        />
                      </ListItem>
                    );
                  }
                })}
                {filteredTelemetry.length === 0 && (
                  <Box sx={{ py: 10, textAlign: 'center', opacity: 0.3 }}>
                    <Terminal size={40} style={{ margin: '0 auto 16px', display: 'block' }} />
                    <Typography variant="caption" sx={{ fontFamily: 'Orbitron', letterSpacing: 2 }}>
                      WAITING FOR DATA STREAM...
                    </Typography>
                  </Box>
                )}
              </List>
            </Box>
          </TacticalPanel>
        </Grid>
      </Grid>

      {/* Global Config Settings Dialog */}
      <Dialog open={openSettings} onClose={() => setOpenSettings(false)} slotProps={{ paper: { sx: { bgcolor: '#1a1a1a', color: '#fff' } } }}>
        <DialogTitle sx={{ fontFamily: 'Orbitron', color: '#00f3ff' }}>GLOBAL TEST CONFIGURATION</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 2 }}>
            <TextField 
              label="Default Concurrency (VUs)" 
              type="number" 
              fullWidth 
              value={config.concurrency}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfig({...config, concurrency: parseInt(e.target.value)})}
              slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
              sx={{ input: { color: '#fff' } }}
            />
            <TextField 
              label="Default Duration (e.g. 30s, 1m)" 
              fullWidth 
              value={config.duration}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfig({...config, duration: e.target.value})}
              slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
              sx={{ input: { color: '#fff' } }}
            />
            <FormControl fullWidth>
              <InputLabel sx={{ color: 'rgba(255,255,255,0.5)' }}>Stress Tools to Expose</InputLabel>
              <Select
                multiple
                value={config.uses_tools}
                onChange={(e) => setConfig({...config, uses_tools: typeof e.target.value === 'string' ? e.target.value.split(',') : e.target.value})}
                input={<OutlinedInput label="Stress Tools to Expose" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} sx={{ bgcolor: '#00f3ff', color: '#000', height: 20, fontSize: 10 }} />
                    ))}
                  </Box>
                )}
                sx={{ color: '#fff', '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1)' } }}
              >
                {['k6', 'wrk', 'hping3', 'locust'].map((name) => (
                  <MenuItem key={name} value={name}>{name.toUpperCase()}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel sx={{ color: 'rgba(255,255,255,0.5)' }}>Target Specific Endpoints (Optional)</InputLabel>
              <Select
                multiple
                value={selectedEndpoints}
                onChange={(e) => setSelectedEndpoints(typeof e.target.value === 'string' ? e.target.value.split(',') : e.target.value)}
                input={<OutlinedInput label="Target Specific Endpoints (Optional)" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} sx={{ bgcolor: '#ff5f1f', color: '#fff', height: 20, fontSize: 10 }} />
                    ))}
                  </Box>
                )}
                sx={{ color: '#fff', '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1)' } }}
              >
                {endpoints.map((ep) => (
                  <MenuItem key={ep.id || ep.http_url} value={ep.http_url}>
                    <Checkbox checked={selectedEndpoints.indexOf(ep.http_url) > -1} sx={{ color: '#00f3ff', '&.Mui-checked': { color: '#00f3ff' } }} />
                    <ListItemText primary={ep.http_url} secondary={ep.http_status ? `Status: ${ep.http_status}` : ''} sx={{ color: '#fff', '.MuiListItemText-secondary': { color: 'rgba(255,255,255,0.4)' } }} />
                  </MenuItem>
                ))}
                {endpoints.length === 0 && (
                  <MenuItem disabled sx={{ color: 'rgba(255,255,255,0.3)' }}>No found endpoints available</MenuItem>
                )}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setOpenSettings(false)} sx={{ color: 'rgba(255,255,255,0.5)' }}>CANCEL</Button>
          <Button onClick={() => setOpenSettings(false)} variant="contained" sx={{ bgcolor: '#00f3ff', color: '#000', fontWeight: 'bold' }}>APPLY</Button>
        </DialogActions>
      </Dialog>

      {/* Tool-Specific Config Dialog */}
      <Dialog 
        open={openToolConfig} 
        onClose={() => setOpenToolConfig(false)} 
        slotProps={{ 
          paper: { 
            sx: { 
              bgcolor: '#121214', 
              color: '#fff', 
              border: '1px solid rgba(0, 243, 255, 0.2)',
              boxShadow: '0 0 30px rgba(0, 243, 255, 0.15)',
              minWidth: { xs: '90%', sm: '480px' } 
            } 
          } 
        }}
      >
        <DialogTitle sx={{ fontFamily: 'Orbitron', color: '#00f3ff', letterSpacing: 1.5, pb: 1 }}>
          {`${activeTab.toUpperCase()} TOOL CONFIGURATION`}
        </DialogTitle>
        <DialogContent dividers sx={{ borderColor: 'rgba(255,255,255,0.05)', py: 3 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {activeTab === 'k6' && (
              <>
                <TextField 
                  label="Virtual Users (VUs)" 
                  type="number" 
                  fullWidth 
                  value={toolConfigs.k6.vus}
                  onChange={(e) => setToolConfigs({
                    ...toolConfigs,
                    k6: { ...toolConfigs.k6, vus: parseInt(e.target.value) || 0 }
                  })}
                  slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
                  sx={{ input: { color: '#fff' }, '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' } } }}
                />
                <TextField 
                  label="Duration (e.g. 30s, 1m)" 
                  fullWidth 
                  value={toolConfigs.k6.duration}
                  onChange={(e) => setToolConfigs({
                    ...toolConfigs,
                    k6: { ...toolConfigs.k6, duration: e.target.value }
                  })}
                  slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
                  sx={{ input: { color: '#fff' }, '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' } } }}
                />
                <FormControl fullWidth>
                  <InputLabel sx={{ color: 'rgba(255,255,255,0.5)' }}>Attack Type</InputLabel>
                  <Select
                    value={toolConfigs.k6.attack_type}
                    onChange={(e) => setToolConfigs({
                      ...toolConfigs,
                      k6: { ...toolConfigs.k6, attack_type: e.target.value }
                    })}
                    input={<OutlinedInput label="Attack Type" />}
                    sx={{ color: '#fff', '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1)' } }}
                  >
                    <MenuItem value="http_get">HTTP GET Load (Standard)</MenuItem>
                    <MenuItem value="slowloris">Slowloris Exhaustion (L4/L7)</MenuItem>
                  </Select>
                </FormControl>
                <TextField 
                  label="Requests Per Second Rate Limit (Optional)" 
                  type="number" 
                  fullWidth 
                  value={toolConfigs.k6.rps}
                  onChange={(e) => setToolConfigs({
                    ...toolConfigs,
                    k6: { ...toolConfigs.k6, rps: e.target.value }
                  })}
                  slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
                  sx={{ input: { color: '#fff' }, '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' } } }}
                />
                <FormControlLabel
                  control={
                    <Switch 
                      checked={toolConfigs.k6.insecure_skip_tls} 
                      onChange={(e) => setToolConfigs({
                        ...toolConfigs,
                        k6: { ...toolConfigs.k6, insecure_skip_tls: e.target.checked }
                      })}
                    />
                  }
                  label={<Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>Skip TLS Verification (--insecure-skip-tls)</Typography>}
                />
                <FormControlLabel
                  control={
                    <Switch 
                      checked={toolConfigs.k6.no_connection_reuse} 
                      onChange={(e) => setToolConfigs({
                        ...toolConfigs,
                        k6: { ...toolConfigs.k6, no_connection_reuse: e.target.checked }
                      })}
                    />
                  }
                  label={<Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>Disable Connection Reuse (--no-connection-reuse)</Typography>}
                />
                <FormControlLabel
                  control={
                    <Switch 
                      checked={!!toolConfigs.k6.http_debug} 
                      onChange={(e) => setToolConfigs({
                        ...toolConfigs,
                        k6: { ...toolConfigs.k6, http_debug: e.target.checked ? "true" : "" }
                      })}
                    />
                  }
                  label={<Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>Enable HTTP Debugging (--http-debug)</Typography>}
                />
              </>
            )}

            {activeTab === 'wrk' && (
              <>
                <TextField 
                  label="Threads Count" 
                  type="number" 
                  fullWidth 
                  value={toolConfigs.wrk.threads}
                  onChange={(e) => setToolConfigs({
                    ...toolConfigs,
                    wrk: { ...toolConfigs.wrk, threads: e.target.value }
                  })}
                  slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
                  sx={{ input: { color: '#fff' }, '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' } } }}
                />
                <TextField 
                  label="Connections to Keep Open" 
                  type="number" 
                  fullWidth 
                  value={toolConfigs.wrk.connections}
                  onChange={(e) => setToolConfigs({
                    ...toolConfigs,
                    wrk: { ...toolConfigs.wrk, connections: parseInt(e.target.value) || 0 }
                  })}
                  slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
                  sx={{ input: { color: '#fff' }, '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' } } }}
                />
                <TextField 
                  label="Duration (e.g. 30s, 1m)" 
                  fullWidth 
                  value={toolConfigs.wrk.duration}
                  onChange={(e) => setToolConfigs({
                    ...toolConfigs,
                    wrk: { ...toolConfigs.wrk, duration: e.target.value }
                  })}
                  slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
                  sx={{ input: { color: '#fff' }, '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' } } }}
                />
                <TextField 
                  label="Timeout Threshold (e.g. 2s)" 
                  fullWidth 
                  value={toolConfigs.wrk.timeout}
                  onChange={(e) => setToolConfigs({
                    ...toolConfigs,
                    wrk: { ...toolConfigs.wrk, timeout: e.target.value }
                  })}
                  slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
                  sx={{ input: { color: '#fff' }, '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' } } }}
                />
                <FormControlLabel
                  control={
                    <Switch 
                      checked={toolConfigs.wrk.latency} 
                      onChange={(e) => setToolConfigs({
                        ...toolConfigs,
                        wrk: { ...toolConfigs.wrk, latency: e.target.checked }
                      })}
                    />
                  }
                  label={<Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>Record & Print Detailed Latency Statistics</Typography>}
                />
              </>
            )}

            {activeTab === 'hping3' && (
              <>
                <FormControl fullWidth>
                  <InputLabel sx={{ color: 'rgba(255,255,255,0.5)' }}>Attack Mode</InputLabel>
                  <Select
                    value={toolConfigs.hping3.attack_mode}
                    onChange={(e) => setToolConfigs({
                      ...toolConfigs,
                      hping3: { ...toolConfigs.hping3, attack_mode: e.target.value }
                    })}
                    input={<OutlinedInput label="Attack Mode" />}
                    sx={{ color: '#fff', '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1)' } }}
                  >
                    <MenuItem value="syn">SYN Flood (L4 Exhaustion)</MenuItem>
                    <MenuItem value="udp">UDP Flood (Bandwidth Exhaustion)</MenuItem>
                    <MenuItem value="icmp">ICMP Ping Flood</MenuItem>
                  </Select>
                </FormControl>
                <TextField 
                  label="Target Port" 
                  type="number" 
                  fullWidth 
                  value={toolConfigs.hping3.port}
                  onChange={(e) => setToolConfigs({
                    ...toolConfigs,
                    hping3: { ...toolConfigs.hping3, port: e.target.value }
                  })}
                  slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
                  sx={{ input: { color: '#fff' }, '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' } } }}
                />
                <FormControl fullWidth>
                  <InputLabel sx={{ color: 'rgba(255,255,255,0.5)' }}>Packet Rate</InputLabel>
                  <Select
                    value={toolConfigs.hping3.rate}
                    onChange={(e) => setToolConfigs({
                      ...toolConfigs,
                      hping3: { ...toolConfigs.hping3, rate: e.target.value }
                    })}
                    input={<OutlinedInput label="Packet Rate" />}
                    sx={{ color: '#fff', '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1)' } }}
                  >
                    <MenuItem value="fast">Fast (10 packets/sec)</MenuItem>
                    <MenuItem value="faster">Faster (100 packets/sec)</MenuItem>
                    <MenuItem value="flood">Flood (As fast as possible! Warning: High resource load)</MenuItem>
                  </Select>
                </FormControl>
                <TextField 
                  label="Packet Payload Size (Bytes)" 
                  type="number" 
                  fullWidth 
                  value={toolConfigs.hping3.data_size}
                  onChange={(e) => setToolConfigs({
                    ...toolConfigs,
                    hping3: { ...toolConfigs.hping3, data_size: e.target.value }
                  })}
                  slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
                  sx={{ input: { color: '#fff' }, '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' } } }}
                />
              </>
            )}

            {activeTab === 'locust' && (
              <>
                <TextField 
                  label="Number of Concurrent Users" 
                  type="number" 
                  fullWidth 
                  value={toolConfigs.locust.users}
                  onChange={(e) => setToolConfigs({
                    ...toolConfigs,
                    locust: { ...toolConfigs.locust, users: parseInt(e.target.value) || 0 }
                  })}
                  slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
                  sx={{ input: { color: '#fff' }, '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' } } }}
                />
                <TextField 
                  label="Spawn Rate (Users started/second)" 
                  type="number" 
                  fullWidth 
                  value={toolConfigs.locust.spawn_rate}
                  onChange={(e) => setToolConfigs({
                    ...toolConfigs,
                    locust: { ...toolConfigs.locust, spawn_rate: parseInt(e.target.value) || 0 }
                  })}
                  slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
                  sx={{ input: { color: '#fff' }, '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' } } }}
                />
                <TextField 
                  label="Run Time (e.g. 30s, 1m)" 
                  fullWidth 
                  value={toolConfigs.locust.run_time}
                  onChange={(e) => setToolConfigs({
                    ...toolConfigs,
                    locust: { ...toolConfigs.locust, run_time: e.target.value }
                  })}
                  slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
                  sx={{ input: { color: '#fff' }, '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' } } }}
                />
                <FormControl fullWidth>
                  <InputLabel sx={{ color: 'rgba(255,255,255,0.5)' }}>Log Level</InputLabel>
                  <Select
                    value={toolConfigs.locust.loglevel}
                    onChange={(e) => setToolConfigs({
                      ...toolConfigs,
                      locust: { ...toolConfigs.locust, loglevel: e.target.value }
                    })}
                    input={<OutlinedInput label="Log Level" />}
                    sx={{ color: '#fff', '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1)' } }}
                  >
                    <MenuItem value="DEBUG">DEBUG</MenuItem>
                    <MenuItem value="INFO">INFO</MenuItem>
                    <MenuItem value="WARNING">WARNING</MenuItem>
                    <MenuItem value="ERROR">ERROR</MenuItem>
                  </Select>
                </FormControl>
              </>
            )}
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setOpenToolConfig(false)} sx={{ color: 'rgba(255,255,255,0.5)', fontFamily: 'Orbitron', letterSpacing: 1 }}>
            CLOSE
          </Button>
          <Button 
            onClick={() => setOpenToolConfig(false)} 
            variant="contained" 
            sx={{ 
              bgcolor: '#00f3ff', 
              color: '#000', 
              fontWeight: 'bold', 
              fontFamily: 'Orbitron', 
              letterSpacing: 1,
              boxShadow: '0 0 10px rgba(0, 243, 255, 0.3)'
            }}
          >
            SAVE CONFIGURATION
          </Button>
        </DialogActions>
      </Dialog>

      {/* Report Generation Dialog */}
      <Dialog open={openReportDialog} onClose={() => setOpenReportDialog(false)} slotProps={{ paper: { sx: { bgcolor: '#1a1a1a', color: '#fff', minWidth: '400px' } } }}>
        <DialogTitle sx={{ fontFamily: 'Orbitron', color: '#00f3ff' }}>GENERATE PERFORMANCE REPORT</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 2 }}>
            <Typography variant="body2" sx={{ opacity: 0.7 }}>
              Select a visual template for your stress test intelligence report.
            </Typography>
            <FormControl fullWidth>
              <InputLabel sx={{ color: 'rgba(255,255,255,0.5)' }}>Template</InputLabel>
              <Select
                value={reportTemplate}
                onChange={(e) => setReportTemplate(e.target.value)}
                input={<OutlinedInput label="Template" />}
                sx={{ color: '#fff', '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1)' } }}
              >
                <MenuItem value="modern">Modern Clean (Minimalist)</MenuItem>
                <MenuItem value="cyber_pro">Cyber Pro (High-Contrast)</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setOpenReportDialog(false)} sx={{ color: 'rgba(255,255,255,0.5)' }}>CANCEL</Button>
          <Button 
            onClick={handleGenerateReport} 
            variant="contained" 
            disabled={isGeneratingReport}
            sx={{ bgcolor: '#00f3ff', color: '#000', fontWeight: 'bold' }}
            startIcon={isGeneratingReport ? <CircularProgress size={16} color="inherit" /> : <Download size={16} />}
          >
            {isGeneratingReport ? 'GENERATING...' : 'GENERATE PDF'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Floating Action Button (FAB) for quick configuration */}
      <Tooltip title={`Configure ${activeTab.toUpperCase()}`} placement="left">
        <Fab 
          color="primary" 
          aria-label="configure" 
          onClick={() => setOpenToolConfig(true)}
          sx={{ 
            position: 'fixed', 
            bottom: 32, 
            right: 32, 
            bgcolor: 'rgba(18, 18, 20, 0.8)',
            backdropFilter: 'blur(10px)',
            color: '#00f3ff',
            border: '1px solid rgba(0, 243, 255, 0.3)',
            boxShadow: '0 0 20px rgba(0, 243, 255, 0.2)',
            zIndex: 1000,
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            '&:hover': {
              bgcolor: 'rgba(0, 243, 255, 0.1)',
              borderColor: '#00f3ff',
              boxShadow: '0 0 30px rgba(0, 243, 255, 0.4)',
              transform: 'scale(1.1) rotate(90deg)'
            }
          }}
        >
          <Sliders size={20} />
        </Fab>
      </Tooltip>
    </Box>
  );
};
