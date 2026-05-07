import React, { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { hackerTheme, modernTheme, enterpriseTheme } from '../theme';
import type { Theme } from '@mui/material/styles';

import type { ThemeType } from '../theme/tokens';
import { themeTokens } from '../theme/tokens';

interface ThemeContextType {
  themeName: ThemeType;
  setTheme: (name: ThemeType) => void;
}


const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const themes: Record<string, Theme> = {
  hacker: hackerTheme,
  modern: modernTheme,
  enterprise: enterpriseTheme,
  clean: modernTheme, // Legacy mapping
  script_kiddie: hackerTheme, // Legacy mapping
};

export const CustomThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [themeName, setThemeName] = useState<ThemeType>(() => {
    const saved = localStorage.getItem('rengine-v3-theme');
    if (saved === 'hacker' || saved === 'modern' || saved === 'enterprise') {
      return saved as ThemeType;
    }
    return 'hacker';
  });

  const setTheme = (name: ThemeType) => {
    setThemeName(name);
    localStorage.setItem('rengine-v3-theme', name);
  };

  useEffect(() => {
    document.body.setAttribute('data-v3-theme', themeName);
    document.body.setAttribute('data-ui-version', 'v3');

    // Inject typography and motion variables
    const root = document.documentElement;
    const isEnterprise = themeName === 'enterprise';
    
    root.style.setProperty('--r3-heading-font', isEnterprise ? '"Inter", sans-serif' : '"Orbitron", sans-serif');
    root.style.setProperty('--r3-body-font', '"Inter", sans-serif');
    root.style.setProperty('--r3-transition', themeTokens.effects.bezier);
    
    if (themeName === 'hacker') {
      document.body.classList.add('cyber-noise');
    } else {
      document.body.classList.remove('cyber-noise');
    }
  }, [themeName]);

  // Ensure we always have a theme object, fallback to hackerTheme
  const activeTheme = themes[themeName] || hackerTheme;

  return (
    <ThemeContext.Provider value={{ themeName, setTheme }}>
      <ThemeProvider theme={activeTheme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeContext.Provider>
  );
};


export const useAppTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    console.error('useAppTheme: Context is undefined. Ensure that the component is wrapped in <CustomThemeProvider>.');
    throw new Error('useAppTheme must be used within a CustomThemeProvider. If you see this, the component tree hierarchy is broken.');
  }
  return context;
};
