import React, { useState } from 'react';
import { 
  Box, 
  Drawer, 
  AppBar, 
  Toolbar, 
  List, 
  Typography, 
  Divider, 
  IconButton, 
  ListItem, 
  ListItemButton, 
  ListItemIcon, 
  ListItemText,
  Avatar,
  Menu,
  MenuItem,
  Tooltip,
  InputBase,
  Collapse,
  Button,
  Chip
} from '@mui/material';

import { 
  Home,
  Folder,
  Target, 
  Monitor,
  Activity,
  ShieldAlert,
  CheckSquare,
  Briefcase,
  Cpu,
  Command,
  Settings,
  Bell, 
  Search, 
  ChevronRight, 
  ChevronDown,
  LayoutGrid,
  Sliders,
  Clock,
  Globe,
  Plus,
  LogOut,
  User as UserIcon
} from 'lucide-react';
import { useTheme } from '@mui/material/styles';
import { Link, useRouterState, useParams } from '@tanstack/react-router';
import { useAppContext } from '../../context/AppContext';

const drawerWidth = 260;
const collapsedWidth = 72;

interface NavItem {
  title: string;
  icon: React.ReactNode;
  path: string;
  color?: string;
  children?: { title: string; path: string }[];
}

export const Shell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const theme = useTheme();
  const { version, projectName } = useAppContext();
  const [isHovered, setIsHovered] = useState(false);
  const [openItems, setOpenItems] = useState<string[]>([]);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const { projectSlug = 'default' } = useParams({ strict: false }) as any;

  const navItems: NavItem[] = [
    { title: 'Dashboard', icon: <Home size={20} />, path: `/${projectSlug}/dashboard`, color: '#7000ff' },
    { title: 'Projects', icon: <Folder size={20} />, path: `/${projectSlug}/projects`, color: '#00f3ff' },


    { title: 'Targets', icon: <Target size={20} />, path: `/${projectSlug}/targets`, color: '#00f3ff' },
    { title: 'Monitoring', icon: <Monitor size={20} />, path: `/${projectSlug}/monitoring`, color: '#00f3ff' },
    { 
      title: 'Scan History', 
      icon: <Activity size={20} />, 
      path: `/${projectSlug}/scans`, 
      color: '#00f3ff',
      children: [
        { title: 'Scan History', path: `/${projectSlug}/scans` },
        { title: 'Sub Scan History', path: `/${projectSlug}/scans/sub` },
        { title: 'Scheduled Scan', path: `/${projectSlug}/scans/scheduled` },
        { title: 'All Subdomains', path: `/${projectSlug}/subdomains` },
        { title: 'All Endpoints', path: `/${projectSlug}/endpoints` },
      ]
    },
    { title: 'Vulnerabilities', icon: <ShieldAlert size={20} />, path: `/${projectSlug}/vulns`, color: '#00f3ff' },
    { title: 'Todo', icon: <CheckSquare size={20} />, path: `/${projectSlug}/todo`, color: '#00f3ff' },
    { title: 'Organization', icon: <Briefcase size={20} />, path: `/${projectSlug}/org`, color: '#00f3ff' },
    { title: 'Scan Engine', icon: <Cpu size={20} />, path: `/${projectSlug}/engines`, color: '#00f3ff' },
    { title: 'Bounty Hub', icon: <Command size={20} />, path: `/${projectSlug}/bounty`, color: '#00f3ff' },
    { 
      title: 'Settings', 
      icon: <Settings size={20} />, 
      path: `/${projectSlug}/settings`, 
      color: '#00f3ff',
      children: [
        { title: 'Proxies', path: `/${projectSlug}/settings/proxies` },
        { title: 'OpSec Settings', path: `/${projectSlug}/settings/opsec` },
        { title: 'Tool Settings', path: `/${projectSlug}/settings/tool-settings` },
        { title: 'API Vault', path: `/${projectSlug}/settings/api-vault` },
        { title: 'LLM Toolkit', path: `/${projectSlug}/settings/llm-toolkit` },
        { title: 'Tools Arsenal', path: `/${projectSlug}/settings/tools-arsenal` },
        { title: 'Report Settings', path: `/${projectSlug}/settings/report-settings` },
        { title: 'reNgine Settings', path: `/${projectSlug}/settings/rengine-settings` },
        { title: 'Notification Settings', path: `/${projectSlug}/settings/notifications` },
      ]
    },
  ];

  const handleToggle = (title: string) => {
    setOpenItems(prev => 
      prev.includes(title) ? prev.filter(i => i !== title) : [...prev, title]
    );
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => setAnchorEl(event.currentTarget);
  const handleMenuClose = () => setAnchorEl(null);

  const routerState = useRouterState();
  const activePath = routerState.location.pathname;

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: '#05050a' }}>
      {/* Sidebar - Mini Drawer Style */}
      <Drawer
        variant="permanent"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        sx={{
          width: isHovered ? drawerWidth : collapsedWidth,
          flexShrink: 0,
          whiteSpace: 'nowrap',
          transition: theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
          '& .MuiDrawer-paper': {
            width: isHovered ? drawerWidth : collapsedWidth,
            transition: theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
            overflowX: 'hidden',
            boxSizing: 'border-box',
            borderRight: 'none',
            bgcolor: 'rgba(10, 10, 20, 0.8)',
            backdropFilter: 'blur(10px)',
            backgroundImage: 'none',
            borderRadius: '0 30px 30px 0',
            height: 'fit-content',
            top: '50%',
            transform: 'translateY(-50%)',
            border: '1px solid rgba(0, 243, 255, 0.1)',
            boxShadow: '0 0 30px rgba(0,0,0,0.5)',
            py: 2
          },
        }}
      >
        <List sx={{ px: 1, mt: 2 }}>
          {navItems.map((item) => {
            const hasChildren = item.children && item.children.length > 0;
            const isOpen = openItems.includes(item.title);
            const isActive = activePath.startsWith(item.path);
            const itemColor = isActive ? '#7000ff' : '#00f3ff';
            
            return (
              <React.Fragment key={item.title}>
                <ListItem disablePadding sx={{ mb: 0.5 }}>
                  <ListItemButton 
                    {...(hasChildren ? {
                      onClick: () => handleToggle(item.title)
                    } : {
                      component: Link,
                      to: item.path
                    })}
                    sx={{ 
                      borderRadius: 2,
                      minHeight: 48,
                      justifyContent: isHovered ? 'initial' : 'center',
                      px: 2.5,
                      bgcolor: isActive ? 'rgba(112, 0, 255, 0.15)' : 'transparent',
                      '&:hover': { 
                        bgcolor: isActive ? 'rgba(112, 0, 255, 0.2)' : 'rgba(0, 243, 255, 0.05)',
                      }
                    }}
                  >
                    <ListItemIcon sx={{ 
                      minWidth: 0, 
                      mr: isHovered ? 2 : 'auto', 
                      justifyContent: 'center',
                      color: itemColor,
                      filter: `drop-shadow(0 0 5px ${itemColor}aa)`
                    }}>
                      {item.icon}
                    </ListItemIcon>
                    
                    {isHovered && (
                      <>
                        <ListItemText 
                          primary={
                            <Typography variant="body2" sx={{ 
                              fontWeight: 600, 
                              color: isActive ? '#7000ff' : 'rgba(255,255,255,0.6)',
                              fontSize: '0.85rem'
                            }}>
                              {item.title}
                            </Typography>
                          } 
                        />
                        {hasChildren && (
                          isOpen ? <ChevronDown size={14} style={{ opacity: 0.5 }} /> : <ChevronRight size={14} style={{ opacity: 0.5 }} />
                        )}
                      </>
                    )}
                  </ListItemButton>
                </ListItem>
                
                {hasChildren && isHovered && (
                  <Collapse in={isOpen} timeout="auto" unmountOnExit>
                    <List component="div" disablePadding sx={{ ml: 2 }}>
                      {item.children?.map((child) => {
                        const isChildActive = activePath === child.path;
                        return (
                          <ListItemButton
                            key={child.title}
                            component={Link}
                            to={child.path}
                            sx={{
                              py: 0.5,
                              borderRadius: 1,
                              mb: 0.2,
                              bgcolor: isChildActive ? 'rgba(112, 0, 255, 0.1)' : 'transparent',
                              '&:hover': {
                                bgcolor: 'rgba(0, 243, 255, 0.05)',
                              }
                            }}
                          >
                            <ListItemText
                              primary={
                                <Typography variant="caption" sx={{
                                  fontWeight: isChildActive ? 700 : 500,
                                  color: isChildActive ? '#7000ff' : 'rgba(255,255,255,0.4)',
                                  fontSize: '0.75rem',
                                  letterSpacing: 0.5
                                }}>
                                  {child.title}
                                </Typography>
                              }
                            />
                          </ListItemButton>
                        );
                      })}
                    </List>
                  </Collapse>
                )}
              </React.Fragment>
            );
          })}
        </List>
      </Drawer>

      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Floating Topbar */}
        <AppBar position="fixed" sx={{ 
          bgcolor: 'rgba(10, 10, 15, 0.95)', 
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          borderRadius: 4,
          mt: 1.5,
          mx: 2,
          width: 'calc(100% - 32px)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          backgroundImage: 'none',
          zIndex: theme.zIndex.drawer + 1
        }}>
          <Toolbar sx={{ px: '16px !important', minHeight: '64px !important' }}>
            {/* Logo Section */}
            <Box sx={{ display: 'flex', alignItems: 'center', mr: 4 }}>
              <Typography variant="h6" sx={{ 
                fontWeight: 900, 
                fontFamily: 'Orbitron', 
                letterSpacing: 2,
                color: '#ff00ff',
                textShadow: '0 0 12px rgba(255, 0, 115, 0.8)',
                fontSize: '1.4rem',
                mr: 1.5,
                textTransform: 'lowercase'
              }}>
                r3ngine
              </Typography>
              <Chip 
                label={version} 
                size="small" 
                sx={{ 
                  height: 18, 
                  fontSize: '0.6rem', 
                  fontWeight: 800, 
                  bgcolor: 'transparent', 
                  border: '1px solid #ff00ff', 
                  color: '#ff00ff',
                  borderRadius: 1
                }} 
              />
            </Box>

            {/* Universal Search */}
            <Box sx={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                bgcolor: 'rgba(255, 255, 255, 0.03)', 
                px: 2, 
                py: 0.5, 
                borderRadius: 10,
                width: '100%',
                maxWidth: 320,
                border: '1px solid rgba(255,255,255,0.05)',
                '&:hover': { borderColor: 'rgba(0, 243, 255, 0.3)' }
              }}>
                <InputBase 
                  placeholder="Universal Search..." 
                  sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', flex: 1, ml: 1 }}
                />
                <Search size={14} style={{ color: '#ff00ff', opacity: 0.8 }} />
              </Box>
            </Box>

            {/* Action Group */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box 
                component={Link} 
                to={`/${projectSlug}/projects`}
                sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer', gap: 0.5, textDecoration: 'none' }}
              >
                <Typography variant="body2" sx={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.6)' }}>Projects</Typography>
                <ChevronDown size={14} style={{ opacity: 0.5, color: 'rgba(255,255,255,0.6)' }} />
              </Box>


              <Box sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer', gap: 0.5 }}>
                <Plus size={14} style={{ opacity: 0.6 }} />
                <Typography variant="body2" sx={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.6)' }}>Quick Add</Typography>
                <ChevronDown size={14} style={{ opacity: 0.5 }} />
              </Box>

              <Box sx={{ display: 'flex', gap: 1.5, mx: 2 }}>
                <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.5)' }}><LayoutGrid size={18} /></IconButton>
                <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.5)' }}><Sliders size={18} /></IconButton>
                <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.5)' }}><Bell size={18} /></IconButton>
                <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.5)' }}><Activity size={18} /></IconButton>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer', ml: 1 }} onClick={handleMenuOpen}>
                <Avatar 
                  sx={{ 
                    width: 32, 
                    height: 32, 
                    bgcolor: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(0, 243, 255, 0.3)',
                    p: 0.2
                  }}
                >
                  <img src="https://img.icons8.com/color/48/000000/hacker.png" width="24" alt="avatar" />
                </Avatar>
                <Box sx={{ ml: 1, display: 'flex', alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8rem', color: 'rgba(255,255,255,0.7)' }}>root</Typography>
                  <ChevronDown size={14} style={{ opacity: 0.4, marginLeft: 4 }} />
                </Box>
              </Box>
            </Box>
          </Toolbar>
        </AppBar>

        {/* Page Content */}
        <Box 
          component="main" 
          sx={{ 
            flexGrow: 1, 
            pt: 12,
            px: 3,
            pb: 4,
            overflow: 'auto',
            position: 'relative',
            background: `linear-gradient(rgba(5, 5, 10, 0.85), rgba(5, 5, 10, 0.85)), url("/staticfiles/img/neon_city.png") no-repeat center center fixed`,
            backgroundSize: 'cover',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
              opacity: 0.05,
              pointerEvents: 'none',
              zIndex: 0
            }
          }}
        >
          <Box sx={{ position: 'relative', zIndex: 1 }}>
            {children}
          </Box>
        </Box>
      </Box>
    </Box>
  );
};
