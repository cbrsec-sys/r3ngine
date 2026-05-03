import React from 'react';
import {
  Box,
  Typography,
  Menu,
  IconButton,
  Stack,
  Button,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  CircularProgress
} from '@mui/material';
import { Bell, Check, Trash2, Info, AlertCircle, XCircle, BellOff } from 'lucide-react';
// import { formatDistanceToNow } from 'date-fns';
import { useNotifications, useUnreadCount, useMarkAllRead, useClearAll, useMarkRead } from '../api';

interface NotificationsDropdownProps {
  anchorEl: HTMLElement | null;
  onClose: () => void;
  projectSlug?: string;
}

export const NotificationsDropdown: React.FC<NotificationsDropdownProps> = ({
  anchorEl,
  onClose,
  projectSlug
}) => {
  const { data: notifications, isLoading } = useNotifications(projectSlug);
  const markAllRead = useMarkAllRead();
  const clearAll = useClearAll();
  const markRead = useMarkRead();

  const open = Boolean(anchorEl);

  const getIcon = (type: string) => {
    switch (type) {
      case 'info': return <Info size={16} color="#00f3ff" />;
      case 'warning': return <AlertCircle size={16} color="#fffc00" />;
      case 'error': return <XCircle size={16} color="#ff003c" />;
      default: return <Bell size={16} color="rgba(255,255,255,0.5)" />;
    }
  };

  return (
    <Menu
      anchorEl={anchorEl}
      open={open}
      onClose={onClose}
      disableScrollLock
      paperprops={{
        sx: {
          width: 360,
          maxHeight: 500,
          bgcolor: 'rgba(10, 10, 15, 0.95)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(0, 243, 255, 0.2)',
          borderRadius: 2,
          backgroundImage: 'none',
          mt: 1.5,
          '& .MuiList-root': { p: 0 }
        }
      }}
    >
      <Box sx={{ p: 2, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 900, fontSize: '0.75rem', letterSpacing: 1, color: '#00f3ff' }}>
            NOTIFICATIONS
          </Typography>
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              onClick={() => markAllRead.mutate(projectSlug)}
              sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.6)', '&:hover': { color: '#00f3ff' } }}
            >
              Mark all read
            </Button>
            <Button
              size="small"
              onClick={() => clearAll.mutate(projectSlug)}
              sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.6)', '&:hover': { color: '#ff003c' } }}
            >
              Clear All
            </Button>
          </Stack>
        </Stack>
      </Box>

      <List sx={{ maxHeight: 400, overflow: 'auto' }}>
        {isLoading ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <CircularProgress size={20} sx={{ color: '#00f3ff' }} />
          </Box>
        ) : (Array.isArray(notifications) && notifications.length > 0) ? (
          notifications.map((notif: any) => (
            <ListItem
              key={notif.id}
              onClick={() => markRead.mutate(notif.id)}
              sx={{
                borderBottom: '1px solid rgba(255,255,255,0.03)',
                cursor: 'pointer',
                bgcolor: notif.is_read ? 'transparent' : 'rgba(0, 243, 255, 0.03)',
                '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' },
                transition: 'all 0.2s'
              }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>
                {getIcon(notif.notification_type)}
              </ListItemIcon>
              <ListItemText
                primary={notif.title}
                secondary={
                  <Stack spacing={0.5} sx={{ mt: 0.5 }}>
                    <Typography sx={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.7)' }}>
                      {notif.description}
                    </Typography>
                    <Typography sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
                      {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </Typography>
                  </Stack>
                }
                primaryTypographyProps={{
                  sx: {
                    fontSize: '0.8rem',
                    fontWeight: notif.is_read ? 500 : 900,
                    color: notif.is_read ? 'rgba(255,255,255,0.8)' : '#fff'
                  }
                }}
              />
            </ListItem>
          ))
        ) : (
          <Box sx={{ p: 4, textAlign: 'center', opacity: 0.5 }}>
            <BellOff size={32} style={{ marginBottom: 8, color: 'rgba(255,255,255,0.2)' }} />
            <Typography sx={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>
              Ping? Pong! No notifications, moving along
            </Typography>
          </Box>
        )}
      </List>
    </Menu>
  );
};
