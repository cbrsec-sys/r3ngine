import React from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  List, 
  Chip
} from '@mui/material';
import { Activity } from 'lucide-react';
import type { DashboardData } from '../api';
import { useThemeTokens } from '../../../theme/useThemeTokens';

const SeverityChip: React.FC<{ severity: number }> = ({ severity }) => {
  const { isLight } = useThemeTokens();
  const configs: Record<number, { label: string; color: string; glow: string }> = {
    4: { label: 'CRITICAL', color: '#ff003c', glow: 'rgba(255, 0, 60, 0.5)' },
    3: { label: 'HIGH', color: '#ff9f00', glow: 'rgba(255, 159, 0, 0.5)' },
    2: { label: 'MEDIUM', color: isLight ? '#b8b500' : '#fffc00', glow: 'rgba(255, 252, 0, 0.5)' },
    1: { label: 'LOW', color: isLight ? '#00ad42' : '#00ff62', glow: 'rgba(0, 255, 98, 0.5)' },
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
        boxShadow: isLight ? 'none' : `0 0 8px ${config.glow}`
      }} 
    />
  );
};

const FeedCard: React.FC<{ title: string; icon: React.ReactNode; iconColor: string; children: React.ReactNode }> = ({ title, icon, iconColor, children }) => {
  const { tokens, isLight } = useThemeTokens();
  return (
    <Card sx={{ 
      height: 500, 
      bgcolor: isLight ? 'background.paper' : 'rgba(5, 5, 15, 0.6)', 
      backdropFilter: 'blur(10px)', 
      border: isLight ? '1px solid rgba(0, 0, 0, 0.08)' : '1px solid rgba(0, 243, 255, 0.1)',
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
            color: isLight ? 'text.primary' : '#fff'
          }}>
            {title}
          </Typography>
        </Box>
        <Box sx={{ mt: 1, flexGrow: 1, overflow: 'auto', pr: 1, '&::-webkit-scrollbar': { width: 4 }, '&::-webkit-scrollbar-thumb': { bgcolor: isLight ? 'rgba(0,0,0,0.1)' : 'rgba(0, 243, 255, 0.2)', borderRadius: 2 } }}>
          {children}
        </Box>
      </CardContent>
    </Card>
  );
};

export const ActivityFeed: React.FC<{ data: DashboardData }> = ({ data }) => {
  const { tokens, isLight } = useThemeTokens();
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
            <Box 
              key={scan.id} 
              sx={{ 
                mb: 1, 
                p: 1.2, 
                borderRadius: 2, 
                bgcolor: isLight ? 'action.hover' : 'rgba(255,255,255,0.02)', 
                border: isLight ? '1px solid rgba(0, 0, 0, 0.05)' : '1px solid rgba(0, 243, 255, 0.1)',
                position: 'relative',
                overflow: 'hidden',
                transition: 'all 0.2s',
                '&:hover': {
                  bgcolor: isLight ? 'action.selected' : 'rgba(0, 243, 255, 0.05)',
                  borderColor: isLight ? 'rgba(0, 0, 0, 0.15)' : 'rgba(0, 243, 255, 0.4)',
                  boxShadow: isLight ? 'none' : '0 0 10px rgba(0, 243, 255, 0.1)'
                }
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Box 
                  sx={{ 
                    width: 6, 
                    height: 6, 
                    borderRadius: '50%', 
                    bgcolor: scan.status === 2 ? '#00ff62' : '#ff9f00', 
                    mr: 1.2, 
                    boxShadow: isLight ? 'none' : (scan.status === 2 ? '0 0 8px #00ff62' : '0 0 8px #ff9f00')
                  }} 
                />
                <Typography variant="body2" sx={{ fontWeight: 800, color: isLight ? 'text.primary' : '#fff', fontSize: '0.8rem', flex: 1 }}>
                  {scan.title}
                </Typography>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box sx={{ 
                  display: 'inline-flex', 
                  alignItems: 'center',
                  px: 1, 
                  py: 0.2, 
                  borderRadius: 0.5, 
                  bgcolor: isLight ? `${tokens.accent.primary}1A` : 'rgba(0, 243, 255, 0.05)', 
                  border: `1px solid ${isLight ? tokens.accent.primary + '33' : 'rgba(0, 243, 255, 0.2)'}`,
                }}>
                  <Typography variant="body2" sx={{ color: isLight ? 'primary.main' : '#00f3ff', fontWeight: 700, fontSize: '0.65rem' }}>
                    {scan.domain}
                  </Typography>
                </Box>

                <Typography variant="caption" sx={{ color: isLight ? 'text.secondary' : 'rgba(255,255,255,0.3)', fontSize: '0.65rem' }}>
                  {scan.completed_ago}
                </Typography>
              </Box>
            </Box>
          ))
        )}
      </List>
    </FeedCard>
  );
};
