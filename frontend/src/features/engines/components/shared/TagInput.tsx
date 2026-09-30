import React from 'react';
import { Autocomplete, TextField, Chip } from '@mui/material';
import { getFieldSx } from '../../../../theme/semanticColors';
import { useThemeTokens } from '../../../../theme/useThemeTokens';

interface TagInputProps {
  label: string;
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  helperText?: string;
}

export const TagInput: React.FC<TagInputProps> = ({ label, value, onChange, placeholder, helperText }) => {
  const { tokens, isLight } = useThemeTokens();

  return (
    <Autocomplete<string, true, false, true>
      multiple
      freeSolo
      options={[]}
      value={value}
      onChange={(_event, next) => onChange(next)}
      renderValue={(tagValues, getItemProps) =>
        tagValues.map((option, index) => {
          const { key, ...itemProps } = getItemProps({ index });
          return (
            <Chip
              key={key}
              {...itemProps}
              label={option}
              size="small"
              sx={{
                bgcolor: isLight ? tokens.accent.primary + '15' : tokens.accent.primary + '25',
                color: tokens.accent.primary,
                border: `1px solid ${tokens.accent.primary + '50'}`,
              }}
            />
          );
        })
      }
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          placeholder={placeholder ?? 'Type and press Enter'}
          helperText={helperText}
          size="small"
          sx={getFieldSx(isLight, tokens)}
        />
      )}
      sx={{ mb: 2 }}
    />
  );
};
