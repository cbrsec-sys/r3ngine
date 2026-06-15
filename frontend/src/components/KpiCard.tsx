import { useThemeTokens } from '../theme/useThemeTokens';
import React from 'react';
import { Box, Typography, Card, CardContent, useTheme } from '@mui/material';
import type { SxProps, Theme } from '@mui/material';

export interface KpiCardProps {
  title: string;
  value: number | string;
  icon: any;
  color: string;
  subtitle?: string;
  className?: string;
  sx?: SxProps<Theme>;
}

export const KpiCard: React.FC<KpiCardProps> = ({ title, value, icon: Icon, color, subtitle, sx }) => {
  const { tokens } = useThemeTokens();
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';

  return (
    <Card
      sx={{
        height: '100%',
        bgcolor: isLight ? theme.palette.background.paper : 'rgba(5, 5, 15, 0.4)',
        backdropFilter: 'blur(12px)',
        border: isLight ? `1px solid ${theme.palette.divider}` : '1px solid rgba(255, 255, 255, 0.05)',
        position: 'relative',
        overflow: 'hidden',
        borderRadius: isLight ? '8px' : '12px',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        '&:hover': {
          transform: 'translateY(-4px)',
          borderColor: color,
          boxShadow: isLight ? `0 4px 20px ${color}15` : `0 0 15px ${color}22`,
          '& .kpi-icon-bg': { opacity: 0.15, transform: 'scale(1.1) rotate(-10deg)' }
        },
        ...sx
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
            opacity: isLight ? 0.05 : 0.08,
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
            boxShadow: isLight ? 'none' : `0 0 15px ${color}22`
          }}>
            <Icon size={22} />
          </Box>
          <Typography variant="overline" sx={{
            fontWeight: 800,
            letterSpacing: 2,
            color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.5)',
            fontFamily: 'var(--r3-heading-font)',
            lineHeight: 1
          }}>
            {title}
          </Typography>
        </Box>

        {/* Value Row */}
        <Typography variant="h3" sx={{
          fontWeight: 900,
          mb: 0.5,
          fontFamily: 'var(--r3-heading-font)',
          letterSpacing: -1,
          color: isLight ? theme.palette.text.primary : '#fff'
        }}>
          {typeof value === 'number' ? value.toLocaleString() : value}
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
                boxShadow: isLight ? 'none' : `0 0 8px ${color}`
              }}
            />
            <Typography variant="caption" sx={{
              color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.4)',
              fontWeight: 800,
              fontSize: '0.65rem',
              letterSpacing: 1
            }}>
              {subtitle.toUpperCase()}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};
