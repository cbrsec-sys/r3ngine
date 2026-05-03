import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  TextField,
  Button,
  Divider,
  Alert,
  Snackbar,
  IconButton,
  InputAdornment,
} from '@mui/material';
import {
  User,
  Lock,
  Eye,
  EyeOff,
  CheckCircle,
  AlertCircle,
  Shield,
} from 'lucide-react';
import { useParams } from '@tanstack/react-router';

export const ProfileSettingsPage: React.FC = () => {
  const { projectSlug } = useParams({ from: '/$projectSlug' });
  const [showOldPassword, setShowOldPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  const [formData, setFormData] = useState({
    old_password: '',
    new_password1: '',
    new_password2: '',
  });

  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (formData.new_password1 !== formData.new_password2) {
      setNotification({
        open: true,
        message: 'New passwords do not match!',
        severity: 'error',
      });
      return;
    }

    try {
      // Constructing form data for the legacy Django view
      const form = new FormData();
      form.append('old_password', formData.old_password);
      form.append('new_password1', formData.new_password1);
      form.append('new_password2', formData.new_password2);
      
      // We fetch the CSRF token from cookies
      const csrfToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];

      const response = await fetch(`/${projectSlug}/profile/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken || '',
        },
        body: form,
      });

      if (response.ok) {
        setNotification({
          open: true,
          message: 'Password changed successfully!',
          severity: 'success',
        });
        setFormData({
          old_password: '',
          new_password1: '',
          new_password2: '',
        });
      } else {
        setNotification({
          open: true,
          message: 'Failed to change password. Please check your old password.',
          severity: 'error',
        });
      }
    } catch (error) {
      setNotification({
        open: true,
        message: 'An error occurred while changing password.',
        severity: 'error',
      });
    }
  };

  const handleCloseNotification = () => {
    setNotification((prev) => ({ ...prev, open: false }));
  };

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 1200, margin: '0 auto' }}>
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography 
          variant="h4" 
          sx={{ 
            fontFamily: 'Orbitron', 
            fontWeight: 900, 
            letterSpacing: 2,
            color: '#fff',
            textShadow: '0 0 15px rgba(0, 243, 255, 0.3)'
          }}
        >
          MY PROFILE
        </Typography>
        <Box sx={{ flexGrow: 1, height: '1px', background: 'linear-gradient(90deg, rgba(0, 243, 255, 0.5), transparent)' }} />
      </Box>

      <Paper
        elevation={0}
        sx={{
          p: 4,
          background: 'rgba(10, 10, 15, 0.7)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(0, 243, 255, 0.1)',
          borderRadius: 2,
          position: 'relative',
          overflow: 'hidden',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '2px',
            background: 'linear-gradient(90deg, transparent, #00f3ff, transparent)',
            opacity: 0.5
          }
        }}
      >
        <Typography 
          variant="h5" 
          sx={{ 
            fontFamily: 'Orbitron', 
            mb: 4, 
            color: '#00f3ff',
            display: 'flex',
            alignItems: 'center',
            gap: 1.5,
            fontSize: '1.2rem'
          }}
        >
          HI ROOT!
        </Typography>

        <Grid container spacing={4}>
          {/* Username Section */}
          <Grid size={{xs: 12}} >
            <Typography variant="subtitle2" sx={{ color: 'rgba(255,255,255,0.5)', mb: 1, textTransform: 'uppercase', letterSpacing: 1 }}>
              Username
            </Typography>
            <TextField
              fullWidth
              value="@root"
              disabled
              variant="outlined"
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <User size={18} color="rgba(255,255,255,0.3)" />
                    </InputAdornment>
                  ),
                }
              }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  bgcolor: 'rgba(255,255,255,0.03)',
                  color: 'rgba(255,255,255,0.5)',
                  '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                }
              }}
            />
          </Grid>

          <Grid size={{xs: 12}} >
            <Divider sx={{ borderColor: 'rgba(0, 243, 255, 0.1)', my: 2 }} />
          </Grid>

          {/* Change Password Section */}
          <Grid size={{xs: 12}} >
            <Typography 
              variant="h6" 
              sx={{ 
                fontFamily: 'Orbitron', 
                mb: 3, 
                color: '#fff',
                fontSize: '1rem',
                letterSpacing: 1,
                display: 'flex',
                alignItems: 'center',
                gap: 1
              }}
            >
              <Lock size={18} color="#00f3ff" />
              CHANGE PASSWORD
            </Typography>

            <form onSubmit={handlePasswordChange}>
              <Grid container spacing={3}>
                <Grid size={{xs: 12}} >
                  <Typography variant="subtitle2" sx={{ color: 'rgba(255,255,255,0.6)', mb: 1 }}>
                    Old Password
                  </Typography>
                  <TextField
                    fullWidth
                    type={showOldPassword ? 'text' : 'password'}
                    name="old_password"
                    value={formData.old_password}
                    onChange={handleInputChange}
                    required
                    placeholder="Enter old password"
                    slotProps={{
                      input: {
                        endAdornment: (
                          <InputAdornment position="end">
                            <IconButton onClick={() => setShowOldPassword(!showOldPassword)} edge="end" sx={{ color: 'rgba(255,255,255,0.3)' }}>
                              {showOldPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </IconButton>
                          </InputAdornment>
                        ),
                      }
                    }}
                    sx={textFieldStyle}
                  />
                </Grid>

                <Grid size={{xs: 12, md: 6}} >
                  <Typography variant="subtitle2" sx={{ color: 'rgba(255,255,255,0.6)', mb: 1 }}>
                    New Password
                  </Typography>
                  <TextField
                    fullWidth
                    type={showNewPassword ? 'text' : 'password'}
                    name="new_password1"
                    value={formData.new_password1}
                    onChange={handleInputChange}
                    required
                    placeholder="Enter new password"
                    slotProps={{
                      input: {
                        endAdornment: (
                          <InputAdornment position="end">
                            <IconButton onClick={() => setShowNewPassword(!showNewPassword)} edge="end" sx={{ color: 'rgba(255,255,255,0.3)' }}>
                              {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </IconButton>
                          </InputAdornment>
                        ),
                      }
                    }}
                    sx={textFieldStyle}
                  />
                </Grid>

                <Grid size={{xs: 12, md: 6}} >
                  <Typography variant="subtitle2" sx={{ color: 'rgba(255,255,255,0.6)', mb: 1 }}>
                    Confirm Password
                  </Typography>
                  <TextField
                    fullWidth
                    type={showConfirmPassword ? 'text' : 'password'}
                    name="new_password2"
                    value={formData.new_password2}
                    onChange={handleInputChange}
                    required
                    placeholder="Confirm new password"
                    slotProps={{
                      input: {
                        endAdornment: (
                          <InputAdornment position="end">
                            <IconButton onClick={() => setShowConfirmPassword(!showConfirmPassword)} edge="end" sx={{ color: 'rgba(255,255,255,0.3)' }}>
                              {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </IconButton>
                          </InputAdornment>
                        ),
                      }
                    }}
                    sx={textFieldStyle}
                  />
                </Grid>

                <Grid size={{xs: 12}} sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
                  <Button
                    type="submit"
                    variant="contained"
                    sx={{
                      bgcolor: 'rgba(0, 243, 255, 0.1)',
                      color: '#00f3ff',
                      border: '1px solid #00f3ff',
                      fontFamily: 'Orbitron',
                      fontWeight: 600,
                      px: 4,
                      py: 1,
                      '&:hover': {
                        bgcolor: '#00f3ff',
                        color: '#000',
                        boxShadow: '0 0 20px rgba(0, 243, 255, 0.4)'
                      }
                    }}
                  >
                    CHANGE PASSWORD
                  </Button>
                </Grid>
              </Grid>
            </form>
          </Grid>
        </Grid>
      </Paper>

      {/* Security Info Card */}
      <Box sx={{ mt: 4 }}>
        <Paper
          sx={{
            p: 3,
            background: 'linear-gradient(135deg, rgba(255, 0, 60, 0.05) 0%, transparent 100%)',
            border: '1px solid rgba(255, 0, 60, 0.1)',
            borderRadius: 2,
            display: 'flex',
            alignItems: 'flex-start',
            gap: 2
          }}
        >
          <Shield color="#ff003c" size={24} style={{ marginTop: 4 }} />
          <Box>
            <Typography variant="h6" sx={{ color: '#ff003c', fontFamily: 'Orbitron', fontSize: '0.9rem', mb: 1 }}>
              SECURITY_PROTOCOL
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)', lineHeight: 1.6 }}>
              Ensure your password is at least 12 characters long and contains a mix of alphanumeric characters and special symbols. 
              Avoid reusing passwords from other platforms. Your security is the priority of the reNgine perimeter.
            </Typography>
          </Box>
        </Paper>
      </Box>

      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={handleCloseNotification}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Alert 
          onClose={handleCloseNotification} 
          severity={notification.severity}
          sx={{ 
            width: '100%',
            bgcolor: notification.severity === 'success' ? 'rgba(0, 200, 83, 0.9)' : 'rgba(211, 47, 47, 0.9)',
            color: '#fff',
            backdropFilter: 'blur(10px)',
            '& .MuiAlert-icon': { color: '#fff' }
          }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

const textFieldStyle = {
  '& .MuiOutlinedInput-root': {
    color: '#fff',
    bgcolor: 'rgba(255,255,255,0.03)',
    '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
    '&:hover fieldset': { borderColor: 'rgba(0, 243, 255, 0.3)' },
    '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
  },
  '& .MuiInputBase-input::placeholder': {
    color: 'rgba(255,255,255,0.2)',
    opacity: 1,
  }
};
