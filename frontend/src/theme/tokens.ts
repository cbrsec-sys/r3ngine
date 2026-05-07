export const themeTokens = {
  hacker: {
    bg: {
      primary: '#0a0a0f',
      secondary: '#12121a',
      glass: 'rgba(12, 10, 20, 0.75)',
    },
    neon: {
      cyan: '#00f3ff',
      pink: '#ff00ff',
      purple: '#bc13fe',
    },
    cyber: {
      text: '#e0e0e0',
      border: 'rgba(0, 243, 255, 0.2)',
      glow: {
        cyan: '0 0 15px rgba(0, 243, 255, 0.3)',
        pink: '0 0 15px rgba(255, 0, 255, 0.3)',
      },
    },
  },
  modern: { // Hybrid Theme
    bg: {
      primary: '#0f172a', // Slate 900
      secondary: '#1e293b', // Slate 800
      glass: 'rgba(15, 23, 42, 0.8)',
    },
    neon: {
      cyan: '#00f3ff',
      pink: '#ff00ff',
      purple: '#bc13fe',
    },
    cyber: {
      text: '#f8fafc',
      border: 'rgba(0, 243, 255, 0.15)',
      glow: {
        cyan: '0 0 10px rgba(0, 243, 255, 0.2)',
        pink: '0 0 10px rgba(255, 0, 255, 0.2)',
      },
    },
  },
  enterprise: { // Professional Theme
    bg: {
      primary: '#f8fafc', // Slate 50 (Light mode feel but keeping dark if needed, let's use dark slate for consistency with app logic)
      secondary: '#ffffff',
    },
    // We'll use a deep professional blue palette
    palette: {
      primary: '#0284c7', // Sky 600
      secondary: '#475569', // Slate 600
      background: '#f8fafc',
      paper: '#ffffff',
      text: '#0f172a',
      border: '#e2e8f0',
    }
  },
  effects: {
    blur: 'blur(14px)',
    radius: '18px',
    bezier: 'cubic-bezier(0.32, 0.72, 0, 1)',
  }
};

export type ThemeType = 'hacker' | 'modern' | 'enterprise' | 'clean' | 'script_kiddie';

