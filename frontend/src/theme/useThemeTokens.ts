import { useTheme } from '@mui/material/styles';
import { getResolvedTokens, type ThemeType } from './tokens';
import { useAppTheme } from '../context/ThemeContext';

export function useThemeTokens() {
  const theme = useTheme();
  const { themeName } = useAppTheme();

  const tokenKey = ((themeName as string) === 'v3_awvs' ? 'v3_light' : themeName) as ThemeType;
  const tokens = getResolvedTokens(tokenKey);
  const isLight = tokens.mode === 'light';
  const isCyber = tokens.cyberEffects;

  return { tokens, isLight, isCyber, theme, themeName: tokenKey };
}
