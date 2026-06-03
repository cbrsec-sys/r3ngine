import { createTheme, alpha, type Theme } from '@mui/material/styles';
import { themeTokens } from './tokens';

const baseTypography = {
  fontFamily: '"Inter", "Cerebri Sans", sans-serif',
  h1: { fontFamily: 'var(--r3-heading-font)', letterSpacing: '2px' },
  h2: { fontFamily: 'var(--r3-heading-font)', letterSpacing: '2px' },
  h3: { fontFamily: 'var(--r3-heading-font)', letterSpacing: '2px' },
  h4: { fontFamily: 'var(--r3-heading-font)', letterSpacing: '2px' },
  h5: { fontFamily: 'var(--r3-heading-font)', letterSpacing: '1px' },
  h6: { fontFamily: 'var(--r3-heading-font)', letterSpacing: '1px' },
};

// --- Shared Component Factories ---

const createHackerComponents = (tokens: any) => ({
  MuiCard: {
    styleOverrides: {
      root: {
        background: `linear-gradient(135deg, ${alpha(tokens.bg.secondary, 0.7)} 0%, ${alpha(tokens.bg.primary, 0.9)} 100%)`,
        backdropFilter: 'blur(25px) saturate(180%)',
        border: `1px solid ${alpha('#fff', 0.06)}`,
        // Double-Bezel (Inner Highlight)
        boxShadow: `inset 0 1px 1px ${alpha('#fff', 0.15)}, 0 15px 35px rgba(0, 0, 0, 0.8)`,
        borderRadius: tokens.effects?.radius || 18,
        transition: `all 0.4s ${themeTokens.effects.bezier}`,
        '&:hover': {
          transform: 'translateY(-6px) scale(1.005)',
          boxShadow: tokens.cyber.glow.cyan,
          borderColor: alpha(tokens.neon.cyan, 0.4),
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
        transition: `all 0.3s ${themeTokens.effects.bezier}`,
        '&:active': { transform: 'scale(0.98)' },
      },
      contained: {
        boxShadow: `0 0 10px ${alpha(tokens.neon.cyan, 0.3)}`,
        '&:hover': {
          boxShadow: `0 0 20px ${alpha(tokens.neon.cyan, 0.6)}`,
        },
      },
    },
  },
});

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
    ...createHackerComponents(themeTokens.hacker),
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

// Modern Theme (Hybrid)
export const modernTheme: Theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: themeTokens.modern.neon.cyan },
    secondary: { main: themeTokens.modern.neon.pink },
    background: {
      default: themeTokens.modern.bg.primary,
      paper: themeTokens.modern.bg.secondary,
    },
    text: {
      primary: themeTokens.modern.cyber.text,
      secondary: alpha(themeTokens.modern.cyber.text, 0.7),
    },
    divider: themeTokens.modern.cyber.border,
  },
  typography: baseTypography,
  shape: { borderRadius: 18 },
  components: {
    ...createHackerComponents(themeTokens.modern),
    MuiCssBaseline: {
      styleOverrides: `
        body {
          background-color: ${themeTokens.modern.bg.primary};
          color: ${themeTokens.modern.cyber.text};
        }
      `,
    },
  },
});

// Enterprise Theme (Professional)
export const enterpriseTheme: Theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: themeTokens.enterprise.palette.primary },
    secondary: { main: themeTokens.enterprise.palette.secondary },
    background: {
      default: themeTokens.enterprise.bg.primary,
      paper: themeTokens.enterprise.bg.secondary,
    },
    text: {
      primary: themeTokens.enterprise.palette.text,
      secondary: alpha(themeTokens.enterprise.palette.text, 0.7),
    },
    divider: themeTokens.enterprise.palette.border,
  },
  typography: baseTypography,
  shape: { borderRadius: 4 },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: themeTokens.enterprise.bg.secondary,
          border: `1px solid ${themeTokens.enterprise.palette.border}`,
          borderRadius: 8,
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          transition: 'none', // Fast & Flat
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none', // More professional
          fontWeight: 600,
          borderRadius: 6,
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: `
        body {
          background-color: ${themeTokens.enterprise.bg.primary};
          color: ${themeTokens.enterprise.palette.text};
        }
      `,
    },
  },
});

// Deprecated / Legacy fallbacks
export const cleanTheme = modernTheme;
export const scriptKiddieTheme = hackerTheme;
export const neonHackerTheme = hackerTheme;
