import React from 'react';
import { Box, Typography, useTheme } from '@mui/material';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle }) => {
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';

  return (
    <Box sx={{ mb: 4 }}>
      <Typography
        variant="h4"
        sx={{
          fontFamily: 'var(--r3-heading-font)',
          fontWeight: 900,
          letterSpacing: isLight ? 1 : 2,
          color: isLight ? theme.palette.text.primary : '#fff',
          textShadow: isLight ? 'none' : '0 0 20px rgba(0, 243, 255, 0.5)',
          mb: subtitle ? 1 : 0,
          textTransform: 'uppercase',
        }}
      >
        {title}
      </Typography>
      {subtitle && (
        <Typography
          variant="body2"
          sx={{
            color: isLight ? theme.palette.text.secondary : 'rgba(255,255,255,0.5)',
            letterSpacing: 1,
          }}
        >
          {subtitle}
        </Typography>
      )}
    </Box>
  );
};
