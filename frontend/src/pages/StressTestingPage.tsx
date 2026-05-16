import React, { useState, useMemo } from 'react';
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
  Tooltip
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
  WifiOff
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
  const [config, setConfig] = useState({
    concurrency: 50,
    duration: "30s",
    uses_tools: ["k6"]
  });
  const [reportTemplate, setReportTemplate] = useState('modern');
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [openReportDialog, setOpenReportDialog] = useState(false);

  const handleStart = async () => {
    clearTelemetry();
    setScanning(true);
    try {
      await axios.post(`/api/stress/${scanId}/control/`, { 
        action: 'start', 
        config: config 
      });
    } catch (error) {
      console.error("Failed to start stress test", error);
      setScanning(false);
    }
  };

  const handleStop = async () => {
    setIsStopping(true);
    try {
      await axios.post(`/api/stress/${scanId}/control/`, { action: 'stop' });
    } catch (error) {
      console.error("Failed to stop stress test", error);
    } finally {
      setIsStopping(false);
    }
  };
  
  const handleGenerateReport = async () => {
    setIsGeneratingReport(true);
    try {
      const response = await axios.get(`/startScan/create_report/${scanId}`, {
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

  const latencyOption = useMemo(() => {
    const data = telemetryData
      .filter(p => (p.avg_latency || p.latency) && p.timestamp)
      .map(p => [p.timestamp * 1000, p.avg_latency || p.latency]);

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
        showSymbol: false,
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
  }, [telemetryData, theme.palette.primary.main]);

  const rpsOption = useMemo(() => {
    const data = telemetryData
      .filter(p => p.throughput_rps && p.timestamp)
      .map(p => [p.timestamp * 1000, p.throughput_rps]);

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
        showSymbol: false,
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
  }, [telemetryData]);

  const heatmapOption = useMemo(() => {
    if (telemetryData.length === 0) return { backgroundColor: 'transparent' };

    const validPoints = telemetryData.filter(p => p.endpoint && p.timestamp);
    const endpoints = Array.from(new Set(validPoints.map(p => p.endpoint)));
    const timestamps = Array.from(new Set(validPoints.map(p => Math.floor(p.timestamp / 5) * 5))).sort(); // 5s buckets
    
    const heatmapData = validPoints.map(p => [
      timestamps.indexOf(Math.floor(p.timestamp / 5) * 5),
      endpoints.indexOf(p.endpoint),
      p.avg_latency || p.latency || 0
    ]).filter(d => d[0] !== -1 && d[1] !== -1);

    return {
      backgroundColor: 'transparent',
      animation: false,
      tooltip: { position: 'top' },
      grid: { height: '80%', top: '10%', right: '10%' },
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
        right: '0%',
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
  }, [telemetryData]);

  const getStatusConfig = () => {
    switch (wsStatus) {
      case 'connected': return { label: 'PIPELINE_READY', color: '#10b981', icon: <Wifi size={14} />, pulse: true };
      case 'connecting': return { label: 'ESTABLISHING_LINK...', color: '#facc15', icon: <Wifi size={14} />, pulse: true };
      case 'error': return { label: 'SIGNAL_ERROR', color: '#ef4444', icon: <WifiOff size={14} />, pulse: false };
      default: return { label: 'PIPELINE_OFFLINE', color: alpha('#fff', 0.3), icon: <WifiOff size={14} />, pulse: false };
    }
  };

  const statusConfig = getStatusConfig();

  return (
    <Box sx={{ p: { xs: 2, md: 4 } }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 6 }}>
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
              ADAPTIVE_STRESS_ANALYSIS
            </Typography>
            <Typography variant="body2" sx={{ color: alpha(theme.palette.primary.main, 0.7), fontFamily: 'Orbitron', fontSize: 10, letterSpacing: 2 }}>
              LIVE_TELEMETRY_PIPELINE // SCAN_ID: {scanId}
            </Typography>
          </Box>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Tooltip title={wsStatus === 'error' ? 'WebSocket connection failed. Retrying...' : 'Telemetry Pipeline Status'}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1.5, 
              mr: 2, 
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
            CONFIGURE
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
            EXECUTE_TEST
          </Button>
          <Button 
            variant="contained" 
            sx={{ 
              background: `linear-gradient(45deg, ${theme.palette.secondary.main}, ${theme.palette.secondary.dark})`,
              fontFamily: 'Orbitron',
              fontSize: '0.75rem',
              fontWeight: 900,
              px: 3,
              boxShadow: `0 0 20px ${alpha(theme.palette.secondary.main, 0.2)}`,
              '&:hover': {
                boxShadow: `0 0 30px ${alpha(theme.palette.secondary.main, 0.4)}`,
              }
            }}
            startIcon={<FileText size={18} />}
            onClick={() => setOpenReportDialog(true)}
          >
            GENERATE_REPORT
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
            KILL_SWITCH
          </Button>
        </Box>
      </Box>

      {/* Main Grid */}
      <Grid container spacing={4}>
        {/* KPI Row */}
        <Grid size={{ xs: 12 }}>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 3 }}>
              <KpiCard 
                title="LATENCY_AVG"
                value={telemetryData.length > 0 ? telemetryData[telemetryData.length-1].avg_latency || 0 : 0}
                icon={Activity}
                color={theme.palette.primary.main}
                subtitle="Milliseconds"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <KpiCard 
                title="THROUGHPUT"
                value={telemetryData.length > 0 ? telemetryData[telemetryData.length-1].throughput_rps || 0 : 0}
                icon={Zap}
                color="#6be6c1"
                subtitle="Req / Sec"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <KpiCard 
                title="ERROR_RATE"
                value={telemetryData.length > 0 ? (telemetryData[telemetryData.length-1].error_rate || 0) * 100 : 0}
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

        {/* Metrics, Logs & Throughput Row */}
        <Grid size={{ xs: 12, lg: 4 }}>
          <TacticalPanel 
            title="LATENCY_METRICS" 
            icon={<Activity size={18} color={theme.palette.primary.main} />}
            sx={{ height: '100%' }}
          >
            <ReactECharts key={`latency-${scanId}`} option={latencyOption} style={{ height: '400px' }} theme="dark" notMerge={true} />
          </TacticalPanel>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <TacticalPanel 
            title="TELEMETRY_LOG" 
            icon={<Terminal size={18} color={theme.palette.primary.main} />}
            sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}
          >
            <Box sx={{ flexGrow: 1, overflowY: 'auto', bgcolor: 'rgba(0,0,0,0.3)', p: 1, borderRadius: 2, height: '400px' }}>
              <List dense>
                {telemetryData.slice(-100).reverse().map((p, i) => (
                  <ListItem key={i} sx={{ borderBottom: `1px solid ${alpha(theme.palette.text.primary, 0.05)}` }}>
                    <ListItemIcon sx={{ minWidth: 30 }}>
                      <Clock size={12} color={alpha(theme.palette.text.primary, 0.3)} />
                    </ListItemIcon>
                    <ListItemText 
                      primary={`${p.tool.toUpperCase()} -> ${p.endpoint.split('/').pop()}`}
                      secondary={`Latency: ${p.avg_latency || p.latency}ms | Status: OK`}
                      slotProps={{
                        primary: { sx: { fontSize: 10, color: '#fff', fontFamily: 'monospace', fontWeight: 600 } },
                        secondary: { sx: { fontSize: 9, color: alpha(theme.palette.text.primary, 0.4), fontFamily: 'monospace' } }
                      }}
                    />
                  </ListItem>
                ))}
                {telemetryData.length === 0 && (
                  <Box sx={{ py: 10, textAlign: 'center', opacity: 0.3 }}>
                    <Terminal size={40} style={{ margin: '0 auto 16px', display: 'block' }} />
                    <Typography variant="caption" sx={{ fontFamily: 'Orbitron', letterSpacing: 2 }}>
                      WAITING_FOR_DATA_STREAM...
                    </Typography>
                  </Box>
                )}
              </List>
            </Box>
          </TacticalPanel>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <TacticalPanel 
            title="THROUGHPUT_LOAD" 
            icon={<Zap size={18} color="#6be6c1" />}
            sx={{ height: '100%' }}
          >
            <ReactECharts key={`rps-${scanId}`} option={rpsOption} style={{ height: '400px' }} theme="dark" notMerge={true} />
          </TacticalPanel>
        </Grid>

        {/* Heatmap Row */}
        <Grid size={{ xs: 12 }}>
          <TacticalPanel title="ENDPOINT_SATURATION_HEATMAP" icon={<Server size={18} color="#facc15" />}>
            <ReactECharts key={`heatmap-${scanId}`} option={heatmapOption} style={{ height: '450px' }} theme="dark" notMerge={true} />
          </TacticalPanel>
        </Grid>
      </Grid>

      {/* Settings Dialog */}
      <Dialog open={openSettings} onClose={() => setOpenSettings(false)} slotProps={{ paper: { sx: { bgcolor: '#1a1a1a', color: '#fff' } } }}>
        <DialogTitle sx={{ fontFamily: 'Orbitron', color: '#00f3ff' }}>TEST_CONFIGURATION</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 2 }}>
            <TextField 
              label="Concurrency (VUs)" 
              type="number" 
              fullWidth 
              value={config.concurrency}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfig({...config, concurrency: parseInt(e.target.value)})}
              slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
              sx={{ input: { color: '#fff' } }}
            />
            <TextField 
              label="Duration (e.g. 30s, 1m)" 
              fullWidth 
              value={config.duration}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfig({...config, duration: e.target.value})}
              slotProps={{ inputLabel: { style: { color: 'rgba(255,255,255,0.5)' } } }}
              sx={{ input: { color: '#fff' } }}
            />
            <FormControl fullWidth>
              <InputLabel sx={{ color: 'rgba(255,255,255,0.5)' }}>Stress Tools</InputLabel>
              <Select
                multiple
                value={config.uses_tools}
                onChange={(e) => setConfig({...config, uses_tools: typeof e.target.value === 'string' ? e.target.value.split(',') : e.target.value})}
                input={<OutlinedInput label="Stress Tools" />}
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
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setOpenSettings(false)} sx={{ color: 'rgba(255,255,255,0.5)' }}>CANCEL</Button>
          <Button onClick={() => setOpenSettings(false)} variant="contained" sx={{ bgcolor: '#00f3ff', color: '#000', fontWeight: 'bold' }}>APPLY</Button>
        </DialogActions>
      </Dialog>

      {/* Report Generation Dialog */}
      <Dialog open={openReportDialog} onClose={() => setOpenReportDialog(false)} slotProps={{ paper: { sx: { bgcolor: '#1a1a1a', color: '#fff', minWidth: '400px' } } }}>
        <DialogTitle sx={{ fontFamily: 'Orbitron', color: '#00f3ff' }}>GENERATE_PERFORMANCE_REPORT</DialogTitle>
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
            {isGeneratingReport ? 'GENERATING...' : 'GENERATE_PDF'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
