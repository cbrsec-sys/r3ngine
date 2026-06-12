import { useTheme } from '@mui/material/styles';
import { themeTokens, type ThemeType } from './tokens';
import { useAppTheme } from '../context/ThemeContext';

export function useThemeTokens() {
  const theme = useTheme();
  const { themeName } = useAppTheme();
  
  // Safe fallback to hacker if somehow themeName is invalid or mapped to a legacy name not in tokens
  const tokenKey = ((themeName as string) === 'v3_awvs' ? 'v3_light' : themeName);
  const activeTokenName = themeTokens[tokenKey as ThemeType] ? tokenKey : 'hacker';
  const tokens = themeTokens[activeTokenName as ThemeType];
  const isLight = theme.palette.mode === 'light' || activeTokenName === 'enterprise' || activeTokenName === 'v3_light';
  
  return { tokens, isLight, theme };
}
