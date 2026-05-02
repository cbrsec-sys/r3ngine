import React from 'react';
import { Box, Typography, Card, CardContent } from '@mui/material';

export interface KpiCardProps {
  title: string;
  value: number;
  icon: any;
  color: string;
  subtitle?: string;
  className?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({ title, value, icon: Icon, color, subtitle }) => {
  return (
    <Card 
      sx={{ 
        height: '100%',
        bgcolor: 'rgba(5, 5, 15, 0.4)', 
        backdropFilter: 'blur(12px)', 
        border: '1px solid rgba(255, 255, 255, 0.05)',
        position: 'relative',
        overflow: 'hidden',
        borderRadius: '12px',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        '&:hover': {
          transform: 'translateY(-4px)',
          borderColor: color,
          boxShadow: `0 0 15px ${color}22`,
          '& .kpi-icon-bg': { opacity: 0.15, transform: 'scale(1.1) rotate(-10deg)' }
        }
      }}
    >
      <CardContent sx={{ p: 3 }}>
        {/* Watermark Icon */}
        <Box 
          className="kpi-icon-bg"
          sx={{ 
            position: 'absolute', 
            right: -15, 
            top: -15, 
            opacity: 0.08,
            transition: 'all 0.3s ease',
            color: color
          }}
        >
          <Icon size={100} />
        </Box>
        
        {/* Header Row */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2.5 }}>
          <Box sx={{ 
            p: 1.2, 
            borderRadius: 2, 
            bgcolor: `${color}15`, 
            color: color,
            display: 'flex',
            mr: 1.5,
            border: `1px solid ${color}33`,
            boxShadow: `0 0 15px ${color}22`
          }}>
            <Icon size={22} />
          </Box>
          <Typography variant="overline" sx={{ 
            fontWeight: 800, 
            letterSpacing: 2, 
            color: 'rgba(255,255,255,0.5)',
            fontFamily: 'Orbitron',
            lineHeight: 1
          }}>
            {title}
          </Typography>
        </Box>

        {/* Value Row */}
        <Typography variant="h3" sx={{ 
          fontWeight: 900, 
          mb: 0.5, 
          fontFamily: 'Orbitron',
          letterSpacing: -1,
          color: '#fff'
        }}>
          {value.toLocaleString()}
        </Typography>
        
        {/* Footer Row */}
        {subtitle && (
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Box 
              sx={{ 
                width: 6, 
                height: 6, 
                borderRadius: '50%', 
                bgcolor: color, 
                mr: 1,
                boxShadow: `0 0 8px ${color}`,
                animation: 'kpiPulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
              }} 
            />
            <Typography variant="caption" sx={{ 
              color: 'rgba(255,255,255,0.4)', 
              fontWeight: 800,
              fontSize: '0.65rem',
              letterSpacing: 1
            }}>
              {subtitle.toUpperCase()}
            </Typography>
          </Box>
        )}
      </CardContent>
      <style>{`
        @keyframes kpiPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </Card>
  );
};
