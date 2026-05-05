import React, { useState } from 'react';
import {
  IconButton,
  Menu,
  MenuItem,
  Typography,
  Box,
  Tooltip
} from '@mui/material';
import { Palette, Check } from 'lucide-react';
import type { ThemeType } from '../../theme/tokens';

import { useAppTheme } from '../../context/ThemeContext';



export const HeaderThemeSwitcher: React.FC = () => {
  const { themeName, setTheme } = useAppTheme();
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
    { id: 'hacker', label: 'V3 Hacker', color: '#00f3ff' },
    { id: 'clean', label: 'V3 Clean', color: '#00d2ff' },
    { id: 'script_kiddie', label: 'V3 Script Kiddie', color: '#ff00ff' },
  ] as const;


  return (
    <>
      <Tooltip title="Switch Theme">
        <IconButton
          onClick={handleOpen}
          size="small"
          sx={{
            color: anchorEl ? '#00f3ff' : 'rgba(255,255,255,0.5)',
            bgcolor: anchorEl ? 'rgba(0, 243, 255, 0.1)' : 'transparent',
            '&:hover': {
              color: '#00f3ff',
              bgcolor: 'rgba(0, 243, 255, 0.05)',
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
              bgcolor: 'rgba(10, 10, 15, 0.98)',
              backdropFilter: 'blur(15px)',
              border: '1px solid rgba(0, 243, 255, 0.2)',
              borderRadius: 2,
              minWidth: 200,
              mt: 1.5,
              boxShadow: '0 8px 32px rgba(0,0,0,0.8)',
              overflow: 'hidden',
            }
          }
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid rgba(255,255,255,0.05)', mb: 1 }}>
          <Typography sx={{
            fontSize: '0.7rem',
            color: '#00f3ff',
            fontFamily: 'Orbitron',
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
              color: themeName === t.id ? '#00f3ff' : 'rgba(255,255,255,0.7)',
              fontFamily: 'Orbitron',
              fontSize: '0.75rem',
              letterSpacing: '1px',
              '&:hover': {
                bgcolor: 'rgba(0, 243, 255, 0.1)',
                color: '#00f3ff',
              }
            }}
          >
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: t.color, boxShadow: `0 0 5px ${t.color}` }} />
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
