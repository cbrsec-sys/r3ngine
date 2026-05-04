import React, { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import { hackerTheme, cleanTheme, scriptKiddieTheme } from '../theme';
import type { Theme } from '@mui/material/styles';

import type { ThemeType } from '../theme/tokens';

interface ThemeContextType {
  themeName: ThemeType;
  setTheme: (name: ThemeType) => void;
}


const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const themes: Record<ThemeType, Theme> = {
  hacker: hackerTheme,
  clean: cleanTheme,
  script_kiddie: scriptKiddieTheme,
};

export const CustomThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [themeName, setThemeName] = useState<ThemeType>(() => {
    const saved = localStorage.getItem('rengine-theme');
    if (saved === 'hacker' || saved === 'clean' || saved === 'script_kiddie') {
      return saved as ThemeType;
    }
    return 'hacker';
  });

  const setTheme = (name: ThemeType) => {
    setThemeName(name);
    localStorage.setItem('rengine-theme', name);
  };

  useEffect(() => {
    document.body.setAttribute('data-v3-theme', themeName);
    document.body.setAttribute('data-ui-version', 'v3');
  }, [themeName]);

  // Ensure we always have a theme object, fallback to hackerTheme
  const activeTheme = themes[themeName] || hackerTheme;

  return (
    <ThemeContext.Provider value={{ themeName, setTheme }}>
      <ThemeProvider theme={activeTheme}>
        {children}
      </ThemeProvider>
    </ThemeContext.Provider>
  );
};


export const useAppTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useAppTheme must be used within a CustomThemeProvider');
  }
  return context;
};

