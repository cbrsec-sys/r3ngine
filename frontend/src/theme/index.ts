import type { Theme } from '@mui/material/styles';
import { createAppTheme } from './createAppTheme';
import { themeDefinitions } from './tokens';

export const hackerTheme: Theme = createAppTheme(themeDefinitions.hacker, 'cyber');
export const modernTheme: Theme = createAppTheme(themeDefinitions.modern, 'cyber');
export const enterpriseTheme: Theme = createAppTheme(themeDefinitions.enterprise, 'enterprise');
export const v3LightTheme: Theme = createAppTheme(themeDefinitions.v3_light, 'light-cyber');

// Legacy aliases
export const cleanTheme = modernTheme;
export const scriptKiddieTheme = hackerTheme;
export const neonHackerTheme = hackerTheme;

export { createAppTheme } from './createAppTheme';
export * from './tokens';
export * from './semanticColors';
export { useSemanticColors } from './useSemanticColors';
