import React from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  ListSubheader,
  FormHelperText,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import { useScanProfiles } from '../api';
import type { ScanProfile } from '../types';

interface ProfileSelectorProps {
  value: string | null;
  onChange: (profileName: string | null) => void;
  disabled?: boolean;
}

const CATEGORY_LABELS: Record<ScanProfile['category'], string> = {
  speed: 'Speed',
  evasion: 'Evasion',
  content: 'Content',
  network: 'Network',
  general: 'General',
  hardware: 'Hardware',
};

const CATEGORY_ORDER: ScanProfile['category'][] = [
  'general',
  'speed',
  'network',
  'content',
  'evasion',
  'hardware',
];

const fieldStyles = {
  '& .MuiOutlinedInput-root': {
    color: '#fff',
    '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
    '&:hover fieldset': { borderColor: 'rgba(0, 255, 98, 0.3)' },
    '&.Mui-focused fieldset': { borderColor: '#00ff62' },
    bgcolor: 'rgba(255,255,255,0.03)',
  },
  '& .MuiInputLabel-root': {
    color: 'rgba(255,255,255,0.4)',
    '&.Mui-focused': { color: '#00ff62' },
  },
  '& .MuiSelect-icon': { color: 'rgba(255,255,255,0.4)' },
  '& .MuiFormHelperText-root': { color: 'rgba(255,255,255,0.3)' },
};

export const ProfileSelector: React.FC<ProfileSelectorProps> = ({
  value,
  onChange,
  disabled = false,
}) => {
  const { data: profiles, isLoading } = useScanProfiles();

  const handleChange = (event: SelectChangeEvent<string>) => {
    const selected = event.target.value;
    onChange(selected === '' ? null : selected);
  };

  const selectedProfile = profiles?.find((p) => p.name === value) ?? null;

  const groupedProfiles = React.useMemo(() => {
    if (!profiles) return new Map<ScanProfile['category'], ScanProfile[]>();
    const map = new Map<ScanProfile['category'], ScanProfile[]>();
    for (const profile of profiles) {
      const group = map.get(profile.category) ?? [];
      group.push(profile);
      map.set(profile.category, group);
    }
    return map;
  }, [profiles]);

  const menuItems: React.ReactNode[] = [];
  menuItems.push(
    <MenuItem key="__default__" value="">
      Default (no profile)
    </MenuItem>
  );

  for (const category of CATEGORY_ORDER) {
    const group = groupedProfiles.get(category);
    if (!group || group.length === 0) continue;
    menuItems.push(
      <ListSubheader
        key={`header-${category}`}
        sx={{
          bgcolor: 'rgba(0,0,0,0.7)',
          color: 'rgba(0, 255, 98, 0.7)',
          fontWeight: 800,
          fontSize: '0.65rem',
          letterSpacing: 1,
          lineHeight: '28px',
        }}
      >
        {CATEGORY_LABELS[category].toUpperCase()}
      </ListSubheader>
    );
    for (const profile of group) {
      menuItems.push(
        <MenuItem key={profile.name} value={profile.name}>
          {profile.name}
          {profile.is_builtin ? ' (built-in)' : ''}
        </MenuItem>
      );
    }
  }

  // Include any categories not in CATEGORY_ORDER
  for (const [category, group] of groupedProfiles.entries()) {
    if (CATEGORY_ORDER.includes(category)) continue;
    menuItems.push(
      <ListSubheader
        key={`header-${category}`}
        sx={{
          bgcolor: 'rgba(0,0,0,0.7)',
          color: 'rgba(0, 255, 98, 0.7)',
          fontWeight: 800,
          fontSize: '0.65rem',
          letterSpacing: 1,
          lineHeight: '28px',
        }}
      >
        {category.toUpperCase()}
      </ListSubheader>
    );
    for (const profile of group) {
      menuItems.push(
        <MenuItem key={profile.name} value={profile.name}>
          {profile.name}
          {profile.is_builtin ? ' (built-in)' : ''}
        </MenuItem>
      );
    }
  }

  const helperText = selectedProfile?.description ?? '';

  return (
    <FormControl fullWidth sx={fieldStyles} disabled={disabled || isLoading}>
      <InputLabel id="profile-selector-label">Scan Profile</InputLabel>
      <Select
        labelId="profile-selector-label"
        id="profile-selector"
        value={isLoading ? '' : (value ?? '')}
        label="Scan Profile"
        onChange={handleChange}
        MenuProps={{
          slotProps: { paper: {
            sx: {
              bgcolor: '#0a0a14',
              border: '1px solid rgba(0, 255, 98, 0.15)',
              '& .MuiMenuItem-root': {
                color: '#fff',
                '&:hover': { bgcolor: 'rgba(0, 255, 98, 0.08)' },
                '&.Mui-selected': {
                  bgcolor: 'rgba(0, 255, 98, 0.12)',
                  '&:hover': { bgcolor: 'rgba(0, 255, 98, 0.16)' },
                },
              },
            },
          } },
        }}
      >
        {isLoading ? (
          <MenuItem value="" disabled>
            Loading profiles…
          </MenuItem>
        ) : (
          menuItems
        )}
      </Select>
      {helperText && <FormHelperText>{helperText}</FormHelperText>}
    </FormControl>
  );
};
