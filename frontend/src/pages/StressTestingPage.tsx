import React, { useState } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import { 
  Box, 
  Grid, 
  Paper, 
  Typography, 
  Button, 
  IconButton, 
  Card,
  CardContent,
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
  Chip
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
import axios from 'axios';

export const StressTestingPage: React.FC = () => {
  const { projectSlug, scanId } = useParams<{ projectSlug: string, scanId: string }>();
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
      title: { text: 'REAL-TIME LATENCY (ms)', textStyle: { color: '#00f3ff', fontFamily: 'Orbitron', fontSize: 14 } },
      tooltip: { 
        trigger: 'axis',
        backgroundColor: 'rgba(0,0,0,0.8)',
        borderColor: '#00f3ff',
        textStyle: { color: '#fff' }
      },
      xAxis: { 
        type: 'time',
        splitLine: { show: false },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
      },
      yAxis: { 
        type: 'value',
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
      },
      series: [{
        name: 'Avg Latency',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: data.map(p => [p.timestamp * 1000, p.avg_latency || p.latency]),
        itemStyle: { color: '#00f3ff' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: 'rgba(0, 243, 255, 0.3)' }, { offset: 1, color: 'rgba(0, 243, 255, 0)' }]
          }
        }
      }]
    };
  };

  const getRpsOption = () => {
    const data = telemetryData.filter(p => p.throughput_rps);
    return {
      backgroundColor: 'transparent',
      title: { text: 'THROUGHPUT (RPS)', textStyle: { color: '#6be6c1', fontFamily: 'Orbitron', fontSize: 14 } },
      tooltip: { 
        trigger: 'axis',
        backgroundColor: 'rgba(0,0,0,0.8)',
        borderColor: '#6be6c1',
        textStyle: { color: '#fff' }
      },
      xAxis: { type: 'time', splitLine: { show: false } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
      series: [{
        name: 'RPS',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: data.map(p => [p.timestamp * 1000, p.throughput_rps]),
        itemStyle: { color: '#6be6c1' }
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
    <Box sx={{ p: 4, minHeight: '100vh', background: '#0a0a0a', color: '#fff' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <IconButton 
            component={RouterLink} 
            to={`/${projectSlug}/scans`} 
            sx={{ color: 'rgba(255,255,255,0.5)', border: '1px solid rgba(255,255,255,0.1)' }}
          >
            <ArrowLeft size={20} />
          </IconButton>
          <Box>
            <Typography variant="h4" sx={{ fontFamily: 'Orbitron', fontWeight: 900, color: '#fff', letterSpacing: 2 }}>
              ADAPTIVE_STRESS_ANALYSIS
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(0,243,255,0.7)', fontFamily: 'Orbitron', fontSize: 10 }}>
              LIVE_TELEMETRY_PIPELINE // SCAN_ID: {scanId}
            </Typography>
          </Box>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button 
            variant="outlined" 
            sx={{ borderColor: 'rgba(255,255,255,0.1)', color: '#fff' }}
            startIcon={<SettingsIcon size={18} />}
            onClick={() => setOpenSettings(true)}
          >
            CONFIGURE
          </Button>
          <Button 
            variant="contained" 
            sx={{ 
              background: 'linear-gradient(45deg, #00f3ff, #0066ff)',
              fontWeight: 'bold',
              '&:disabled': { opacity: 0.5 }
            }}
            startIcon={<Play />}
            onClick={handleStart}
            disabled={isScanning}
          >
            EXECUTE_TEST
          </Button>
          <Button 
            variant="contained" 
            sx={{ background: '#ff003c', fontWeight: 'bold' }}
            startIcon={isStopping ? <CircularProgress size={18} color="inherit" /> : <Square />}
            onClick={handleStop}
            disabled={!isScanning || isStopping}
          >
            KILL_SWITCH
          </Button>
        </Box>
      </Box>

      {/* Main Grid */}
      <Grid container spacing={3}>
        {/* KPI Row */}
        <Grid size={{ xs: 12 }}>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card sx={{ bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 2 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Activity size={16} color="#00f3ff" />
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontFamily: 'Orbitron' }}>LATENCY_AVG</Typography>
                  </Box>
                  <Typography variant="h4" sx={{ fontFamily: 'Orbitron', fontWeight: 700 }}>
                    {telemetryData.length > 0 ? (telemetryData[telemetryData.length-1].avg_latency || 0).toFixed(2) : '0.00'}
                    <span style={{ fontSize: '14px', marginLeft: 8, opacity: 0.5 }}>ms</span>
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card sx={{ bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 2 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Zap size={16} color="#6be6c1" />
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontFamily: 'Orbitron' }}>THROUGHPUT</Typography>
                  </Box>
                  <Typography variant="h4" sx={{ fontFamily: 'Orbitron', fontWeight: 700 }}>
                    {telemetryData.length > 0 ? (telemetryData[telemetryData.length-1].throughput_rps || 0).toFixed(0) : '0'}
                    <span style={{ fontSize: '14px', marginLeft: 8, opacity: 0.5 }}>RPS</span>
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card sx={{ bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 2 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <AlertTriangle size={16} color="#ff003c" />
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontFamily: 'Orbitron' }}>ERROR_RATE</Typography>
                  </Box>
                  <Typography variant="h4" sx={{ fontFamily: 'Orbitron', fontWeight: 700 }}>
                    {telemetryData.length > 0 ? ((telemetryData[telemetryData.length-1].error_rate || 0) * 100).toFixed(1) : '0.0'}
                    <span style={{ fontSize: '14px', marginLeft: 8, opacity: 0.5 }}>%</span>
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card sx={{ bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 2 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Server size={16} color="#facc15" />
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontFamily: 'Orbitron' }}>CONCURRENCY</Typography>
                  </Box>
                  <Typography variant="h4" sx={{ fontFamily: 'Orbitron', fontWeight: 700 }}>
                    {config.concurrency}
                    <span style={{ fontSize: '14px', marginLeft: 8, opacity: 0.5 }}>VUs</span>
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>

        {/* Charts Row */}
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper sx={{ p: 3, bgcolor: '#141414', border: '1px solid rgba(255,255,255,0.05)', height: '400px' }}>
            <ReactECharts option={getLatencyOption()} style={{ height: '350px' }} theme="dark" />
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <Paper sx={{ p: 3, bgcolor: '#141414', border: '1px solid rgba(255,255,255,0.05)', height: '400px' }}>
            <ReactECharts option={getRpsOption()} style={{ height: '350px' }} theme="dark" />
          </Paper>
        </Grid>

        {/* Heatmap & Logs Row */}
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper sx={{ p: 3, bgcolor: '#141414', border: '1px solid rgba(255,255,255,0.05)', height: '500px' }}>
            <Typography variant="subtitle2" sx={{ fontFamily: 'Orbitron', color: 'rgba(255,255,255,0.5)', mb: 2 }}>
              ENDPOINT_SATURATION_HEATMAP
            </Typography>
            <ReactECharts option={getHeatmapOption()} style={{ height: '400px' }} theme="dark" />
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <Paper sx={{ p: 3, bgcolor: '#141414', border: '1px solid rgba(255,255,255,0.05)', height: '500px', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Terminal size={16} color="#00f3ff" />
              <Typography variant="subtitle2" sx={{ fontFamily: 'Orbitron', color: 'rgba(255,255,255,0.5)' }}>
                TELEMETRY_LOG
              </Typography>
            </Box>
            <Box sx={{ flexGrow: 1, overflowY: 'auto', bgcolor: '#000', p: 2, borderRadius: 1, border: '1px solid rgba(255,255,255,0.1)' }}>
              <List dense>
                {telemetryData.slice(-100).reverse().map((p, i) => (
                  <ListItem key={i} sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <ListItemIcon sx={{ minWidth: 30 }}>
                      <Clock size={12} color="rgba(255,255,255,0.3)" />
                    </ListItemIcon>
                    <ListItemText 
                      primary={`${p.tool.toUpperCase()} -> ${p.endpoint.split('/').pop()}`}
                      secondary={`Latency: ${p.avg_latency || p.latency}ms | Status: OK`}
                      slotProps={{
                        primary: { sx: { fontSize: 10, color: '#fff', fontFamily: 'monospace' } },
                        secondary: { sx: { fontSize: 9, color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace' } }
                      }}
                    />
                  </ListItem>
                ))}
                {telemetryData.length === 0 && (
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.2)', textAlign: 'center', display: 'block', mt: 4 }}>
                    WAITING_FOR_DATA...
                  </Typography>
                )}
              </List>
            </Box>
          </Paper>
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
