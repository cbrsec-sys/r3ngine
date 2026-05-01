import { createTheme, alpha } from '@mui/material/styles';
import { neonTokens } from './tokens';

export const neonHackerTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: neonTokens.neon.cyan,
    },
    secondary: {
      main: neonTokens.neon.pink,
    },
    background: {
      default: neonTokens.bg.primary,
      paper: neonTokens.bg.secondary,
    },
    text: {
      primary: neonTokens.cyber.text,
      secondary: alpha(neonTokens.cyber.text, 0.7),
    },
    divider: neonTokens.cyber.border,
  },
  typography: {
    fontFamily: '"Inter", "Cerebri Sans", sans-serif',
    h1: { fontFamily: '"Orbitron", sans-serif', letterSpacing: '2px' },
    h2: { fontFamily: '"Orbitron", sans-serif', letterSpacing: '2px' },
    h3: { fontFamily: '"Orbitron", sans-serif', letterSpacing: '2px' },
    h4: { fontFamily: '"Orbitron", sans-serif', letterSpacing: '2px' },
    h5: { fontFamily: '"Orbitron", sans-serif', letterSpacing: '1px' },
    h6: { fontFamily: '"Orbitron", sans-serif', letterSpacing: '1px' },
  },
  shape: {
    borderRadius: 18,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          background: `linear-gradient(135deg, rgba(20, 15, 30, 0.7) 0%, rgba(10, 10, 15, 0.9) 100%)`,
          backdropFilter: 'blur(25px) saturate(180%)',
          border: `1px solid ${alpha('#fff', 0.06)}`,
          boxShadow: 'inset 0 0 30px rgba(0, 0, 0, 0.5), 0 15px 35px rgba(0, 0, 0, 0.8)',
          transition: 'all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
          '&:hover': {
            transform: 'translateY(-6px) scale(1.005)',
            boxShadow: neonTokens.cyber.glow.cyan,
            borderColor: alpha(neonTokens.neon.cyan, 0.4),
          },
          '&::before': {
            content: '""',
            position: 'absolute',
            inset: 0,
            borderRadius: 'inherit',
            background: `radial-gradient(circle at 20% 20%, ${alpha(neonTokens.neon.pink, 0.15)}, transparent 50%), radial-gradient(circle at 80% 80%, ${alpha(neonTokens.neon.cyan, 0.1)}, transparent 50%)`,
            opacity: 0.6,
            pointerEvents: 'none',
            zIndex: 0,
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'uppercase',
          letterSpacing: '1px',
          fontWeight: 700,
          borderRadius: '8px',
          transition: '0.3s',
        },
        containedPrimary: {
          boxShadow: `0 0 10px ${alpha(neonTokens.neon.cyan, 0.3)}`,
          '&:hover': {
            boxShadow: `0 0 20px ${alpha(neonTokens.neon.cyan, 0.6)}`,
          },
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: `
        body {
          background-color: ${neonTokens.bg.primary};
          color: ${neonTokens.cyber.text};
          overflow-x: hidden;
        }
        @keyframes scanline-move {
          0% { background-position: 0 0; }
          100% { background-position: 0 100%; }
        }
        body::after {
          content: " ";
          display: block;
          position: fixed;
          top: 0; left: 0; bottom: 0; right: 0;
          background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.2) 50%), url("https://grainy-gradients.vercel.app/noise.svg");
          background-size: 100% 3px, 200px 200px;
          z-index: 9999;
          pointer-events: none;
          opacity: 0.12;
          animation: scanline-move 10s linear infinite;
        }
      `,
    },
  },
});
