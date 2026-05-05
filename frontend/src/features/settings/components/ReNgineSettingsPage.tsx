import React, { useState } from 'react';
import {
  Box,
  Typography,
  Stack,
  Button,
  Paper,
  Divider,
  Alert,
  CircularProgress,
  Grid,
  Snackbar
} from '@mui/material';
import { 
  Trash2, 
  Database, 
  Image as ImageIcon, 
  AlertTriangle,
  HardDrive
} from 'lucide-react';
import Chart from 'react-apexcharts';
import { 
  useRengineSystemSettings, 
  useDeleteAllScanResults, 
  useDeleteAllScreenshots 
} from '../api';
import { TacticalPanel } from '../../../components/TacticalPanel';

export const ReNgineSettingsPage: React.FC = () => {
  const { data: systemInfo, isLoading } = useRengineSystemSettings();
  const deleteScanResults = useDeleteAllScanResults();
  const deleteScreenshots = useDeleteAllScreenshots();
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const handleDeleteScanResults = async () => {
    if (window.confirm('CRITICAL: This will permanently delete all scan history and results. This action cannot be undone. Proceed?')) {
      try {
        await deleteScanResults.mutateAsync();
        setSnackbar({
          open: true,
          message: 'All scan results have been deleted.',
          severity: 'success',
        });
      } catch (err) {
        setSnackbar({
          open: true,
          message: 'Failed to initiate deletion of scan results.',
          severity: 'error',
        });
      }
    }
  };

  const handleDeleteScreenshots = async () => {
    if (window.confirm('WARNING: This will permanently delete all screenshots. Proceed?')) {
      try {
        await deleteScreenshots.mutateAsync();
        setSnackbar({
          open: true,
          message: 'All screenshots have been deleted.',
          severity: 'success',
        });
      } catch (err) {
        setSnackbar({
          open: true,
          message: 'Failed to initiate deletion of screenshots.',
          severity: 'error',
        });
      }
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 10 }}>
        <CircularProgress sx={{ color: '#00f3ff' }} />
      </Box>
    );
  }

  const percent = systemInfo?.consumed_percent || 0;
  const isDanger = percent >= 90;
  const isWarning = percent >= 70;

  const gaugeColor = isDanger ? '#ff1100' : (isWarning ? '#ffcc00' : '#00f3ff');
  const gradientColor = isDanger ? '#cc0000' : (isWarning ? '#997700' : '#0084ff');

  const chartOptions: any = {
    chart: {
      type: "radialBar",
      offsetY: -30,
      sparkline: {
        enabled: true
      }
    },
    plotOptions: {
      radialBar: {
        startAngle: -90,
        endAngle: 90,
        track: {
          background: "rgba(255, 255, 255, 0.05)",
          strokeWidth: '97%',
          margin: 5,
          dropShadow: {
            enabled: true,
            top: 2,
            left: 0,
            color: '#000',
            opacity: 0.3,
            blur: 4
          }
        },
        dataLabels: {
          name: {
            show: false
          },
          value: {
            offsetY: -2,
            fontSize: '22px',
            color: '#fff',
            fontWeight: 900,
            fontFamily: 'Orbitron'
          }
        }
      }
    },
    fill: {
      type: 'gradient',
      gradient: {
        shade: 'dark',
        type: 'horizontal',
        shadeIntensity: 0.5,
        gradientToColors: [gradientColor],
        inverseColors: true,
        opacityFrom: 1,
        opacityTo: 1,
        stops: [0, 100]
      }
    },
    stroke: {
      lineCap: 'round'
    },
    labels: ['Storage Used'],
    colors: [gaugeColor],
  };

  const series = [percent];

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="h4" sx={{ color: '#fff', fontFamily: 'Orbitron', fontWeight: 900, mb: 1 }}>
            RENGINE_SYSTEM_CONFIG
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)' }}>
            Monitor system resources and perform global maintenance actions.
          </Typography>
        </Box>

        <TacticalPanel title="STORAGE_METRICS">
          <Box sx={{ 
            display: 'flex', 
            flexDirection: { xs: 'column', md: 'row' }, 
            alignItems: 'center', 
            justifyContent: 'center',
            gap: { xs: 4, md: 8 }
          }}>
            <Box sx={{ width: 300, display: 'flex', justifyContent: 'center', alignItems: 'center', position: 'relative' }}>
              <Chart 
                options={chartOptions} 
                series={series} 
                type="radialBar" 
                height={320}
              />
              <Box sx={{ position: 'absolute', bottom: 10, textAlign: 'center' }}>
                <Typography sx={{ 
                  fontFamily: 'Orbitron', 
                  fontSize: '0.6rem', 
                  fontWeight: 900, 
                  color: gaugeColor,
                  letterSpacing: 2,
                  textTransform: 'uppercase'
                }}>
                  {isDanger ? 'CRITICAL_LEVEL' : (isWarning ? 'WARNING_LEVEL' : 'STABLE_LEVEL')}
                </Typography>
              </Box>
            </Box>
            
            <Box sx={{ flex: '0 1 auto' }}>
              <Grid container spacing={3}>
                <Grid size={{xs: 12, sm: 4}} >
                  <MetricCard 
                    label="TOTAL_STORAGE" 
                    value={`${systemInfo?.total || 0} GB`} 
                    icon={<Database size={20} color="#ffd600" />} 
                  />
                </Grid>
                <Grid size={{xs: 12, sm: 4}} >
                  <MetricCard 
                    label="USED_SPACE" 
                    value={`${systemInfo?.used || 0} GB`} 
                    icon={<HardDrive size={20} color={gaugeColor} />} 
                    statusColor={gaugeColor}
                  />
                </Grid>
                <Grid size={{xs: 12, sm: 4}} >
                  <MetricCard 
                    label="FREE_SPACE" 
                    value={`${systemInfo?.free || 0} GB`} 
                    icon={<Database size={20} color="#00ff9d" />} 
                    statusColor="#00ff9d"
                  />
                </Grid>
              </Grid>
            </Box>
          </Box>
        </TacticalPanel>

        <TacticalPanel title="DANGER_ZONE" borderColor="rgba(255, 0, 85, 0.3)">
          <Stack spacing={0} divider={<Divider sx={{ borderColor: 'rgba(255,0,85,0.1)' }} />}>
            <MaintenanceRow 
              title="Delete all scan results"
              description="Permanently remove all scan history, findings, and logs across all projects. This action is irreversible."
              onAction={handleDeleteScanResults}
              isLoading={deleteScanResults.isPending}
              buttonLabel="PURGE_ALL_SCANS"
            />
            <MaintenanceRow 
              title="Delete all screenshots"
              description="Remove all captured website screenshots to free up disk space. Scan reports will no longer show visual evidence."
              onAction={handleDeleteScreenshots}
              isLoading={deleteScreenshots.isPending}
              buttonLabel="PURGE_SCREENSHOTS"
            />
          </Stack>
        </TacticalPanel>

        <Alert 
          severity="info" 
          icon={<AlertTriangle size={20} />}
          sx={{ 
            bgcolor: 'rgba(0, 243, 255, 0.05)', 
            color: '#00f3ff',
            border: '1px solid rgba(0, 243, 255, 0.2)',
            '& .MuiAlert-icon': { color: '#00f3ff' }
          }}
        >
          System maintenance actions affect all projects globally. Ensure you have backups before performing purge operations.
        </Alert>
      </Stack>

      <Snackbar 
        open={snackbar.open} 
        autoHideDuration={6000} 
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={handleCloseSnackbar} 
          severity={snackbar.severity} 
          variant="filled"
          sx={{ 
            fontFamily: 'Orbitron', 
            fontSize: '0.8rem',
            fontWeight: 700,
            bgcolor: snackbar.severity === 'success' ? 'rgba(0, 243, 255, 0.9)' : 'rgba(255, 0, 85, 0.9)',
            color: '#000',
            '& .MuiAlert-icon': { color: '#000' }
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

const MetricCard: React.FC<{ label: string; value: string; icon: React.ReactNode; statusColor?: string }> = ({ label, value, icon, statusColor }) => (
  <Paper sx={{ 
    p: 2, 
    bgcolor: 'rgba(255,255,255,0.02)', 
    border: '1px solid',
    borderColor: statusColor ? `${statusColor}33` : 'rgba(255,255,255,0.05)',
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
    transition: 'all 0.3s ease',
    '&:hover': {
      bgcolor: 'rgba(255,255,255,0.04)',
      borderColor: statusColor ? statusColor : 'rgba(255,255,255,0.1)',
    }
  }}>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      {icon}
      <Typography sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem', fontWeight: 900, fontFamily: 'Orbitron' }}>
        {label}
      </Typography>
    </Box>
    <Typography sx={{ color: '#fff', fontSize: '1.2rem', fontWeight: 900, fontFamily: 'Orbitron' }}>
      {value}
    </Typography>
  </Paper>
);

const MaintenanceRow: React.FC<{ 
  title: string; 
  description: string; 
  onAction: () => void; 
  isLoading: boolean;
  buttonLabel: string;
}> = ({ title, description, onAction, isLoading, buttonLabel }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 3, px: 2 }}>
    <Box sx={{ flex: 1, pr: 4 }}>
      <Typography sx={{ color: '#ff0055', fontWeight: 900, mb: 0.5, textTransform: 'uppercase' }}>
        {title}
      </Typography>
      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)' }}>
        {description}
      </Typography>
    </Box>
    <Button
      variant="outlined"
      color="error"
      onClick={onAction}
      disabled={isLoading}
      startIcon={<Trash2 size={18} />}
      sx={{ 
        borderColor: '#ff0055', 
        color: '#ff0055',
        fontFamily: 'Orbitron',
        fontWeight: 900,
        px: 3,
        '&:hover': {
          bgcolor: 'rgba(255, 0, 85, 0.1)',
          borderColor: '#ff0055'
        }
      }}
    >
      {isLoading ? 'PROCESSING...' : buttonLabel}
    </Button>
  </Box>
);
