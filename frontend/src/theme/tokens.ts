export interface ThemeSemanticTokens {
  bg: {
    primary: string;
    secondary: string;
    glass: string;
  };
  accent: {
    primary: string;
    secondary: string;
    success: string;
    warning: string;
    error: string;
    info: string;
  };
  effects?: {
    blur?: string;
    radius?: string;
    bezier?: string;
  };
}

export type ThemeType = 'hacker' | 'modern' | 'enterprise' | 'clean' | 'script_kiddie' | 'v3_light';


export const themeTokens: Record<string, ThemeSemanticTokens | any> = {
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
    accent: {
      primary: '#00f3ff',
      secondary: '#bc13fe',
      success: '#00ff62',
      warning: '#ff9f00',
      error: '#ff003c',
      info: '#00aaff'
    }
  },
  modern: {
    bg: {
      primary: '#0f172a',
      secondary: '#1e293b',
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
    accent: {
      primary: '#00f3ff',
      secondary: '#bc13fe',
      success: '#00ff62',
      warning: '#ff9f00',
      error: '#ff003c',
      info: '#00aaff'
    }
  },
  enterprise: {
    bg: {
      primary: '#f8fafc',
      secondary: '#ffffff',
      glass: 'rgba(255, 255, 255, 0.8)'
    },
    palette: {
      primary: '#0284c7',
      secondary: '#475569',
      background: '#f8fafc',
      paper: '#ffffff',
      text: '#0f172a',
      border: '#e2e8f0',
    },
    accent: {
      primary: '#0284c7',
      secondary: '#475569',
      success: '#059669',
      warning: '#d97706',
      error: '#dc2626',
      info: '#0ea5e9'
    }
  },
  v3_light: {
    bg: {
      primary: '#4cbbd9',
      secondary: '#3aaec9',
      glass: 'rgba(255, 255, 255, 0.4)',
    },
    neon: {
      cyan: '#4cbbd9',
      pink: '#ff00ff',
      purple: '#bc13fe',
    },
    cyber: {
      text: '#0f172a',
      border: 'rgba(76, 187, 217, 0.2)',
      glow: {
        cyan: '0 0 15px rgba(76, 187, 217, 0.3)',
        pink: '0 0 15px rgba(255, 0, 255, 0.3)',
      },
    },
    accent: {
      primary: '#4cbbd9',
      secondary: '#7000ff',
      success: '#059669',
      warning: '#d97706',
      error: '#dc2626',
      info: '#0ea5e9'
    }
  },
  effects: {
    blur: 'blur(14px)',
    radius: '18px',
    bezier: 'cubic-bezier(0.32, 0.72, 0, 1)',
  }
};
