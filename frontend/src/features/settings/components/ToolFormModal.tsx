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
            bgcolor: '#0a0a0a',
            border: '1px solid rgba(0,243,255,0.2)',
            color: '#fff',
            backgroundImage: 'linear-gradient(rgba(0,243,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0,243,255,0.05) 1px, transparent 1px)',
            backgroundSize: '20px 20px'
          }
        }
      }}
    >
      <DialogTitle sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        fontFamily: 'Orbitron',
        fontWeight: 'bold',
        color: '#00f3ff'
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Hammer size={20} />
          {tool ? 'MODIFY_TOOL' : 'ADD_NEW_TOOL'}
        </Box>
        <IconButton onClick={onClose} sx={{ color: 'rgba(255,255,255,0.5)' }}>
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
                slotProps={{ inputLabel: { sx: { color: 'rgba(0,243,255,0.7)' } } }}
                sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(255,255,255,0.2)' } } }}
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
                slotProps={{ inputLabel: { sx: { color: 'rgba(0,243,255,0.7)' } } }}
                sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(255,255,255,0.2)' } } }}
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
                slotProps={{ inputLabel: { sx: { color: 'rgba(0,243,255,0.7)' } } }}
                sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(255,255,255,0.2)' } } }}
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
                slotProps={{ inputLabel: { sx: { color: 'rgba(0,243,255,0.7)' } } }}
                sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(255,255,255,0.2)' } } }}
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
                slotProps={{ inputLabel: { sx: { color: 'rgba(0,243,255,0.7)' } } }}
                sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(255,255,255,0.2)' } } }}
              />
            </Grid>
            <Grid size={{xs: 12}} >
              <Typography variant="caption" sx={{ color: 'rgba(0,243,255,0.5)', mb: 1, display: 'block' }}>
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
                slotProps={{ inputLabel: { sx: { color: 'rgba(0,243,255,0.7)' } } }}
                sx={{ mb: 2, '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(255,255,255,0.2)' } } }}
              />
              <TextField
                fullWidth
                label="Update Command"
                name="update_command"
                value={formData.update_command}
                onChange={handleChange}
                variant="outlined"
                placeholder="e.g. go install github.com/project/tool@latest"
                slotProps={{ inputLabel: { sx: { color: 'rgba(0,243,255,0.7)' } } }}
                sx={{ mb: 2, '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(255,255,255,0.2)' } } }}
              />
              <TextField
                fullWidth
                label="Version Lookup Command"
                name="version_lookup_command"
                value={formData.version_lookup_command}
                onChange={handleChange}
                variant="outlined"
                placeholder="e.g. tool --version"
                slotProps={{ inputLabel: { sx: { color: 'rgba(0,243,255,0.7)' } } }}
                sx={{ mb: 2, '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(255,255,255,0.2)' } } }}
              />
              <TextField
                fullWidth
                label="Version Match Regex"
                name="version_match_regex"
                value={formData.version_match_regex}
                onChange={handleChange}
                variant="outlined"
                slotProps={{ inputLabel: { sx: { color: 'rgba(0,243,255,0.7)' } } }}
                sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(255,255,255,0.2)' } } }}
              />
            </Grid>
            <Grid size={{xs: 12}} >
              <Box sx={{ p: 2, border: '1px solid rgba(0,243,255,0.1)', borderRadius: 1, bgcolor: 'rgba(0,243,255,0.02)' }}>
                <FormControlLabel
                  control={
                    <Checkbox 
                      name="is_subdomain_gathering"
                      checked={formData.is_subdomain_gathering}
                      onChange={handleChange}
                      sx={{ color: '#00f3ff', '&.Mui-checked': { color: '#00f3ff' } }}
                    />
                  }
                  label={<Typography sx={{ color: 'rgba(255,255,255,0.8)', fontFamily: 'Orbitron', fontSize: '12px' }}>USED_FOR_SUBDOMAIN_GATHERING</Typography>}
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
                    slotProps={{ inputLabel: { sx: { color: 'rgba(0,243,255,0.7)' } } }}
                    sx={{ mt: 2, '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(255,255,255,0.2)' } } }}
                  />
                )}
              </Box>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions sx={{ p: 3, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          <Button onClick={onClose} sx={{ color: 'rgba(255,255,255,0.5)' }}>
            CANCEL
          </Button>
          <Button 
            type="submit"
            variant="contained" 
            startIcon={<Save size={18} />}
            sx={{ 
              bgcolor: '#00f3ff', 
              color: '#000', 
              fontWeight: 'bold',
              '&:hover': { bgcolor: '#00d8e4' }
            }}
          >
            {tool ? 'UPDATE_TOOL' : 'REGISTER_TOOL'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};
