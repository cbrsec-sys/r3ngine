import { useThemeTokens } from '../theme/useThemeTokens';
import React from 'react';
import { MenuItem, Typography, Box, Divider } from '@mui/material';
import { Palette, Check } from 'lucide-react';
import { useAppTheme } from '../context/ThemeContext';

export const ThemeSwitcher: React.FC = () => {
  const { tokens } = useThemeTokens();
  const { themeName, setTheme } = useAppTheme();


  const themes = [
    { id: 'hacker', label: 'V3 Hacker', color: tokens.accent.primary },
    { id: 'clean', label: 'V3 Clean', color: '#00d2ff' },
    { id: 'script_kiddie', label: 'V3 Script Kiddie', color: tokens.accent.secondary },
  ] as const;

  return (
    <>
      <Box sx={{ px: 2.5, py: 1.5, display: 'flex', alignItems: 'center', gap: 1.5, color: 'rgba(255,255,255,0.4)' }}>
        <Palette size={14} />
        <Typography sx={{ fontSize: '0.7rem', fontWeight: 600, letterSpacing: 0.5, textTransform: 'uppercase' }}>
          Interface Theme
        </Typography>
      </Box>
      
      {themes.map((t) => (
        <MenuItem 
          key={t.id} 
          onClick={() => setTheme(t.id)}
          sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            bgcolor: themeName === t.id ? 'rgba(0, 243, 255, 0.05) !important' : 'transparent',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: t.color, boxShadow: `0 0 5px ${t.color}` }} />
            <Typography sx={{ fontSize: 'inherit', fontFamily: 'inherit', fontWeight: 600 }}>
              {t.label}
            </Typography>
          </Box>
          {themeName === t.id && <Check size={14} style={{ color: t.color }} />}
        </MenuItem>
      ))}
    </>
  );
};
