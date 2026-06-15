import { useTheme } from '@mui/material/styles';
import { useAppTheme } from '../context/ThemeContext';
import { getSemanticColors } from './semanticColors';

/** Primary hook for theme-aware colors in feature components */
export function useSemanticColors() {
  const theme = useTheme();
  const { themeName } = useAppTheme();
  const semantic = getSemanticColors(themeName);

  return {
    ...semantic,
    theme,
    themeName,
  };
}
