import React from 'react';
import { Box, Card, CardContent, Typography, useTheme } from '@mui/material';
import clsx from 'clsx';
import { useThemeTokens } from '../theme/useThemeTokens';

interface TacticalPanelProps {
  title?: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  borderColor?: string;
  sx?: any;
  headerAction?: React.ReactNode;
}

export const TacticalPanel: React.FC<TacticalPanelProps> = ({ 
  title, 
  icon, 
  children, 
  className,
  borderColor = '#00f0ff',
  sx = {},
  headerAction
}) => {
  const { theme, isLight, tokens } = useThemeTokens();

  return (
    <Card 
      className={clsx("relative overflow-hidden group transition-all duration-500", className)}
      sx={{ 
        background: isLight 
          ? tokens.bg.secondary
          : 'linear-gradient(135deg, rgba(20, 15, 30, 0.7) 0%, rgba(10, 10, 15, 0.9) 100%)',
        backdropFilter: 'blur(25px) saturate(180%)',
        border: isLight 
          ? `1px solid rgba(0,0,0,0.1)` 
          : '1px solid rgba(255, 255, 255, 0.06)',
        borderRadius: isLight ? '8px' : '18px',
        position: 'relative',
        boxShadow: isLight 
          ? '0 1px 3px rgba(0, 0, 0, 0.05)' 
          : 'inset 0 0 30px rgba(0, 0, 0, 0.5), 0 15px 35px rgba(0, 0, 0, 0.8)',
        /* Minimal hover effect to prevent huge tables from getting too hectic */
        '&:hover': {
          borderColor: isLight ? theme.palette.primary.main : 'rgba(0, 240, 255, 0.2)',
        },
        ...sx,
        /* Dual Gradient Glow - Disabled in light mode */
        '&::before': {
          content: '""',
          position: 'absolute',
          inset: 0,
          borderRadius: 'inherit',
          background: 'radial-gradient(circle at 20% 20%, rgba(255, 43, 214, 0.15), transparent 50%), radial-gradient(circle at 80% 80%, rgba(0, 240, 255, 0.1), transparent 50%)',
          opacity: isLight ? 0 : 0.6,
          pointerEvents: 'none',
          zIndex: 0
        }
      }}
    >
      <CardContent sx={{ position: 'relative', zIndex: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2.5, justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              {icon && (
                <Box sx={{ 
                  mr: 1.5, 
                  display: 'flex', 
                  filter: isLight ? 'none' : 'drop-shadow(0 0 5px rgba(0, 240, 255, 0.5))' 
                }}>
                  {icon}
                </Box>
              )}
              <Typography variant="h6" sx={{ 
                fontSize: '0.75rem', 
                fontWeight: 800, 
                textTransform: 'uppercase', 
                letterSpacing: 2.5,
                fontFamily: 'var(--r3-heading-font)',
                color: isLight ? theme.palette.text.primary : '#8ba4c0',
                textShadow: isLight ? 'none' : '0 0 10px rgba(255, 43, 214, 0.4)'
              }}>
                {title}
              </Typography>
            </Box>
            {headerAction && <Box>{headerAction}</Box>}
          </Box>
        {children}
      </CardContent>
    </Card>
  );
};

