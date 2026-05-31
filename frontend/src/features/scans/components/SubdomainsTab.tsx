import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Box,
  Typography,
  Grid,
  InputBase,
  Button,
  IconButton,
  Tooltip,
  CircularProgress,
  Pagination,
  Stack,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  FormControlLabel,
  InputLabel,
  Select,
  Checkbox,
  TextField,
  List,
  ListItem,
  ListItemButton,
  FormGroup,
  Divider,
  Alert,
  Snackbar,
  Modal,
  Fade,
  Backdrop
} from '@mui/material';
import {
  Search,
  Zap,
  Eye,
  FilePlus,
  MoreHorizontal,
  Download,
  ChevronRight,
  ExternalLink,
  AlertTriangle,
  Trash2,
  Copy,
  FileText,
  Shield,
  Network,
  X,
  Folder
} from 'lucide-react';
import { getCsrfToken } from '../../../api/axiosConfig';


import { 
  useSubdomains, 
  useDeleteSubdomain, 
  useToggleSubdomainImportant, 
  useInitiateSubscan,
  useGPTAttackSurface
} from '../../subdomains/api';
import { useEngines } from '../../engines/api';
import { useCreateTodo } from '../../todos/api';
import { TacticalPanel } from '../../../components/TacticalPanel';
import { ConfirmDialog } from '../../../components/ConfirmDialog';

interface SubdomainsTabProps {
  projectSlug: string;
  scanId?: number;
  targetId?: number;
  onTabChange?: (index: number) => void;
}

const TASK_TIER_ORDER: string[] = [
  // Tier 1 — Discovery
  'subdomain_discovery', 'amass_intel_discovery', 'firewall_vpn_scan',
  'dns_security', 'osint', 'spiderfoot_scan', 'baddns',
  // Tier 2 — HTTP Crawl & Port Scan
  'http_crawl', 'port_scan', 'vigolium_discovery',
  // Tier 3 — Fetching & Screenshot
  'fetch_url', 'screenshot',
  // Tier 4 — Fuzzing
  'dir_file_fuzz',
  // Tier 5 — Analysis
  'web_api_discovery', 'waf_detection', 'secret_scanning', 'vigolium_analysis',
  // Tier 6 — Security Assessment
  'vulnerability_scan', 'waf_bypass', 'brute_force_scan', 'vigolium_scan',
];

export const SubdomainsTab: React.FC<SubdomainsTabProps> = ({ projectSlug, scanId, targetId, onTabChange }) => {

  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSearch, setActiveSearch] = useState('');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedAssets, setSelectedAssets] = useState<number[]>([]);

  const { data, isLoading } = useSubdomains(projectSlug, page, activeSearch, scanId, false, targetId);
  const [isReady, setIsReady] = useState(false);
  
  // Modals state
  const [subscanModalOpen, setSubscanModalOpen] = useState(false);
  const [attackSurfaceModalOpen, setAttackSurfaceModalOpen] = useState(false);
  const [todoModalOpen, setTodoModalOpen] = useState(false);
  
  // Selected subdomain for single actions
  const [targetSubdomain, setTargetSubdomain] = useState<any>(null);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [lightboxLabel, setLightboxLabel] = useState<string>('');
  
  const openLightbox = (src: string, label: string = '') => {
    setLightboxSrc(src);
    setLightboxLabel(label);
  };
  const closeLightbox = () => {
    setLightboxSrc(null);
    setLightboxLabel('');
  };
  
  // Confirmation state
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmConfig, setConfirmConfig] = useState<{
    title: string;
    message: string;
    onConfirm: () => void;
    type?: 'danger' | 'info' | 'warning';
  }>({
    title: '',
    message: '',
    onConfirm: () => {},
  });
  
  // Subscan state
  const [selectedEngineId, setSelectedEngineId] = useState<number | null>(null);
  const [selectedTasks, setSelectedTasks] = useState<string[]>([]);
  
  // TODO state
  const [todoTitle, setTodoTitle] = useState('');
  const [todoDescription, setTodoDescription] = useState('');
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  // AD Assessment state
  const [adLaunchMsg, setAdLaunchMsg] = useState<{ text: string; severity: 'success' | 'error' } | null>(null);

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const showNotification = (message: string, severity: 'success' | 'error' | 'info' | 'warning' = 'success') => {
    setSnackbar({
      open: true,
      message,
      severity,
    });
  };

  // Mutations
  const deleteMutation = useDeleteSubdomain(projectSlug);
  const importantMutation = useToggleSubdomainImportant(projectSlug);
  const subscanMutation = useInitiateSubscan();
  const attackSurfaceMutation = useGPTAttackSurface();
  const createTodoMutation = useCreateTodo();
  const { data: enginesData } = useEngines();

  React.useEffect(() => {
    if (!isLoading && data) {
      const timer = setTimeout(() => setIsReady(true), 100);
      return () => clearTimeout(timer);
    } else {
      setIsReady(false);
    }
  }, [isLoading, data]);

  const toggleSelectAll = () => {
    if (selectedAssets.length === data?.results.length) {
      setSelectedAssets([]);
    } else {
      setSelectedAssets(data?.results.map(s => s.id) || []);
    }
  };

  const toggleSelectAsset = (id: number) => {
    setSelectedAssets(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleSearch = () => {
    setPage(1);
    setActiveSearch(searchQuery);
  };

  const handleActionClick = (event: React.MouseEvent<HTMLButtonElement>, sub: any) => {
    setAnchorEl(event.currentTarget);
    setSelectedId(sub.id);
    setTargetSubdomain(sub);
  };

  const handleActionClose = () => {
    setAnchorEl(null);
    setSelectedId(null);
    // We keep targetSubdomain until a new one is selected or modal closes
  };

  const handleDelete = async (id: number) => {
    setConfirmConfig({
      title: 'DELETE ASSET',
      message: 'Are you sure you want to delete this subdomain? This action cannot be undone.',
      type: 'danger',
      onConfirm: async () => {
        try {
          await deleteMutation.mutateAsync([id]);
          showNotification('Subdomain deleted successfully');
        } catch (error: any) {
          showNotification(error.message || 'Failed to delete subdomain', 'error');
        }
        handleActionClose();
      }
    });
    setConfirmOpen(true);
  };

  const handleBulkDelete = async () => {
    if (selectedAssets.length === 0) return;
    setConfirmConfig({
      title: 'BULK DELETE ASSETS',
      message: `Are you sure you want to delete ${selectedAssets.length} subdomains? This operation is permanent.`,
      type: 'danger',
      onConfirm: async () => {
        try {
          await deleteMutation.mutateAsync(selectedAssets);
          showNotification(`${selectedAssets.length} subdomains deleted`);
          setSelectedAssets([]);
        } catch (error: any) {
          showNotification(error.message || 'Failed to delete subdomains', 'error');
        }
      }
    });
    setConfirmOpen(true);
  };

  const handleToggleImportant = async (id: number) => {
    try {
      await importantMutation.mutateAsync(id);
      showNotification('Status updated');
    } catch (error: any) {
      showNotification(error.message || 'Failed to update status', 'error');
    }
    handleActionClose();
  };

  const handleLaunchADAssessment = async () => {
    handleActionClose();
    if (!selectedId) return;
    try {
      const res = await fetch('/api/action/ad-assessment/from-subdomain/', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() ?? '' },
        body: JSON.stringify({ subdomain_id: selectedId }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? `HTTP ${res.status}`);
      setAdLaunchMsg({
        text: `AD Assessment created for ${json.target_domain}. Open the AD Intelligence plugin to start it.`,
        severity: 'success',
      });
    } catch (err: unknown) {
      setAdLaunchMsg({
        text: (err instanceof Error ? err.message : 'Failed to create AD assessment'),
        severity: 'error',
      });
    }
  };

  const handleInitiateSubscan = async () => {
    if (!selectedEngineId) {
      showNotification('Please select an engine', 'error');
      return;
    }
    if (selectedTasks.length === 0) {
      showNotification('Please select at least one task', 'error');
      return;
    }

    const subdomain_ids = selectedAssets.length > 0 
      ? selectedAssets 
      : targetSubdomain ? [targetSubdomain.id] : [];

    if (subdomain_ids.length === 0) {
      showNotification('No subdomains selected', 'error');
      return;
    }

    try {
      await subscanMutation.mutateAsync({
        engine_id: selectedEngineId,
        tasks: selectedTasks,
        subdomain_ids
      });
      showNotification('Subscan initiated successfully');
      setSubscanModalOpen(false);
      setSelectedEngineId(null);
      setSelectedTasks([]);
    } catch (error: any) {
      showNotification(error.message || 'Failed to initiate subscan', 'error');
    }
  };

  const selectedEngine = enginesData?.find(e => e.id === selectedEngineId);

  const handleAddTodo = async () => {
    if (!todoDescription) {
      showNotification('Please enter a description', 'error');
      return;
    }
    try {
      await createTodoMutation.mutateAsync({
        title: todoTitle || `TODO: ${targetSubdomain.name}`,
        description: todoDescription,
        subdomain_id: targetSubdomain.id,
        project: projectSlug || ""
      });
      setTodoModalOpen(false);
      setTodoDescription('');
      showNotification('TODO note added successfully');
    } catch (error: any) {
      showNotification(error.message || 'Failed to add TODO note', 'error');
    }
  };

  const handleShowAttackSurface = async (sub: any) => {
    setTargetSubdomain(sub);
    setAttackSurfaceModalOpen(true);
    try {
      await attackSurfaceMutation.mutateAsync(sub.id);
    } catch (error: any) {
      showNotification(error.message || 'Failed to fetch attack surface', 'error');
    }
  };

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return '#00ffaa';
    if (status >= 300 && status < 400) return '#00f3ff';
    if (status >= 400 && status < 500) return '#ffae00';
    if (status >= 500) return '#ff003c';
    return '#888';
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Tactical Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 4, mt: 2 }}>
        <Box>
          <Typography variant="h5" sx={{
            fontWeight: 900,
            fontFamily: 'Orbitron',
            letterSpacing: 3,
            color: '#fff',
            textTransform: 'uppercase'
          }}>
            Subdomain Inventory
          </Typography>
          <Typography sx={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', mt: 0.5, letterSpacing: 1 }}>
            V3.0 SCAN ASSETS RECON ACTIVE
          </Typography>
        </Box>
      </Box>

      {/* Enterprise-Grade Search Bar */}
      <Box sx={{
        display: 'flex',
        bgcolor: 'rgba(255,255,255,0.03)',
        borderRadius: '4px',
        overflow: 'hidden',
        mb: 3,
        border: '1px solid rgba(0, 243, 255, 0.1)',
        '&:focus-within': {
          borderColor: 'rgba(0, 243, 255, 0.4)',
          boxShadow: '0 0 15px rgba(0, 243, 255, 0.1)'
        },
        transition: 'all 0.2s'
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', pl: 2, color: 'rgba(255,255,255,0.3)' }}>
          <Search size={18} />
        </Box>
        <InputBase
          placeholder="Filter Subdomains (e.g. name=google.com, http_status=200)"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          sx={{
            flex: 1,
            px: 2,
            py: 1,
            fontSize: '0.9rem',
            color: '#fff',
            '&::placeholder': { color: 'rgba(255,255,255,0.2)', opacity: 1 }
          }}
        />
        <Button
          onClick={handleSearch}
          sx={{
            bgcolor: 'rgba(0, 243, 255, 0.1)',
            color: '#00f3ff',
            px: 4,
            borderRadius: 0,
            fontWeight: 700,
            fontSize: '11px',
            letterSpacing: 1,
            borderLeft: '1px solid rgba(0, 243, 255, 0.1)',
            '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)' }
          }}
        >
          SEARCH
        </Button>
      </Box>

      {/* Tactical Panel */}
      <TacticalPanel>
        {/* Tactical Table Header (Legacy Parity) */}
        <Box sx={{
          p: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          bgcolor: 'rgba(255,255,255,0.01)'
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography sx={{ fontSize: '11px', fontWeight: 600, color: 'rgba(255,255,255,0.5)' }}>Results :</Typography>
              <Box sx={{ px: 1, py: 0.5, bgcolor: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 1 }}>
                <Typography sx={{ fontSize: '11px', color: '#fff', fontWeight: 700 }}>50</Typography>
              </Box>
            </Box>
            <Box sx={{ px: 3, py: 0.8, bgcolor: 'rgba(255,255,255,0.03)', borderRadius: 1, border: '1px solid rgba(255,255,255,0.1)' }}>
              <Typography sx={{ fontSize: '11px', fontWeight: 700, color: 'rgba(255,255,255,0.7)', letterSpacing: 0.5 }}>
                Showing page {page} of {Math.ceil((data?.count || 0) / 50) || 1}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {selectedAssets.length > 0 && (
              <Stack direction="row" spacing={1}>
                <Button 
                  size="small" 
                  variant="contained" 
                  onClick={() => setSubscanModalOpen(true)}
                  sx={{ 
                    bgcolor: 'rgba(0, 243, 255, 0.1)', 
                    color: '#00f3ff', 
                    fontSize: '10px', 
                    fontWeight: 800, 
                    border: '1px solid rgba(0, 243, 255, 0.2)',
                    '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)' } 
                  }}
                >
                  SUBSCAN SELECTED ({selectedAssets.length})
                </Button>
                <Button 
                  size="small" 
                  variant="contained" 
                  onClick={handleBulkDelete}
                  sx={{ 
                    bgcolor: 'rgba(255, 0, 60, 0.1)', 
                    color: '#ff003c', 
                    fontSize: '10px', 
                    fontWeight: 800, 
                    border: '1px solid rgba(255, 0, 60, 0.2)',
                    '&:hover': { bgcolor: 'rgba(255, 0, 60, 0.2)' } 
                  }}
                >
                  DELETE SELECTED ({selectedAssets.length})
                </Button>
              </Stack>
            )}
            <IconButton size="small" sx={{ color: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.05)', border: '1px solid rgba(0, 243, 255, 0.1)', borderRadius: 1 }}>
              <Download size={14} />
            </IconButton>
          </Box>
        </Box>

        {/* Responsive Subdomains Table */}
        <Box sx={{
          overflowX: 'auto',
          width: '100%',
          '&::-webkit-scrollbar': { height: '6px' },
          '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(0, 243, 255, 0.2)', borderRadius: '3px' }
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'auto' }}>
            <thead>
              <tr style={{
                textAlign: 'left',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                backgroundColor: 'rgba(255,255,255,0.02)'
              }}>
                <th style={{ width: '40px', padding: '12px 16px', textAlign: 'center' }}>
                  <input
                    type="checkbox"
                    checked={selectedAssets.length === data?.results.length && data?.results.length > 0}
                    onChange={toggleSelectAll}
                    style={{ width: '14px', height: '14px', accentColor: '#00f3ff', cursor: 'pointer', opacity: 0.6 }}
                  />
                </th>
                <th style={{ padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>SUBDOMAIN</th>
                <Box component="th" sx={{ display: { xs: 'none', sm: 'table-cell' }, padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>STATUS</Box>
                <Box component="th" sx={{ display: { xs: 'none', md: 'table-cell' }, padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>IP</Box>
                <Box component="th" sx={{ display: { xs: 'none', lg: 'table-cell' }, padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>PORTS</Box>
                <Box component="th" sx={{ display: { xs: 'none', xl: 'table-cell' }, padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>CONTENT</Box>
                <Box component="th" sx={{ display: { xs: 'none', lg: 'table-cell' }, padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>TIME</Box>
                <Box component="th" sx={{ display: { xs: 'none', md: 'table-cell' }, padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron' }}>SCREENSHOT</Box>
                <th style={{ padding: '12px 16px', color: '#00f3ff', fontSize: '10px', fontWeight: 900, letterSpacing: 1.5, fontFamily: 'Orbitron', textAlign: 'right' }}>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={9} style={{ padding: '80px', textAlign: 'center' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                      <CircularProgress size={32} sx={{ color: '#00f3ff', filter: 'drop-shadow(0 0 8px #00f3ff)' }} />
                      <Typography sx={{
                        fontSize: '10px',
                        fontWeight: 900,
                        color: 'rgba(0, 243, 255, 0.5)',
                        fontFamily: 'Orbitron',
                        letterSpacing: 2,
                        textTransform: 'uppercase'
                      }}>
                        System Fetching Subdomains...
                      </Typography>
                    </Box>
                  </td>
                </tr>
              ) : data?.results.map((sub) => (
                <tr key={sub.id} style={{
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  backgroundColor: selectedAssets.includes(sub.id) ? 'rgba(0, 243, 255, 0.02)' : (sub.is_important ? 'rgba(255, 0, 60, 0.03)' : 'transparent'),
                  transition: 'background 0.2s'
                }}>
                  <td style={{ padding: '12px 16px', verticalAlign: 'middle', textAlign: 'center' }}>
                    <input
                      type="checkbox"
                      checked={selectedAssets.includes(sub.id)}
                      onChange={() => toggleSelectAsset(sub.id)}
                      style={{
                        width: '14px',
                        height: '14px',
                        accentColor: '#00f3ff',
                        cursor: 'pointer',
                        opacity: 0.6
                      }}
                    />
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography sx={{ fontSize: '13px', fontWeight: 700, color: '#fff', letterSpacing: 0.2 }}>{sub.name}</Typography>
                        {sub.is_important && <Shield size={12} color="#ffae00" style={{ filter: 'drop-shadow(0 0 5px #ffae00)' }} />}
                        <IconButton 
                          size="small" 
                          onClick={() => {
                            navigator.clipboard.writeText(sub.name);
                            showNotification('Copied to clipboard');
                          }}
                          sx={{ p: 0.2, color: 'rgba(255,255,255,0.3)', '&:hover': { color: '#00f3ff' } }}
                        >
                          <Copy size={12} />
                        </IconButton>
                      </Box>

                      {/* Asset Intelligence Badges (Legacy Feature) */}
                      <Box sx={{ display: 'flex', gap: 1.5, mt: 0.5 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Tooltip title="Subscans">
                            <Typography sx={{ fontSize: '9px', fontWeight: 800, color: 'rgba(255,255,255,0.4)', display: 'flex', alignItems: 'center', gap: 0.5, cursor: 'help' }}>
                              <Zap size={10} style={{ color: '#00f3ff' }} /> {sub.subscan_count || 0}
                            </Typography>
                          </Tooltip>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Tooltip title="Endpoints">
                            <Typography sx={{ fontSize: '9px', fontWeight: 800, color: 'rgba(255,255,255,0.4)', display: 'flex', alignItems: 'center', gap: 0.5, cursor: 'help' }}>
                              <ExternalLink size={10} style={{ color: '#7000ff' }} /> {sub.endpoint_count || 0}
                            </Typography>
                          </Tooltip>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Tooltip title="Critical Vulnerabilities">
                            <Typography sx={{ fontSize: '9px', fontWeight: 800, color: 'rgba(255,255,255,0.4)', display: 'flex', alignItems: 'center', gap: 0.5, cursor: 'help' }}>
                              <AlertTriangle size={10} style={{ color: '#ff003c' }} /> {sub.critical_count || 0}
                            </Typography>
                          </Tooltip>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Tooltip title="Directories Discovered">
                            <Typography sx={{ fontSize: '9px', fontWeight: 800, color: 'rgba(255,255,255,0.4)', display: 'flex', alignItems: 'center', gap: 0.5, cursor: 'help' }}>
                              <Folder size={10} style={{ color: '#fffc00' }} /> {sub.directories_count || 0}
                            </Typography>
                          </Tooltip>
                        </Box>

                        {sub.info_count > 0 && (
                          <Chip label={`${sub.info_count} Info`} size="small" sx={{ height: 14, fontSize: '7px', fontWeight: 900, bgcolor: 'rgba(0, 243, 255, 0.1)', color: '#00f3ff', borderRadius: 0.5 }} />
                        )}
                      </Box>
                    </Box>
                  </td>
                  <Box component="td" sx={{ display: { xs: 'none', sm: 'table-cell' }, padding: '12px 16px' }}>
                    <Box sx={{
                      display: 'inline-flex',
                      px: 1.2,
                      py: 0.4,
                      borderRadius: 0.5,
                      bgcolor: `${getStatusColor(sub.http_status)}20`,
                      border: `1px solid ${getStatusColor(sub.http_status)}40`,
                    }}>
                      <Typography sx={{ fontSize: '11px', fontWeight: 900, color: getStatusColor(sub.http_status) }}>
                        {sub.http_status || '404'}
                      </Typography>
                    </Box>
                  </Box>
                  <Box component="td" sx={{ display: { xs: 'none', md: 'table-cell' }, padding: '12px 16px' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      {sub.ip_addresses?.map(ip => (
                        <Typography
                          key={`ip-${sub.id}-${ip.id}`}
                          sx={{
                            fontSize: '11px',
                            color: ip.is_cdn ? '#ffae00' : 'rgba(255,255,255,0.5)',
                            fontFamily: 'monospace',
                            fontWeight: 600
                          }}
                        >
                          {ip.address}
                        </Typography>
                      ))}
                    </Box>
                  </Box>
                  <Box component="td" sx={{ display: { xs: 'none', lg: 'table-cell' }, padding: '12px 16px' }}>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {sub.ip_addresses?.flatMap(ip => ip.ports.map(port => ({ ...port, ipId: ip.id }))).map(port => (
                        <Box
                          key={`port-${sub.id}-${port.ipId}-${port.id}`}
                          sx={{
                            px: 1,
                            py: 0.2,
                            borderRadius: 0.5,
                            bgcolor: port.is_uncommon ? 'rgba(255, 0, 60, 0.1)' : 'rgba(255,255,255,0.05)',
                            border: `1px solid ${port.is_uncommon ? 'rgba(255, 0, 60, 0.2)' : 'rgba(255,255,255,0.1)'}`,
                          }}
                        >
                          <Typography sx={{ fontSize: '9px', fontWeight: 800, color: port.is_uncommon ? '#ff003c' : 'rgba(255,255,255,0.6)', fontFamily: 'monospace' }}>
                            {port.number}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                  <Box component="td" sx={{ display: { xs: 'none', xl: 'table-cell' }, padding: '12px 16px' }}>
                    <Typography sx={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
                      {sub.content_length ? `${(sub.content_length / 1024).toFixed(1)} KB` : '0 KB'}
                    </Typography>
                  </Box>
                  <Box component="td" sx={{ display: { xs: 'none', lg: 'table-cell' }, padding: '12px 16px' }}>
                    <Typography sx={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
                      {sub.response_time ? `${(sub.response_time * 1000).toFixed(0)}ms` : '-'}
                    </Typography>
                  </Box>
                  <Box component="td" sx={{ display: { xs: 'none', md: 'table-cell' }, padding: '12px 16px' }}>
                    {(() => {
                      const ssPath = sub.screenshot_path || sub.screenshots?.[0]?.screenshot_path || null;
                      return ssPath ? (
                        <Box
                          onClick={() => openLightbox(ssPath, sub.name)}
                          sx={{
                            width: 60,
                            height: 34,
                            borderRadius: 0.5,
                            overflow: 'hidden',
                            border: '1px solid rgba(255,255,255,0.1)',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            position: 'relative',
                            '&:hover': {
                              borderColor: '#00f3ff',
                              transform: 'scale(1.1)',
                              zIndex: 10,
                              boxShadow: '0 0 15px rgba(0, 243, 255, 0.3)'
                            }
                          }}
                        >
                          <img
                            src={`/media/${ssPath}`}
                            alt="preview"
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          />
                        </Box>
                      ) : (
                        <Typography sx={{ fontSize: '9px', color: 'rgba(255,255,255,0.15)', fontWeight: 800 }}>NO DATA</Typography>
                      );
                    })()}
                  </Box>
                  <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                    <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                      <Tooltip title="Show Attack Surface">
                        <IconButton 
                          size="small" 
                          onClick={() => handleShowAttackSurface(sub)}
                          sx={{ color: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.05)', p: 0.5 }}
                        >
                          <Eye size={14} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Further Scan Subdomain">
                        <IconButton 
                          size="small" 
                          onClick={() => {
                            setTargetSubdomain(sub);
                            setSubscanModalOpen(true);
                          }}
                          sx={{ color: '#00ffaa', bgcolor: 'rgba(0, 255, 170, 0.05)', p: 0.5 }}
                        >
                          <Zap size={14} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Add Recon TODO/Note">
                        <IconButton 
                          size="small" 
                          onClick={() => {
                            setTargetSubdomain(sub);
                            setTodoModalOpen(true);
                          }}
                          sx={{ color: '#ffae00', bgcolor: 'rgba(255, 174, 0, 0.05)', p: 0.5 }}
                        >
                          <FileText size={14} />
                        </IconButton>
                      </Tooltip>
                      <IconButton size="small" onClick={(e) => handleActionClick(e, sub)} sx={{ color: 'rgba(255,255,255,0.3)', p: 0.5 }}>
                        <MoreHorizontal size={14} />
                      </IconButton>
                    </Box>
                  </td>

                </tr>
              ))}
            </tbody>
          </table>
        </Box>

        {/* Tactical Pagination */}
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'center', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <Stack spacing={2}>
            <Pagination
              count={Math.ceil((data?.count || 0) / 50)}
              page={page}
              onChange={(_, v) => setPage(v)}
              size="small"
              sx={{
                '& .MuiPaginationItem-root': {
                  color: 'rgba(255,255,255,0.5)',
                  borderColor: 'rgba(255,255,255,0.1)',
                  fontFamily: 'Orbitron',
                  fontSize: '10px',
                  '&.Mui-selected': {
                    bgcolor: 'rgba(0, 243, 255, 0.1)',
                    color: '#00f3ff',
                    borderColor: '#00f3ff'
                  }
                }
              }}
            />
          </Stack>
        </Box>
      </TacticalPanel>

      {/* Action Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleActionClose}
        slotProps={{
          paper: {
            sx: {
              bgcolor: '#001a24',
              border: '1px solid rgba(0, 243, 255, 0.2)',
              color: '#fff',
              '& .MuiMenuItem-root': {
                fontSize: '12px',
                fontWeight: 600,
                fontFamily: 'Inter',
                '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.1)' }
              }
            }
          }
        }}
      >
        {/* <MenuItem onClick={() => { handleActionClose(); setAttackSurfaceModalOpen(true); }}>
          <ListItemIcon><Eye size={16} color="#00f3ff" /></ListItemIcon>
          <ListItemText primary="ATTACK SURFACE" />
        </MenuItem>
        <MenuItem onClick={() => { handleActionClose(); setSubscanModalOpen(true); }}>
          <ListItemIcon><Zap size={16} color="#00f3ff" /></ListItemIcon>
          <ListItemText primary="INITIATE SCAN" />
        </MenuItem>
        <MenuItem onClick={() => { handleActionClose(); setTodoModalOpen(true); }}>
          <ListItemIcon><FilePlus size={16} color="#00f3ff" /></ListItemIcon>
          <ListItemText primary="ADD NOTE" />
        </MenuItem> */}
        <MenuItem onClick={handleLaunchADAssessment} sx={{ color: '#00f3ff' }}>
          <ListItemIcon><Network size={16} color="#00f3ff" /></ListItemIcon>
          <ListItemText primary="ASSESS IDENTITY INFRASTRUCTURE" />
        </MenuItem>
        <Divider sx={{ my: 0.5, borderColor: 'rgba(255,255,255,0.08)' }} />
        <MenuItem onClick={() => handleToggleImportant(selectedId!)} sx={{ color: '#ffae00' }}>
          <ListItemIcon><Shield size={16} color="#ffae00" /></ListItemIcon>
          <ListItemText primary={targetSubdomain?.is_important ? "UNMARK IMPORTANT" : "MARK IMPORTANT"} />
        </MenuItem>
        <MenuItem onClick={() => handleDelete(selectedId!)} sx={{ color: '#ff003c' }}>
          <ListItemIcon><Trash2 size={16} color="#ff003c" /></ListItemIcon>
          <ListItemText primary="DELETE ASSET" />
        </MenuItem>
      </Menu>

      {/* Subscan Overlay */}
      <Dialog
        open={subscanModalOpen}
        onClose={() => setSubscanModalOpen(false)}
        maxWidth="xs"
        fullWidth
        slotProps={{
          paper: {
            sx: {
              bgcolor: '#0a0a0a',
              border: '1px solid rgba(0, 243, 255, 0.2)',
            }
          }
        }}
      >
        <DialogTitle sx={{ color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '0.9rem', letterSpacing: 2 }}>
          CONFIGURE SUBSCAN: {selectedAssets.length > 0 ? `${selectedAssets.length} ASSETS` : targetSubdomain?.name}
        </DialogTitle>
        <DialogContent>
          <Typography sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem', mb: 2, fontFamily: 'monospace' }}>
            SELECT ENGINE & ANALYTIC TASKS
          </Typography>
          
          <FormControl fullWidth size="small" sx={{ mb: 3 }}>
            <InputLabel id="engine-select-label" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem' }}>Scan Engine</InputLabel>
            <Select
              labelId="engine-select-label"
              value={selectedEngineId || ''}
              label="Scan Engine"
              onChange={(e) => {
                setSelectedEngineId(Number(e.target.value));
                setSelectedTasks([]);
              }}
              sx={{
                color: '#fff',
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1)' },
                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(0, 243, 255, 0.3)' },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#00f3ff' },
              }}
            >
              {enginesData?.map(engine => (
                <MenuItem key={engine.id} value={engine.id}>{engine.engine_name}</MenuItem>
              ))}
            </Select>
          </FormControl>

          {selectedEngine && (
            <Box>
              <Typography sx={{ color: 'rgba(0, 243, 255, 0.7)', fontSize: '0.65rem', mb: 1, fontWeight: 900, fontFamily: 'Orbitron' }}>
                AVAILABLE TASKS
              </Typography>
              <FormGroup>
                {[...selectedEngine.tasks]
                  .sort((a, b) => {
                    const ai = TASK_TIER_ORDER.indexOf(a);
                    const bi = TASK_TIER_ORDER.indexOf(b);
                    return (ai === -1 ? Infinity : ai) - (bi === -1 ? Infinity : bi);
                  })
                  .map((task: string) => (
                  <FormControlLabel
                    key={task}
                    control={
                      <Checkbox
                        size="small"
                        checked={selectedTasks.includes(task)}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedTasks(prev => [...prev, task]);
                          else setSelectedTasks(prev => prev.filter(t => t !== task));
                        }}
                        sx={{ color: 'rgba(0, 243, 255, 0.2)', '&.Mui-checked': { color: '#00f3ff' } }}
                      />
                    }
                    label={<Typography sx={{ fontSize: '0.8rem', color: '#fff', fontWeight: 600 }}>{task.replace(/_/g, ' ').toUpperCase()}</Typography>}
                  />
                ))}
              </FormGroup>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <Button onClick={() => setSubscanModalOpen(false)} sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>CANCEL</Button>
          <Button
            variant="contained"
            onClick={handleInitiateSubscan}
            disabled={subscanMutation.isPending || !selectedEngineId || selectedTasks.length === 0}
            sx={{
              bgcolor: 'rgba(0, 243, 255, 0.1)',
              color: '#00f3ff',
              border: '1px solid rgba(0, 243, 255, 0.2)',
              fontSize: '0.7rem',
              fontWeight: 900,
              '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)' }
            }}
          >
            {subscanMutation.isPending ? 'INITIATING...' : 'RUN SUBSCAN'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Attack Surface Modal */}
      <Dialog
        open={attackSurfaceModalOpen}
        onClose={() => setAttackSurfaceModalOpen(false)}
        maxWidth="md"
        fullWidth
        slotProps={{
          paper: {
            sx: {
              bgcolor: '#0a0a0a',
              border: '1px solid rgba(0, 243, 255, 0.2)',
            }
          }
        }}
      >
        <DialogTitle sx={{ color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '0.9rem', letterSpacing: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          ATTACK SURFACE ANALYSIS: {targetSubdomain?.name}
          <IconButton onClick={() => setAttackSurfaceModalOpen(false)} size="small" sx={{ color: 'rgba(255,255,255,0.3)' }}><X size={18} /></IconButton>
        </DialogTitle>
        <DialogContent>
          {attackSurfaceMutation.isPending ? (
            <Box sx={{ py: 8, textAlign: 'center' }}>
              <CircularProgress size={32} sx={{ color: '#00f3ff' }} />
              <Typography sx={{ color: 'rgba(0, 243, 255, 0.5)', fontSize: '0.7rem', mt: 2, fontFamily: 'Orbitron', letterSpacing: 1 }}>
                AI ENGINE ANALYZING TARGET VECTOR...
              </Typography>
            </Box>
          ) : attackSurfaceMutation.isError ? (
            <Alert severity="error" sx={{ bgcolor: 'rgba(255, 0, 60, 0.05)', color: '#ff003c', border: '1px solid rgba(255, 0, 60, 0.2)' }}>
              {((attackSurfaceMutation.error as any)?.response?.data?.error) || (attackSurfaceMutation.error as any)?.message || "Failed to generate attack surface. Ensure LLM is configured in settings."}
            </Alert>
          ) : attackSurfaceMutation.data?.status === false ? (
            <Alert severity="error" sx={{ bgcolor: 'rgba(255, 0, 60, 0.05)', color: '#ff003c', border: '1px solid rgba(255, 0, 60, 0.2)' }}>
              {attackSurfaceMutation.data?.error || "Failed to generate attack surface. Ensure LLM is configured in settings."}
            </Alert>
          ) : (
            <Box sx={{
              p: 3,
              bgcolor: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.05)',
              borderRadius: 1,
              maxHeight: '70vh',
              overflow: 'auto',
              color: 'rgba(255,255,255,0.9)',
              '& .markdown-content': {
                fontFamily: 'Inter, sans-serif',
                fontSize: '0.9rem',
                lineHeight: 1.6,
                '& h1, h2, h3': { color: '#00f3ff', fontFamily: 'Orbitron', mt: 3, mb: 1.5, letterSpacing: 1 },
                '& p': { mb: 2 },
                '& ul, ol': { mb: 2, pl: 3 },
                '& li': { mb: 1 },
                '& strong': { color: '#00f3ff', fontWeight: 800 },
                '& code': { bgcolor: 'rgba(0, 243, 255, 0.1)', px: 0.5, borderRadius: 0.5, color: '#00f3ff', fontFamily: 'monospace' },
                '& pre': { bgcolor: 'rgba(0,0,0,0.3)', p: 2, borderRadius: 1, border: '1px solid rgba(255,255,255,0.05)', overflow: 'auto', mb: 2 },
              }
            }}>
              <div className="markdown-content">
                <ReactMarkdown>
                  {attackSurfaceMutation.data?.description || "No analysis provided by LLM."}
                </ReactMarkdown>
              </div>
            </Box>
          )}
        </DialogContent>
      </Dialog>

      {/* Add TODO Modal */}
      <Dialog
        open={todoModalOpen}
        onClose={() => setTodoModalOpen(false)}
        maxWidth="xs"
        fullWidth
        slotProps={{
          paper: {
            sx: {
              bgcolor: '#0a0a0a',
              border: '1px solid rgba(255, 174, 0, 0.2)',
            }
          }
        }}
      >
        <DialogTitle sx={{ color: '#ffae00', fontFamily: 'Orbitron', fontSize: '0.9rem', letterSpacing: 2 }}>
          ADD RECON NOTE: {targetSubdomain?.name}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Title"
              fullWidth
              size="small"
              value={todoTitle}
              onChange={(e) => setTodoTitle(e.target.value)}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  color: '#fff',
                  '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                  '&:hover fieldset': { borderColor: '#ffae00' },
                  '&.Mui-focused fieldset': { borderColor: '#ffae00' },
                },
                '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.4)' }
              }}
            />
            <TextField
              label="Description"
              fullWidth
              multiline
              rows={3}
              value={todoDescription}
              onChange={(e) => setTodoDescription(e.target.value)}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  color: '#fff',
                  '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                  '&:hover fieldset': { borderColor: '#ffae00' },
                  '&.Mui-focused fieldset': { borderColor: '#ffae00' },
                },
                '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.4)' }
              }}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <Button onClick={() => setTodoModalOpen(false)} sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>CANCEL</Button>
          <Button
            variant="contained"
            onClick={handleAddTodo}
            disabled={createTodoMutation.isPending}
            sx={{
              bgcolor: 'rgba(255, 174, 0, 0.1)',
              color: '#ffae00',
              border: '1px solid rgba(255, 174, 0, 0.2)',
              fontSize: '0.7rem',
              fontWeight: 900,
              '&:hover': { bgcolor: 'rgba(255, 174, 0, 0.2)' }
            }}
          >
            {createTodoMutation.isPending ? 'SAVING...' : 'SAVE NOTE'}
          </Button>
        </DialogActions>
      </Dialog>
      {/* Confirmation Dialog */}
      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => {
          confirmConfig.onConfirm();
          setConfirmOpen(false);
        }}
        title={confirmConfig.title}
        message={confirmConfig.message}
        type={confirmConfig.type}
      />

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          variant="filled"
          sx={{
            fontFamily: 'Orbitron',
            fontSize: '0.8rem',
            fontWeight: 700,
            bgcolor: snackbar.severity === 'success' ? 'rgba(0, 243, 255, 0.9)' : 'rgba(255, 0, 85, 0.9)',
            color: '#000',
            '& .MuiAlert-icon': { color: '#000' }
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>

      <Snackbar
        open={adLaunchMsg !== null}
        autoHideDuration={6000}
        onClose={() => setAdLaunchMsg(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity={adLaunchMsg?.severity ?? 'info'}
          onClose={() => setAdLaunchMsg(null)}
          sx={{ width: '100%' }}
        >
          {adLaunchMsg?.text}
        </Alert>
      </Snackbar>

      {/* Lightbox Modal */}
      <Modal
        open={!!lightboxSrc}
        onClose={closeLightbox}
        closeAfterTransition
        sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          zIndex: 999999 // Extremely high to be sure
        }}
      >
        <Fade in={!!lightboxSrc} timeout={200}>
          <Box
            sx={{
              position: 'relative',
              width: '100vw',
              height: '100vh',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              outline: 'none',
            }}
          >
            {/* Custom Backdrop - guaranteed to be behind since it's the first child */}
            <Box 
              onClick={closeLightbox}
              sx={{ 
                position: 'absolute', 
                inset: 0, 
                bgcolor: 'rgba(0, 0, 0, 0.92)', 
                backdropFilter: 'blur(8px)',
                zIndex: 1,
                cursor: 'zoom-out'
              }} 
            />
            
            {/* Content - guaranteed to be on top since it's after the backdrop and has higher zIndex */}
            <Box
              sx={{
                position: 'relative',
                zIndex: 2,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                p: 4,
                maxWidth: '95vw',
                maxHeight: '95vh',
              }}
            >
              <IconButton
                onClick={closeLightbox}
                sx={{
                  position: 'absolute',
                  top: -20,
                  right: -20,
                  color: 'rgba(255,255,255,0.8)',
                  bgcolor: 'rgba(0,0,0,0.5)',
                  zIndex: 3,
                  '&:hover': { color: '#fff', bgcolor: 'rgba(0, 243, 255, 0.2)' }
                }}
              >
                <X size={20} />
              </IconButton>
            
            <Box
              component="img"
              src={lightboxSrc || ''}
              alt="Screenshot Full View"
              onClick={(e) => e.stopPropagation()}
              sx={{
                maxWidth: '95vw',
                maxHeight: '85vh',
                objectFit: 'contain',
                borderRadius: 1,
                border: '1px solid rgba(0, 243, 255, 0.2)',
                boxShadow: '0 0 50px rgba(0, 243, 255, 0.15)',
                cursor: 'default'
              }}
            />
              </Box>
            </Box>
          </Fade>
      </Modal>
    </Box>
  );
};
