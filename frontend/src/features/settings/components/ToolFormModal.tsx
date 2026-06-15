import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControlLabel,
  Checkbox,
  Box,
  Typography,
  Grid,
  IconButton
} from '@mui/material';
import { X, Save, Hammer } from 'lucide-react';
import type { InstalledTool } from '../api';
import { useThemeTokens } from '../../../theme/useThemeTokens';

interface ToolFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (formData: FormData) => void;
  tool?: InstalledTool;
}

export const ToolFormModal: React.FC<ToolFormModalProps> = ({
  open,
  onClose,
  onSubmit,
  tool
}) => {
  const { tokens } = useThemeTokens();
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    github_url: '',
    license_url: '',
    logo_url: '',
    install_command: '',
    update_command: '',
    version_lookup_command: '',
    version_match_regex: '[vV]*(\\d+\\.)?(\\d+\\.)?(\\*|\\d+)',
    is_subdomain_gathering: false,
    subdomain_gathering_command: 'tool_name -d {TARGET} -o {OUTPUT}'
  });

  useEffect(() => {
    if (tool) {
      setFormData({
        name: tool.name || '',
        description: tool.description || '',
        github_url: tool.github_url || '',
        license_url: tool.license_url || '',
        logo_url: tool.logo_url || '',
        install_command: tool.install_command || '',
        update_command: tool.update_command || '',
        version_lookup_command: tool.version_lookup_command || '',
        version_match_regex: tool.version_match_regex || '[vV]*(\\d+\\.)?(\\d+\\.)?(\\*|\\d+)',
        is_subdomain_gathering: tool.is_subdomain_gathering || false,
        subdomain_gathering_command: tool.subdomain_gathering_command || 'tool_name -d {TARGET} -o {OUTPUT}'
      });
    } else {
      setFormData({
        name: '',
        description: '',
        github_url: '',
        license_url: '',
        logo_url: '',
        install_command: '',
        update_command: '',
        version_lookup_command: '',
        version_match_regex: '[vV]*(\\d+\\.)?(\\d+\\.)?(\\*|\\d+)',
        is_subdomain_gathering: false,
        subdomain_gathering_command: 'tool_name -d {TARGET} -o {OUTPUT}'
      });
    }
  }, [tool, open]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, checked, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data = new FormData();
    Object.entries(formData).forEach(([key, value]) => {
      if (typeof value === 'boolean') {
        if (value) data.append(key, 'on');
      } else {
        data.append(key, value);
      }
    });
    onSubmit(data);
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="md"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            bgcolor: 'background.paper',
            border: `1px solid ${tokens.accent.primary}33`,
            color: 'text.primary',
            backgroundImage: `linear-gradient(${tokens.accent.primary}0D 1px, transparent 1px), linear-gradient(90deg, ${tokens.accent.primary}0D 1px, transparent 1px)`,
            backgroundSize: '20px 20px'
          }
        }
      }}
    >
      <DialogTitle sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        borderBottom: 1,
        borderColor: 'divider',
        fontFamily: 'Orbitron',
        fontWeight: 'bold',
        color: tokens.accent.primary
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Hammer size={20} />
          {tool ? 'MODIFY TOOL' : 'ADD NEW TOOL'}
        </Box>
        <IconButton onClick={onClose} sx={{ color: 'text.secondary' }}>
          <X size={20} />
        </IconButton>
      </DialogTitle>
      
      <form onSubmit={handleSubmit}>
        <DialogContent sx={{ mt: 2 }}>
          <Grid container spacing={3}>
            <Grid size={{xs: 12, md: 6}} >
              <TextField
                fullWidth
                label="Tool Name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                variant="outlined"
                required
                slotProps={{ inputLabel: { sx: { color: `${tokens.accent.primary}B3` } } }}
                sx={{ '& .MuiOutlinedInput-root': { color: 'text.primary', '& fieldset': { borderColor: 'divider' } } }}
              />
            </Grid>
            <Grid size={{xs: 12, md: 6}} >
              <TextField
                fullWidth
                label="Logo URL"
                name="logo_url"
                value={formData.logo_url}
                onChange={handleChange}
                variant="outlined"
                slotProps={{ inputLabel: { sx: { color: `${tokens.accent.primary}B3` } } }}
                sx={{ '& .MuiOutlinedInput-root': { color: 'text.primary', '& fieldset': { borderColor: 'divider' } } }}
              />
            </Grid>
            <Grid size={{xs: 12}} >
              <TextField
                fullWidth
                label="Description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                variant="outlined"
                multiline
                rows={2}
                slotProps={{ inputLabel: { sx: { color: `${tokens.accent.primary}B3` } } }}
                sx={{ '& .MuiOutlinedInput-root': { color: 'text.primary', '& fieldset': { borderColor: 'divider' } } }}
              />
            </Grid>
            <Grid size={{xs: 12, md: 6}} >
              <TextField
                fullWidth
                label="GitHub URL"
                name="github_url"
                value={formData.github_url}
                onChange={handleChange}
                variant="outlined"
                required
                slotProps={{ inputLabel: { sx: { color: `${tokens.accent.primary}B3` } } }}
                sx={{ '& .MuiOutlinedInput-root': { color: 'text.primary', '& fieldset': { borderColor: 'divider' } } }}
              />
            </Grid>
            <Grid size={{xs: 12, md: 6}} >
              <TextField
                fullWidth
                label="License URL"
                name="license_url"
                value={formData.license_url}
                onChange={handleChange}
                variant="outlined"
                slotProps={{ inputLabel: { sx: { color: `${tokens.accent.primary}B3` } } }}
                sx={{ '& .MuiOutlinedInput-root': { color: 'text.primary', '& fieldset': { borderColor: 'divider' } } }}
              />
            </Grid>
            <Grid size={{xs: 12}} >
              <Typography variant="caption" sx={{ color: `${tokens.accent.primary}80`, mb: 1, display: 'block' }}>
                COMMAND CONFIGURATION
              </Typography>
              <TextField
                fullWidth
                label="Install Command"
                name="install_command"
                value={formData.install_command}
                onChange={handleChange}
                variant="outlined"
                required
                placeholder="e.g. go install github.com/project/tool@latest"
                slotProps={{ inputLabel: { sx: { color: `${tokens.accent.primary}B3` } } }}
                sx={{ mb: 2, '& .MuiOutlinedInput-root': { color: 'text.primary', '& fieldset': { borderColor: 'divider' } } }}
              />
              <TextField
                fullWidth
                label="Update Command"
                name="update_command"
                value={formData.update_command}
                onChange={handleChange}
                variant="outlined"
                placeholder="e.g. go install github.com/project/tool@latest"
                slotProps={{ inputLabel: { sx: { color: `${tokens.accent.primary}B3` } } }}
                sx={{ mb: 2, '& .MuiOutlinedInput-root': { color: 'text.primary', '& fieldset': { borderColor: 'divider' } } }}
              />
              <TextField
                fullWidth
                label="Version Lookup Command"
                name="version_lookup_command"
                value={formData.version_lookup_command}
                onChange={handleChange}
                variant="outlined"
                placeholder="e.g. tool --version"
                slotProps={{ inputLabel: { sx: { color: `${tokens.accent.primary}B3` } } }}
                sx={{ mb: 2, '& .MuiOutlinedInput-root': { color: 'text.primary', '& fieldset': { borderColor: 'divider' } } }}
              />
              <TextField
                fullWidth
                label="Version Match Regex"
                name="version_match_regex"
                value={formData.version_match_regex}
                onChange={handleChange}
                variant="outlined"
                slotProps={{ inputLabel: { sx: { color: `${tokens.accent.primary}B3` } } }}
                sx={{ '& .MuiOutlinedInput-root': { color: 'text.primary', '& fieldset': { borderColor: 'divider' } } }}
              />
            </Grid>
            <Grid size={{xs: 12}} >
              <Box sx={{ p: 2, border: 1, borderColor: `${tokens.accent.primary}1A`, borderRadius: 1, bgcolor: `${tokens.accent.primary}05` }}>
                <FormControlLabel
                  control={
                    <Checkbox 
                      name="is_subdomain_gathering"
                      checked={formData.is_subdomain_gathering}
                      onChange={handleChange}
                      sx={{ color: tokens.accent.primary, '&.Mui-checked': { color: tokens.accent.primary } }}
                    />
                  }
                  label={<Typography sx={{ color: 'text.secondary', fontFamily: 'Orbitron', fontSize: '12px' }}>USED FOR SUBDOMAIN GATHERING</Typography>}
                />
                {formData.is_subdomain_gathering && (
                  <TextField
                    fullWidth
                    label="Subdomain Gathering Command"
                    name="subdomain_gathering_command"
                    value={formData.subdomain_gathering_command}
                    onChange={handleChange}
                    variant="outlined"
                    placeholder="e.g. tool_name -d {TARGET} -o {OUTPUT}"
                    slotProps={{ inputLabel: { sx: { color: `${tokens.accent.primary}B3` } } }}
                    sx={{ mt: 2, '& .MuiOutlinedInput-root': { color: 'text.primary', '& fieldset': { borderColor: 'divider' } } }}
                  />
                )}
              </Box>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions sx={{ p: 3, borderTop: 1, borderColor: 'divider' }}>
          <Button onClick={onClose} sx={{ color: 'text.secondary' }}>
            CANCEL
          </Button>
          <Button 
            type="submit"
            variant="contained" 
            startIcon={<Save size={18} />}
            sx={{ 
              bgcolor: tokens.accent.primary, 
              color: '#000', 
              fontWeight: 'bold',
              '&:hover': { bgcolor: tokens.accent.primary, filter: 'brightness(1.1)' }
            }}
          >
            {tool ? 'UPDATE TOOL' : 'REGISTER TOOL'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};
