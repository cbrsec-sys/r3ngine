import React from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Grid, 
  List, 
  ListItem, 
  ListItemText, 
  Chip,
  Divider,
  IconButton
} from '@mui/material';
import { ShieldAlert, Activity, ExternalLink } from 'lucide-react';
import type { DashboardData } from '../api';

const SeverityChip: React.FC<{ severity: number }> = ({ severity }) => {
  const configs: Record<number, { label: string; color: string; glow: string }> = {
    4: { label: 'CRITICAL', color: '#ff003c', glow: 'rgba(255, 0, 60, 0.5)' },
    3: { label: 'HIGH', color: '#ff9f00', glow: 'rgba(255, 159, 0, 0.5)' },
    2: { label: 'MEDIUM', color: '#fffc00', glow: 'rgba(255, 252, 0, 0.5)' },
    1: { label: 'LOW', color: '#00ff62', glow: 'rgba(0, 255, 98, 0.5)' },
    0: { label: 'INFO', color: '#00f3ff', glow: 'rgba(0, 243, 255, 0.5)' },
    [-1]: { label: 'UNKNOWN', color: '#7000ff', glow: 'rgba(112, 0, 255, 0.5)' }
  };
  const config = configs[severity] || configs[-1];
  return (
    <Chip 
      label={config.label} 
      size="small" 
      sx={{ 
        fontSize: '0.6rem', 
        fontWeight: 800, 
        borderRadius: 1,
        bgcolor: 'transparent',
        border: `1px solid ${config.color}`,
        color: config.color,
        boxShadow: `0 0 8px ${config.glow}`
      }} 
    />
  );
};

const FeedCard: React.FC<{ title: string; icon: React.ReactNode; iconColor: string; children: React.ReactNode }> = ({ title, icon, iconColor, children }) => (
  <Card sx={{ 
    height: 500, 
    bgcolor: 'rgba(5, 5, 15, 0.6)', 
    backdropFilter: 'blur(10px)', 
    border: '1px solid rgba(0, 243, 255, 0.1)',
    position: 'relative',
    '&::after': {
      content: '""',
      position: 'absolute',
      top: 0,
      left: 0,
      width: '100%',
      height: '2px',
      background: `linear-gradient(90deg, ${iconColor}, transparent)`
    }
  }}>
    <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Box sx={{ color: iconColor, mr: 1.5, display: 'flex' }}>{icon}</Box>
        <Typography variant="h6" sx={{ 
          fontSize: '0.85rem', 
          fontWeight: 800, 
          textTransform: 'uppercase', 
          letterSpacing: 1.5,
          fontFamily: 'Orbitron',
          color: '#fff'
        }}>
          {title}
        </Typography>
      </Box>
      <Box sx={{ mt: 1, flexGrow: 1, overflow: 'auto', pr: 1, '&::-webkit-scrollbar': { width: 4 }, '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(0, 243, 255, 0.2)', borderRadius: 2 } }}>
        {children}
      </Box>
    </CardContent>
  </Card>
);

export const ActivityFeed: React.FC<{ data: DashboardData }> = ({ data }) => {
  return (
    <FeedCard 
      title="OPERATIONAL SCAN ACTIVITY" 
      icon={<Activity size={20} />} 
      iconColor="#00f3ff"
    >
      <List sx={{ p: 0 }}>
        {data.activity_feed.length === 0 ? (
          <Typography variant="body2" color="text.secondary">No recent scans.</Typography>
        ) : (
          data.activity_feed.map((scan, i) => (
            <React.Fragment key={scan.id}>
              <ListItem sx={{ px: 1, py: 1.5, borderRadius: 1, '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.03)' } }}>
                <ListItemText 
                  primary={
                    <Typography variant="body2" sx={{ fontWeight: 600, color: '#e6f1ff' }}>
                      {scan.domain.name}
                    </Typography>
                  }
                  secondary={
                    <Typography variant="caption" sx={{ opacity: 0.6, display: 'block' }}>
                      {`${scan.scan_type?.engine_name || 'Standard'} • ${scan.completed_ago || 'Tactical Active'}`}
                    </Typography>
                  }
                />
                <Box sx={{ ml: 2 }}>
                   <Chip 
                    label={String(scan.scan_status).toUpperCase()} 
                    size="small" 
                    variant="outlined"
                    sx={{ 
                      fontSize: '0.6rem', 
                      fontWeight: 800,
                      borderRadius: 1,
                      borderColor: String(scan.scan_status).toLowerCase().includes('success') ? 'success.main' : 'warning.main',
                      color: String(scan.scan_status).toLowerCase().includes('success') ? 'success.main' : 'warning.main',
                      boxShadow: String(scan.scan_status).toLowerCase().includes('success') ? '0 0 5px rgba(0, 255, 136, 0.3)' : 'none'
                    }} 
                  />
                </Box>
              </ListItem>
              {i < data.activity_feed.length - 1 && <Divider sx={{ opacity: 0.05 }} />}
            </React.Fragment>
          ))
        )}
      </List>
    </FeedCard>
  );
};
