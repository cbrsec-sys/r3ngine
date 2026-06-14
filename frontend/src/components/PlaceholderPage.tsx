import React from 'react';
import { Box, Typography, Button, useTheme, alpha } from '@mui/material';

export const PlaceholderPage: React.FC<{ title: string; icon: React.ReactNode }> = ({ title, icon }) => {
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';

  return (
    <Box
      sx={{
        height: '60vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
        background: isLight
          ? alpha(theme.palette.primary.main, 0.03)
          : 'rgba(255, 255, 255, 0.02)',
        borderRadius: 4,
        border: isLight
          ? `1px dashed ${theme.palette.divider}`
          : '1px dashed rgba(255, 255, 255, 0.1)',
        p: 4
      }}
    >
      <Box sx={{ color: theme.palette.primary.main, mb: 3 }}>
        {icon}
      </Box>
      <Typography variant="h4" sx={{
        fontFamily: 'var(--r3-heading-font)',
        fontWeight: 900,
        mb: 2,
        color: isLight ? theme.palette.text.primary : '#fff'
      }}>
        {title.toUpperCase()}
      </Typography>
      <Typography variant="body1" sx={{
        color: theme.palette.text.secondary,
        maxWidth: 500,
        mb: 4
      }}>
        The {title} tactical module is currently being migrated to the new React interface.
        Please check back shortly for full reconnaissance data.
      </Typography>
      <Button
        variant="outlined"
        sx={{
          borderColor: theme.palette.primary.main,
          color: theme.palette.primary.main,
          '&:hover': {
            bgcolor: alpha(theme.palette.primary.main, 0.08),
          }
        }}
      >
        NOTIFY ON COMPLETION
      </Button>
    </Box>
  );
};
