import { createTheme, alpha, type Theme } from '@mui/material/styles';
import { themeTokens } from './tokens';

const baseTypography = {
  fontFamily: '"Inter", "Cerebri Sans", sans-serif',
  h1: { fontFamily: '"Orbitron", sans-serif', letterSpacing: '2px' },
  h2: { fontFamily: '"Orbitron", sans-serif', letterSpacing: '2px' },
  h3: { fontFamily: '"Orbitron", sans-serif', letterSpacing: '2px' },
  h4: { fontFamily: '"Orbitron", sans-serif', letterSpacing: '2px' },
  h5: { fontFamily: '"Orbitron", sans-serif', letterSpacing: '1px' },
  h6: { fontFamily: '"Orbitron", sans-serif', letterSpacing: '1px' },
};

// Hacker Theme (Cyberpunk)
export const hackerTheme: Theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: themeTokens.hacker.neon.cyan },
    secondary: { main: themeTokens.hacker.neon.pink },
    background: {
      default: themeTokens.hacker.bg.primary,
      paper: themeTokens.hacker.bg.secondary,
    },
    text: {
      primary: themeTokens.hacker.cyber.text,
      secondary: alpha(themeTokens.hacker.cyber.text, 0.7),
    },
    divider: themeTokens.hacker.cyber.border,
  },
  typography: baseTypography,
  shape: { borderRadius: 18 },
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
            boxShadow: themeTokens.hacker.cyber.glow.cyan,
            borderColor: alpha(themeTokens.hacker.neon.cyan, 0.4),
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
        },
        contained: {
          boxShadow: `0 0 10px ${alpha(themeTokens.hacker.neon.cyan, 0.3)}`,
          '&:hover': {
            boxShadow: `0 0 20px ${alpha(themeTokens.hacker.neon.cyan, 0.6)}`,
          },
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: `
        body {
          background-color: #05050a;
          background-image: linear-gradient(rgba(5, 5, 10, 0.5), rgba(5, 5, 10, 0.75)), url("/staticfiles/img/neon_city.png");
          background-size: cover;
          background-position: center;
          background-attachment: fixed;
          background-repeat: no-repeat;
          color: ${themeTokens.hacker.cyber.text};
          margin: 0;
        }
      `,
    },
  },
});

// Clean Theme (Cyan Focus)
export const cleanTheme: Theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: themeTokens.clean.primary },
    secondary: { main: themeTokens.clean.secondary },
    background: {
      default: themeTokens.clean.bg.primary,
      paper: themeTokens.clean.bg.secondary,
    },
    text: {
      primary: themeTokens.clean.text,
      secondary: alpha(themeTokens.clean.text, 0.7),
    },
    divider: themeTokens.clean.border,
  },
  typography: {
    ...baseTypography,
    h1: { ...baseTypography.h1, fontFamily: '"Inter", sans-serif' },
    h2: { ...baseTypography.h2, fontFamily: '"Inter", sans-serif' },
    h3: { ...baseTypography.h3, fontFamily: '"Inter", sans-serif' },
    h4: { ...baseTypography.h4, fontFamily: '"Inter", sans-serif' },
    h5: { ...baseTypography.h5, fontFamily: '"Inter", sans-serif' },
    h6: { ...baseTypography.h6, fontFamily: '"Inter", sans-serif' },
  },
  shape: { borderRadius: 4 },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: themeTokens.clean.bg.secondary,
          border: `1px solid ${themeTokens.clean.border}`,
          borderRadius: 4,
          boxShadow: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'uppercase',
          letterSpacing: '1px',
          fontWeight: 'bold',
          borderRadius: 4,
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: `
        body {
          background-color: ${themeTokens.clean.bg.primary};
          color: ${themeTokens.clean.text};
        }
      `,
    },
  },
});

// Script Kiddie Theme (Magenta Focus)
export const scriptKiddieTheme: Theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: themeTokens.script_kiddie.primary },
    secondary: { main: themeTokens.script_kiddie.secondary },
    background: {
      default: themeTokens.script_kiddie.bg.primary,
      paper: themeTokens.script_kiddie.bg.secondary,
    },
    text: {
      primary: themeTokens.script_kiddie.text,
      secondary: alpha(themeTokens.script_kiddie.text, 0.7),
    },
    divider: themeTokens.script_kiddie.border,
  },
  typography: baseTypography,
  shape: { borderRadius: 0 },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: themeTokens.script_kiddie.bg.secondary,
          border: `1px solid ${themeTokens.script_kiddie.border}`,
          boxShadow: themeTokens.script_kiddie.glow,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'uppercase',
          fontWeight: 'bold',
          borderRadius: 0,
          border: `1px solid ${themeTokens.script_kiddie.primary}`,
          '&:hover': {
            backgroundColor: themeTokens.script_kiddie.primary,
            color: themeTokens.script_kiddie.bg.primary,
          },
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: `
        body {
          background-color: ${themeTokens.script_kiddie.bg.primary};
          color: ${themeTokens.script_kiddie.text};
        }
        h1, h2, h3, h4, h5, h6 {
            color: ${themeTokens.script_kiddie.primary};
        }
      `,
    },
  },
});

export const neonHackerTheme = hackerTheme;
