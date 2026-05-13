import React, { useState } from 'react';
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
  alpha
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
  Clock
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

  const getLatencyOption = () => {
    const data = telemetryData.filter(p => p.avg_latency || p.latency);
    return {
      backgroundColor: 'transparent',
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
        data: data.map(p => [p.timestamp * 1000, p.avg_latency || p.latency]),
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
  };

  const getRpsOption = () => {
    const data = telemetryData.filter(p => p.throughput_rps);
    return {
      backgroundColor: 'transparent',
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
        data: data.map(p => [p.timestamp * 1000, p.throughput_rps]),
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
  };

  const getHeatmapOption = () => {
    const endpoints = Array.from(new Set(telemetryData.map(p => p.endpoint)));
    const timestamps = Array.from(new Set(telemetryData.map(p => Math.floor(p.timestamp / 5) * 5))); // 5s buckets
    
    const heatmapData = telemetryData.map(p => [
      timestamps.indexOf(Math.floor(p.timestamp / 5) * 5),
      endpoints.indexOf(p.endpoint),
      p.avg_latency || p.latency || 0
    ]);

    return {
      backgroundColor: 'transparent',
      tooltip: { position: 'top' },
      grid: { height: '80%', top: '10%', right: '10%' },
      xAxis: { 
        type: 'category', 
        data: timestamps.map(t => new Date(t * 1000).toLocaleTimeString()),
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
  };

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
        
        <Box sx={{ display: 'flex', gap: 2 }}>
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
            <ReactECharts option={getLatencyOption()} style={{ height: '400px' }} theme="dark" />
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
            <ReactECharts option={getRpsOption()} style={{ height: '400px' }} theme="dark" />
          </TacticalPanel>
        </Grid>

        {/* Heatmap Row */}
        <Grid size={{ xs: 12 }}>
          <TacticalPanel title="ENDPOINT_SATURATION_HEATMAP" icon={<Server size={18} color="#facc15" />}>
            <ReactECharts option={getHeatmapOption()} style={{ height: '450px' }} theme="dark" />
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
    </Box>
  );
};
