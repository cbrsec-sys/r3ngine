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
  clean: {
    bg: {
      primary: '#0f172a',
      secondary: '#1e293b',
      glass: 'rgba(30, 41, 59, 0.7)',
    },
    primary: '#00d2ff',
    secondary: '#3a7bd5',
    text: '#f8fafc',
    border: 'rgba(0, 210, 255, 0.2)',
    hover: 'rgba(0, 210, 255, 0.1)',
  },
  script_kiddie: {
    bg: {
      primary: '#0a0a0f',
      secondary: '#15151e',
      glass: 'rgba(21, 21, 30, 0.8)',
    },
    primary: '#ff00ff',
    secondary: '#00ffff',
    text: '#ffffff',
    border: 'rgba(255, 0, 255, 0.4)',
    glow: '0 0 8px rgba(255, 0, 255, 0.5)',
    hover: 'rgba(255, 0, 255, 0.15)',
  },
  effects: {
    blur: 'blur(14px)',
    radius: '18px',
  }
};

export type ThemeType = 'hacker' | 'clean' | 'script_kiddie';

