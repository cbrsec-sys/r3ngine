import React, { useState } from 'react';
import {
  IconButton,
  Menu,
  MenuItem,
  Typography,
  Box,
  Tooltip,
  useTheme
} from '@mui/material';
import { Palette, Check } from 'lucide-react';
import type { ThemeType } from '../../theme/tokens';
import { themeTokens } from '../../theme/tokens';

import { useAppTheme } from '../../context/ThemeContext';



export const HeaderThemeSwitcher: React.FC = () => {
  const { themeName, setTheme } = useAppTheme();
  const theme = useTheme();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleSelect = (name: ThemeType) => {
    setTheme(name);
    handleClose();
  };

  const themes = [
    { id: 'hacker', label: 'V3 Hacker', color: themeTokens.hacker.neon.pink },
    { id: 'modern', label: 'V3 Hybrid', color: themeTokens.modern.neon.cyan },
    { id: 'enterprise', label: 'V3 Enterprise', color: themeTokens.enterprise.palette.primary },
  ] as const;


  return (
    <>
      <Tooltip title="Switch Theme">
        <IconButton
          onClick={handleOpen}
          size="small"
          sx={{
            color: anchorEl ? theme.palette.primary.main : alpha(theme.palette.text.secondary, 0.5),
            bgcolor: anchorEl ? alpha(theme.palette.primary.main, 0.1) : 'transparent',
            '&:hover': {
              color: theme.palette.primary.main,
              bgcolor: alpha(theme.palette.primary.main, 0.05),
            }
          }}
        >
          <Palette size={18} />
        </IconButton>
      </Tooltip>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        slotProps={{
          paper: {
            sx: {
              bgcolor: alpha(theme.palette.background.paper, 0.95),
              backdropFilter: 'blur(15px)',
              border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
              borderRadius: 2,
              minWidth: 200,
              mt: 1.5,
              boxShadow: themeName === 'enterprise' ? theme.shadows[4] : `0 8px 32px ${alpha('#000', 0.8)}`,
              overflow: 'hidden',
            }
          }
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <Box sx={{ px: 2, py: 1.5, borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`, mb: 1 }}>
          <Typography sx={{
            fontSize: '0.7rem',
            color: theme.palette.primary.main,
            fontFamily: 'var(--r3-heading-font)',
            fontWeight: 800,
            letterSpacing: 1
          }}>
            THEME SELECTOR
          </Typography>
        </Box>

        {themes.map((t) => (
          <MenuItem
            key={t.id}
            onClick={() => handleSelect(t.id)}
            sx={{
              py: 1.5,
              px: 2.5,
              gap: 2,
              color: themeName === t.id ? theme.palette.primary.main : alpha(theme.palette.text.primary, 0.7),
              fontFamily: 'var(--r3-heading-font)',
              fontSize: '0.75rem',
              letterSpacing: '1px',
              '&:hover': {
                bgcolor: alpha(theme.palette.primary.main, 0.1),
                color: theme.palette.primary.main,
              }
            }}
          >
            <Box sx={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              bgcolor: t.color,
              boxShadow: themeName !== 'enterprise' ? `0 0 5px ${t.color}` : 'none'
            }} />
            <Typography sx={{ fontSize: 'inherit', fontFamily: 'inherit', fontWeight: 600, flexGrow: 1 }}>
              {t.label}
            </Typography>
            {themeName === t.id && <Check size={14} />}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};

// Helper since alpha isn't imported from mui
function alpha(color: string, value: number) {
  return color.startsWith('rgb') ? color.replace(')', `, ${value})`).replace('rgb', 'rgba') : `${color}${Math.floor(value * 255).toString(16).padStart(2, '0')}`;
}
