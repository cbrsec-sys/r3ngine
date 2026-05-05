import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { Activity, ShieldAlert } from 'lucide-react';

export const PlaceholderPage: React.FC<{ title: string; icon: React.ReactNode }> = ({ title, icon }) => {
  return (
    <Box
      sx={{
        height: '60vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
        background: 'rgba(255, 255, 255, 0.02)',
        borderRadius: 4,
        border: '1px dashed rgba(255, 255, 255, 0.1)',
        p: 4
      }}
    >
      <Box sx={{ color: '#00f3ff', mb: 3 }}>
        {icon}
      </Box>
      <Typography variant="h4" sx={{ fontFamily: 'Orbitron', fontWeight: 900, mb: 2, color: '#fff' }}>
        {title.toUpperCase()}
      </Typography>
      <Typography variant="body1" sx={{ color: 'rgba(255, 255, 255, 0.5)', maxWidth: 500, mb: 4 }}>
        The {title} tactical module is currently being migrated to the new React interface. 
        Please check back shortly for full reconnaissance data.
      </Typography>
      <Button variant="outlined" sx={{ borderColor: '#00f3ff', color: '#00f3ff' }}>
        NOTIFY ON COMPLETION
      </Button>
    </Box>
  );
};
