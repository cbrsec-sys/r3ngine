import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { ShieldAlert, Home, RefreshCw } from 'lucide-react';
import { Link } from '@tanstack/react-router';

export const NotFound: React.FC = () => {
  return (
    <Box
      sx={{
        height: '80vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {/* Glitch Effect Background */}
      <Box sx={{
        position: 'absolute',
        fontSize: '15rem',
        fontWeight: 900,
        opacity: 0.03,
        color: '#ff003c',
        zIndex: 0,
        userSelect: 'none',
        fontFamily: 'Orbitron'
      }}>
        404
      </Box>

      <Box sx={{ zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Box sx={{
          p: 3,
          borderRadius: '50%',
          bgcolor: 'rgba(255, 0, 60, 0.1)',
          border: '2px solid rgba(255, 0, 60, 0.3)',
          boxShadow: '0 0 30px rgba(255, 0, 60, 0.2)',
          mb: 4,
          // animation: 'pulse 2s infinite ease-in-out',
          // '@keyframes pulse': {
          //   '0%': { transform: 'scale(1)', boxShadow: '0 0 20px rgba(255, 0, 60, 0.2)' },
          //   '50%': { transform: 'scale(1.05)', boxShadow: '0 0 40px rgba(255, 0, 60, 0.4)' },
          //   '100%': { transform: 'scale(1)', boxShadow: '0 0 20px rgba(255, 0, 60, 0.2)' },
          // }
        }}>
          <ShieldAlert size={64} color="#ff003c" />
        </Box>

        <Typography variant="h2" sx={{
          fontFamily: 'Orbitron',
          fontWeight: 900,
          letterSpacing: 4,
          color: '#fff',
          mb: 1,
          textShadow: '0 0 10px rgba(255, 0, 60, 0.8)'
        }}>
          SIGNAL LOST
        </Typography>

        <Typography variant="h6" sx={{
          color: '#ff003c',
          fontWeight: 800,
          fontFamily: 'Orbitron',
          mb: 4,
          opacity: 0.8
        }}>
          UNAUTHORIZED SECTOR ACCESS
        </Typography>

        <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.6)', maxWidth: 450, mb: 6, lineHeight: 1.6 }}>
          The tactical coordinates you provided do not match any known sectors in the reNgine perimeter.
          Return to base or verify the target parameters.
        </Typography>

        <Box sx={{ display: 'flex', gap: 3 }}>
          <Button
            component={Link}
            to="/"
            variant="contained"
            startIcon={<Home size={18} />}
            sx={{
              bgcolor: 'rgba(255, 255, 255, 0.05)',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.1)',
              '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.1)', borderColor: '#fff' },
              fontFamily: 'Orbitron',
              fontWeight: 800,
              px: 4
            }}
          >
            Return to Dashboard
          </Button>
          <Button
            onClick={() => window.location.reload()}
            variant="outlined"
            startIcon={<RefreshCw size={18} />}
            sx={{
              borderColor: '#ff003c',
              color: '#ff003c',
              '&:hover': { borderColor: '#ff003c', bgcolor: 'rgba(255, 0, 60, 0.05)' },
              fontFamily: 'Orbitron',
              fontWeight: 800,
              px: 4
            }}
          >
            Reconnect Signal
          </Button>
        </Box>
      </Box>
    </Box>
  );
};
