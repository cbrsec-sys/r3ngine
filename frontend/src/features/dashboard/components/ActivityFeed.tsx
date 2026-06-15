import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  List,
  useTheme,
  alpha
} from '@mui/material';
import { Activity } from 'lucide-react';
import type { DashboardData } from '../api';

const FeedCard: React.FC<{ title: string; icon: React.ReactNode; iconColor: string; children: React.ReactNode }> = ({ title, icon, iconColor, children }) => {
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';

  return (
    <Card sx={{
      height: 500,
      bgcolor: isLight ? theme.palette.background.paper : 'rgba(5, 5, 15, 0.6)',
      backdropFilter: isLight ? 'none' : 'blur(10px)',
      border: isLight ? `1px solid ${theme.palette.divider}` : '1px solid rgba(0, 243, 255, 0.1)',
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
            fontFamily: 'var(--r3-heading-font)',
            color: isLight ? theme.palette.text.primary : '#fff'
          }}>
            {title}
          </Typography>
        </Box>
        <Box sx={{
          mt: 1,
          flexGrow: 1,
          overflow: 'auto',
          pr: 1,
          '&::-webkit-scrollbar': { width: 4 },
          '&::-webkit-scrollbar-thumb': {
            bgcolor: isLight ? theme.palette.divider : 'rgba(0, 243, 255, 0.2)',
            borderRadius: 2
          }
        }}>
          {children}
        </Box>
      </CardContent>
    </Card>
  );
};

export const ActivityFeed: React.FC<{ data: DashboardData }> = ({ data }) => {
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';
  const primaryColor = theme.palette.primary.main;

  return (
    <FeedCard
      title="OPERATIONAL SCAN ACTIVITY"
      icon={<Activity size={20} />}
      iconColor={primaryColor}
    >
      <List sx={{ p: 0 }}>
        {data.activity_feed.length === 0 ? (
          <Typography variant="body2" color="text.secondary">No recent scans.</Typography>
        ) : (
          data.activity_feed.map((scan) => (
            <Box
              key={scan.id}
              sx={{
                mb: 1,
                p: 1.2,
                borderRadius: 2,
                bgcolor: isLight ? alpha(theme.palette.primary.main, 0.03) : 'rgba(255,255,255,0.02)',
                border: isLight
                  ? `1px solid ${theme.palette.divider}`
                  : '1px solid rgba(0, 243, 255, 0.1)',
                position: 'relative',
                overflow: 'hidden',
                transition: 'all 0.2s',
                '&:hover': {
                  bgcolor: isLight
                    ? alpha(theme.palette.primary.main, 0.07)
                    : 'rgba(0, 243, 255, 0.05)',
                  borderColor: isLight
                    ? theme.palette.primary.main
                    : 'rgba(0, 243, 255, 0.4)',
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
                    bgcolor: scan.status === 2 ? '#16a34a' : '#d97706',
                    mr: 1.2,
                    boxShadow: isLight
                      ? 'none'
                      : scan.status === 2 ? '0 0 8px #00ff62' : '0 0 8px #ff9f00'
                  }}
                />
                <Typography variant="body2" sx={{
                  fontWeight: 800,
                  color: isLight ? theme.palette.text.primary : '#fff',
                  fontSize: '0.8rem',
                  flex: 1
                }}>
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
                  bgcolor: isLight
                    ? alpha(theme.palette.primary.main, 0.08)
                    : 'rgba(0, 243, 255, 0.05)',
                  border: isLight
                    ? `1px solid ${alpha(theme.palette.primary.main, 0.3)}`
                    : '1px solid rgba(0, 243, 255, 0.2)',
                }}>
                  <Typography variant="body2" sx={{
                    color: theme.palette.primary.main,
                    fontWeight: 700,
                    fontSize: '0.65rem'
                  }}>
                    {scan.domain}
                  </Typography>
                </Box>

                <Typography variant="caption" sx={{
                  color: theme.palette.text.secondary,
                  fontSize: '0.65rem'
                }}>
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
