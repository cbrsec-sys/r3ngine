import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Button,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  Edit2 as EditIcon,
  Trash2 as DeleteIcon,
  UserPlus as PersonAddIcon,
  Power as PowerIcon,
} from 'lucide-react';
import { useUsers, useCreateUser, useToggleUserStatus, useUpdateUser, useDeleteUser } from '../api';
import type { User } from '../api';

const textFieldStyle = {
  '& .MuiOutlinedInput-root': {
    '& fieldset': { borderColor: 'rgba(0, 243, 255, 0.2)' },
    '&:hover fieldset': { borderColor: 'rgba(0, 243, 255, 0.5)' },
    '&.Mui-focused fieldset': { borderColor: '#00f3ff' },
    backgroundColor: 'rgba(0, 20, 40, 0.4)',
  },
  '& .MuiInputLabel-root': { color: 'rgba(0, 243, 255, 0.7)' },
  '& .MuiInputBase-input': { color: '#fff', fontFamily: 'Inter, sans-serif' },
};

const ROLES = [
  { value: 'system_administrator', label: 'Sys Admin' },
  { value: 'auditor', label: 'Auditor' },
  { value: 'penetration_tester', label: 'Penetration Tester' },
];

export const AdminSettingsPage: React.FC = () => {
  const { data: users, isLoading } = useUsers();
  const createUserMutation = useCreateUser();
  const toggleStatusMutation = useToggleUserStatus();
  const updateUserMutation = useUpdateUser();
  const deleteUserMutation = useDeleteUser();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    role: 'penetration_tester',
  });

  const handleOpenModal = (user: User | null = null) => {
    if (user) {
      setEditingUser(user);
      setFormData({
        username: user.username,
        password: '',
        role: user.role,
      });
    } else {
      setEditingUser(null);
      setFormData({
        username: '',
        password: '',
        role: 'penetration_tester',
      });
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingUser(null);
  };

  const handleSubmit = async () => {
    if (editingUser) {
      await updateUserMutation.mutateAsync({
        userId: editingUser.id,
        data: {
          role: formData.role,
          password: formData.password || undefined,
        },
      });
    } else {
      await createUserMutation.mutateAsync(formData);
    }
    handleCloseModal();
  };

  const handleToggleStatus = (userId: number) => {
    toggleStatusMutation.mutate(userId);
  };

  const handleDeleteUser = (userId: number) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      deleteUserMutation.mutate(userId);
    }
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="400px">
        <CircularProgress sx={{ color: '#00f3ff' }} />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4, maxWidth: '1200px', margin: '0 auto' }}>
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
          USER MANAGEMENT
        </Typography>
        <Box sx={{ flexGrow: 1, height: '1px', background: 'linear-gradient(90deg, rgba(0, 243, 255, 0.5), transparent)' }} />
        <Button
          variant="contained"
          startIcon={<PersonAddIcon size={18} />}
          onClick={() => handleOpenModal()}
          sx={{
            bgcolor: '#00f3ff',
            color: '#000',
            fontFamily: 'Orbitron',
            fontWeight: 900,
            fontSize: '11px',
            px: 3,
            height: '36px',
            '&:hover': { 
              bgcolor: '#00c8d4',
              boxShadow: '0 0 15px rgba(0, 243, 255, 0.4)'
            }
          }}
        >
          ADD NEW USER
        </Button>
      </Box>

      <TableContainer component={Paper} sx={{
        background: 'rgba(10, 25, 41, 0.7)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(0, 243, 255, 0.2)',
        borderRadius: '12px',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.8)',
      }}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: 'rgba(0, 243, 255, 0.05)' }}>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 'bold', fontFamily: 'Orbitron' }}>USERNAME</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 'bold', fontFamily: 'Orbitron' }}>NAME</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 'bold', fontFamily: 'Orbitron' }}>ROLE</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 'bold', fontFamily: 'Orbitron' }}>CREATED ON</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 'bold', fontFamily: 'Orbitron' }}>LAST LOGGED IN</TableCell>
              <TableCell sx={{ color: '#00f3ff', fontWeight: 'bold', fontFamily: 'Orbitron' }}>STATUS</TableCell>
              <TableCell align="right" sx={{ color: '#00f3ff', fontWeight: 'bold', fontFamily: 'Orbitron' }}>ACTIONS</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {users?.map((user) => (
              <TableRow key={user.id} sx={{ '&:hover': { backgroundColor: 'rgba(0, 243, 255, 0.02)' } }}>
                <TableCell sx={{ color: '#fff' }}>{user.username}</TableCell>
                <TableCell sx={{ color: '#fff' }}>{user.full_name}</TableCell>
                <TableCell>
                  <Chip 
                    label={user.role.replace('_', ' ').toUpperCase()} 
                    size="small"
                    sx={{ 
                      backgroundColor: 'rgba(188, 0, 255, 0.1)', 
                      color: '#bc00ff', 
                      border: '1px solid rgba(188, 0, 255, 0.3)',
                      fontFamily: 'Orbitron',
                      fontSize: '0.7rem'
                    }} 
                  />
                </TableCell>
                <TableCell sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>{user.date_joined_humanized}</TableCell>
                <TableCell sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>{user.last_login_humanized}</TableCell>
                <TableCell>
                  <Chip 
                    label={user.is_active ? 'ACTIVE' : 'INACTIVE'} 
                    size="small"
                    color={user.is_active ? 'success' : 'error'}
                    variant="outlined"
                    sx={{ fontFamily: 'Orbitron', fontSize: '0.6rem' }}
                  />
                </TableCell>
                <TableCell align="right">
                  <Tooltip title={user.is_active ? "Disable User" : "Enable User"}>
                    <IconButton size="small" onClick={() => handleToggleStatus(user.id)} sx={{ color: user.is_active ? '#00f3ff' : '#ff0055' }}>
                      <PowerIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Edit User">
                    <IconButton size="small" onClick={() => handleOpenModal(user)} sx={{ color: '#00f3ff' }}>
                      <EditIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete User">
                    <IconButton size="small" onClick={() => handleDeleteUser(user.id)} sx={{ color: '#ff0055' }}>
                      <DeleteIcon />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog 
        open={isModalOpen} 
        onClose={handleCloseModal}
        PaperProps={{
          sx: {
            background: 'rgba(10, 25, 41, 0.95)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(0, 243, 255, 0.3)',
            color: '#fff',
            minWidth: '400px'
          }
        }}
      >
        <DialogTitle sx={{ fontFamily: 'Orbitron', color: '#00f3ff' }}>
          {editingUser ? 'EDIT USER' : 'ADD NEW USER'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            {!editingUser && (
              <TextField
                label="Username"
                fullWidth
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                sx={textFieldStyle}
              />
            )}
            <TextField
              label={editingUser ? "New Password (leave empty to keep current)" : "Password"}
              type="password"
              fullWidth
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              sx={textFieldStyle}
            />
            <TextField
              select
              label="Role"
              fullWidth
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              sx={textFieldStyle}
            >
              {ROLES.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={handleCloseModal} sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>CANCEL</Button>
          <Button 
            variant="contained" 
            onClick={handleSubmit}
            sx={{
              backgroundColor: '#00f3ff',
              color: '#000',
              fontWeight: 'bold',
              '&:hover': { backgroundColor: '#00d0db' }
            }}
          >
            {editingUser ? 'UPDATE' : 'CREATE'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
