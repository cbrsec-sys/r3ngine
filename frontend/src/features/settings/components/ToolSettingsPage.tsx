import React, { useState } from 'react';
import axios from 'axios';
import { 
  Box, 
  Typography, 
  Grid, 
  Button, 
  Tabs, 
  Tab, 
  Paper, 
  IconButton, 
  Tooltip,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  TextField,
  Alert,
  Snackbar
} from '@mui/material';
import { 
  Settings, 
  Upload, 
  Save, 
  FileText, 
  Zap, 
  Shield, 
  Code,
  CheckCircle,
  AlertTriangle,
  Search,
  Trash2,
  Edit3,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import { TacticalPanel } from '../../../components/TacticalPanel';
import { 
  useToolSettings, 
  useFileContent, 
  useUpdateToolConfig, 
  useUploadToolFiles 
} from '../api';
import { useParams } from '@tanstack/react-router';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tool-tabpanel-${index}`}
      aria-labelledby={`tool-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ py: 2 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export const ToolSettingsPage: React.FC = () => {
  const { projectSlug } = useParams({ from: '/$projectSlug/settings/tool-settings' });
  const [tabValue, setTabValue] = useState(0);
  const [editingFile, setEditingFile] = useState<{ key: string; name: string } | null>(null);
  const [fileContent, setFileContent] = useState('');
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const { data: toolSettings, isLoading } = useToolSettings(projectSlug);
  const updateConfig = useUpdateToolConfig(projectSlug);
  const uploadFiles = useUploadToolFiles(projectSlug);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setEditingFile(null);
  };

  const handleEditConfig = (key: string, name: string) => {
    setEditingFile({ key, name });
    // Note: We'll use the fileContent hook by setting a query param state if needed,
    // but for simplicity and to match the legacy logic which fetches on click,
    // we can use axios directly or a manual refetch.
    // Let's use axios for now to ensure it works with the current setup.
    setFileContent('Loading...');
    axios.get(`/api/getFileContents/?${key}`)
      .then(res => {
        if (res.data.status) setFileContent(res.data.content);
        else setFileContent('Error loading file content');
      })
      .catch(() => setFileContent('Failed to fetch file content'));
  };

  const handleEditGF = (patternName: string) => {
    setEditingFile({ key: 'gf_pattern', name: patternName });
    setFileContent('Loading...');
    axios.get(`/api/getFileContents/?gf_pattern&name=${patternName}`)
      .then(res => {
        if (res.data.status) setFileContent(res.data.content);
        else setFileContent('Error loading GF pattern');
      })
      .catch(() => setFileContent('Failed to fetch GF pattern'));
  };

  const handleViewNucleiTemplate = (templateName: string) => {
    setEditingFile({ key: 'nuclei_template', name: templateName });
    setFileContent('Loading...');
    axios.get(`/api/getFileContents/?nuclei_template&name=${templateName}`)
      .then(res => {
        if (res.data.status) setFileContent(res.data.content);
        else setFileContent('Error loading template');
      })
      .catch(() => setFileContent('Failed to fetch template'));
  };

  const handleSaveConfig = () => {
    if (!editingFile) return;
    
    // Map the key back to the form field name expected by the backend
    let postKey = '';
    if (editingFile.key === 'nuclei_config') postKey = 'nuclei_config_text_area';
    else if (editingFile.key === 'subfinder_config') postKey = 'subfinder_config_text_area';
    else if (editingFile.key === 'naabu_config') postKey = 'naabu_config_text_area';
    else if (editingFile.key === 'amass_config') postKey = 'amass_config_text_area';
    else if (editingFile.key === 'theharvester_config') postKey = 'theharvester_config_text_area';
    else if (editingFile.key === 'spiderfoot_config') postKey = 'spiderfoot_config_text_area';
    
    if (postKey) {
      updateConfig.mutate({ key: postKey, content: fileContent }, {
        onSuccess: (data) => {
          setSnackbar({ open: true, message: data.message || 'Config updated successfully', severity: 'success' });
          setEditingFile(null);
        },
        onError: () => {
          setSnackbar({ open: true, message: 'Failed to update config', severity: 'error' });
        }
      });
    }
  };

  const handleFileUpload = (key: string, e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      uploadFiles.mutate({ key, files }, {
        onSuccess: (data) => {
          setSnackbar({ open: true, message: data.message, severity: 'success' });
        },
        onError: (error: any) => {
          setSnackbar({ open: true, message: error.response?.data?.message || 'Upload failed', severity: 'error' });
        }
      });
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 10 }}>
        <CircularProgress sx={{ color: '#00f3ff' }} />
      </Box>
    );
  }

  const configFiles = [
    { key: 'nuclei_config', name: 'Nuclei Config', icon: <Shield size={20} /> },
    { key: 'subfinder_config', name: 'Subfinder Config', icon: <Search size={20} /> },
    { key: 'naabu_config', name: 'Naabu Config', icon: <Zap size={20} /> },
    { key: 'amass_config', name: 'Amass Config', icon: <FileText size={20} /> },
    { key: 'theharvester_config', name: 'theHarvester Config', icon: <Search size={20} /> },
    { key: 'spiderfoot_config', name: 'SpiderFoot Config', icon: <Settings size={20} /> },
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontFamily: 'Orbitron', fontWeight: 900, color: '#fff', mb: 1 }}>
          TOOL_SETTINGS
        </Typography>
        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>
          Manage configuration files, GF patterns, and Nuclei templates.
        </Typography>
      </Box>

      <TacticalPanel title="CONFIGURATION_PANEL" sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'rgba(255,255,255,0.1)' }}>
          <Tabs 
            value={tabValue} 
            onChange={handleTabChange}
            sx={{
              '& .MuiTabs-indicator': { bgcolor: '#00f3ff' },
              '& .MuiTab-root': { 
                color: 'rgba(255,255,255,0.5)',
                fontFamily: 'Orbitron',
                fontSize: '12px',
                '&.Mui-selected': { color: '#00f3ff' }
              }
            }}
          >
            <Tab label="GF PATTERNS" />
            <Tab label="NUCLEI TEMPLATES" />
            <Tab label="CONFIG FILES" />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={3}>
              <Paper sx={{ bgcolor: 'rgba(0,0,0,0.3)', p: 2, border: '1px solid rgba(0,243,255,0.1)', width: '100%' }}>
                <Typography variant="h6" sx={{ color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '14px', mb: 2 }}>
                  UPLOAD GF PATTERNS
                </Typography>
                <input
                  accept=".json"
                  style={{ display: 'none' }}
                  id="gf-upload"
                  multiple
                  type="file"
                  onChange={(e) => handleFileUpload('gfFileUpload', e)}
                />
                <label htmlFor="gf-upload">
                  <Button
                    variant="outlined"
                    component="span"
                    fullWidth
                    startIcon={<Upload size={18} />}
                    sx={{ 
                      borderColor: '#00f3ff', 
                      color: '#00f3ff',
                      '&:hover': { bgcolor: 'rgba(0,243,255,0.1)', borderColor: '#00f3ff' }
                    }}
                  >
                    SELECT JSON FILES
                  </Button>
                </label>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', mt: 1, display: 'block' }}>
                  Upload multiple .json patterns for GF
                </Typography>
              </Paper>

              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" sx={{ color: 'rgba(255,255,255,0.7)', mb: 1 }}>
                  INSTALLED PATTERNS ({toolSettings?.gf_patterns.length})
                </Typography>
                <Paper sx={{ 
                  bgcolor: 'rgba(0,0,0,0.2)', 
                  maxHeight: '400px', 
                  overflow: 'auto',
                  border: '1px solid rgba(255,255,255,0.05)',
                  width: '100%'
                }}>
                  <List dense>
                    {toolSettings?.gf_patterns.map((pattern) => (
                      <ListItem 
                        key={pattern}
                        button
                        onClick={() => handleEditGF(pattern)}
                        sx={{ 
                          '&:hover': { bgcolor: 'rgba(0,243,255,0.05)' },
                          borderBottom: '1px solid rgba(255,255,255,0.05)'
                        }}
                      >
                        <ListItemText 
                          primary={pattern} 
                          primaryTypographyProps={{ sx: { color: 'rgba(255,255,255,0.8)', fontSize: '13px' } }}
                        />
                        <ChevronRight size={14} color="rgba(255,255,255,0.3)" />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Box>
            </Grid>

            <Grid item xs={12} md={9}>
              {editingFile && editingFile.key === 'gf_pattern' ? (
                <Paper sx={{ bgcolor: 'rgba(0,0,0,0.3)', p: 2, border: '1px solid rgba(0,243,255,0.2)', width: '100%' }}>
                   <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography sx={{ color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '14px' }}>
                      EDITING: {editingFile.name}
                    </Typography>
                    <Box>
                       <Button 
                        size="small" 
                        variant="contained" 
                        startIcon={<Save size={16} />}
                        onClick={handleSaveConfig}
                        disabled={updateConfig.isPending}
                        sx={{ bgcolor: '#00f3ff', color: '#000', fontWeight: 'bold', '&:hover': { bgcolor: '#00d8e4' } }}
                      >
                        SAVE
                      </Button>
                      <Button 
                        size="small" 
                        sx={{ color: 'rgba(255,255,255,0.5)', ml: 1 }}
                        onClick={() => setEditingFile(null)}
                      >
                        CANCEL
                      </Button>
                    </Box>
                  </Box>
                  <TextField
                    multiline
                    fullWidth
                    rows={20}
                    value={fileContent}
                    onChange={(e) => setFileContent(e.target.value)}
                    variant="standard"
                    InputProps={{
                      disableUnderline: true,
                      sx: { 
                        fontFamily: 'monospace', 
                        color: '#a9b7c6', 
                        bgcolor: '#1e1e1e', 
                        p: 2,
                        fontSize: '13px',
                        border: '1px solid rgba(0,243,255,0.1)'
                      }
                    }}
                  />
                  <Alert severity="warning" sx={{ mt: 2, bgcolor: 'rgba(255,152,0,0.1)', color: '#ff9800' }}>
                    Manually editing GF patterns is experimental. Ensure the JSON structure is valid.
                  </Alert>
                </Paper>
              ) : (
                <Box sx={{ 
                  height: '100%', 
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  bgcolor: 'rgba(0,0,0,0.1)',
                  borderRadius: 1,
                  p: 5,
                  border: '1px dashed rgba(255,255,255,0.1)'
                }}>
                  <Code size={48} color="rgba(0,243,255,0.2)" />
                  <Typography sx={{ color: 'rgba(255,255,255,0.3)', mt: 2, fontFamily: 'Orbitron', fontSize: '12px' }}>
                    SELECT A PATTERN TO VIEW OR EDIT
                  </Typography>
                </Box>
              )}
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Box sx={{ display: 'flex', gap: 2, width: '100%', alignItems: 'flex-start' }}>
            <Box sx={{ width: '300px', flexShrink: 0 }}>
              <Paper sx={{ bgcolor: 'rgba(0,0,0,0.3)', p: 2, border: '1px solid rgba(0,243,255,0.1)', mb: 2 }}>
                <Typography variant="h6" sx={{ color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '14px', mb: 2 }}>
                  UPLOAD NUCLEI TEMPLATES
                </Typography>
                <input
                  accept=".yaml,.yml"
                  style={{ display: 'none' }}
                  id="nuclei-upload"
                  multiple
                  type="file"
                  onChange={(e) => handleFileUpload('nucleiFileUpload', e)}
                />
                <label htmlFor="nuclei-upload">
                  <Button
                    variant="outlined"
                    component="span"
                    fullWidth
                    startIcon={<Upload size={18} />}
                    sx={{ 
                      borderColor: '#00f3ff', 
                      color: '#00f3ff',
                      '&:hover': { bgcolor: 'rgba(0,243,255,0.1)', borderColor: '#00f3ff' }
                    }}
                  >
                    SELECT YAML FILES
                  </Button>
                </label>
              </Paper>

              <Typography variant="subtitle2" sx={{ color: 'rgba(255,255,255,0.7)', mb: 1, fontFamily: 'Orbitron', fontSize: '11px' }}>
                CUSTOM TEMPLATES ({toolSettings?.nuclei_templates?.length || 0})
              </Typography>
              <Paper sx={{ 
                bgcolor: 'rgba(0,0,0,0.2)', 
                maxHeight: '500px', 
                overflow: 'auto',
                border: '1px solid rgba(255,255,255,0.05)',
                width: '100%'
              }}>
                <List dense>
                  {toolSettings?.nuclei_templates?.map((template) => (
                    <ListItem 
                      key={template}
                      button
                      selected={editingFile?.key === 'nuclei_template' && editingFile?.name === template}
                      onClick={() => handleViewNucleiTemplate(template)}
                      sx={{ 
                        borderBottom: '1px solid rgba(255,255,255,0.05)',
                        '&.Mui-selected': {
                          bgcolor: 'rgba(0,243,255,0.1)',
                          borderLeft: '3px solid #00f3ff'
                        },
                        '&:hover': { bgcolor: 'rgba(0,243,255,0.05)' }
                      }}
                    >
                      <ListItemText 
                        primary={template} 
                        primaryTypographyProps={{ 
                          sx: { 
                            color: (editingFile?.key === 'nuclei_template' && editingFile?.name === template) ? '#00f3ff' : 'rgba(255,255,255,0.8)', 
                            fontSize: '12px' 
                          } 
                        }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Box>

            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              {editingFile && editingFile.key === 'nuclei_template' ? (
                <Paper sx={{ bgcolor: 'rgba(0,0,0,0.3)', p: 2, border: '1px solid rgba(0,243,255,0.2)', width: '100%' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography sx={{ color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '14px' }}>
                      {editingFile.name} (READ-ONLY)
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Shield size={16} color="#00f3ff" />
                      <Typography sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '11px', fontFamily: 'Orbitron' }}>
                        TEMPLATES ARE VIEW-ONLY
                      </Typography>
                    </Box>
                  </Box>
                  <TextField
                    multiline
                    fullWidth
                    rows={28}
                    value={fileContent}
                    readOnly
                    variant="standard"
                    InputProps={{
                      readOnly: true,
                      disableUnderline: true,
                      sx: { 
                        fontFamily: 'monospace', 
                        color: '#a9b7c6', 
                        bgcolor: '#1e1e1e', 
                        p: 2,
                        fontSize: '13px',
                        border: '1px solid rgba(0,243,255,0.1)'
                      }
                    }}
                  />
                </Paper>
              ) : (
                <Box sx={{ 
                  height: '600px', 
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  bgcolor: 'rgba(0,0,0,0.1)',
                  borderRadius: 1,
                  p: 5,
                  border: '1px dashed rgba(255,255,255,0.1)'
                }}>
                  <Shield size={48} color="rgba(0,243,255,0.2)" />
                  <Typography sx={{ color: 'rgba(255,255,255,0.3)', mt: 2, fontFamily: 'Orbitron', fontSize: '12px', textAlign: 'center' }}>
                    SELECT A NUCLEI TEMPLATE TO VIEW CONTENT<br/>
                    UPLOAD NEW ONES USING THE PANEL ON THE LEFT
                  </Typography>
                </Box>
              )}
            </Box>
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <Box sx={{ display: 'flex', gap: 2, width: '100%', alignItems: 'flex-start' }}>
            <Box sx={{ width: '250px', flexShrink: 0 }}>
              <List sx={{ bgcolor: 'rgba(0,0,0,0.2)', borderRadius: 1 }}>
                {configFiles.map((file) => (
                  <ListItem 
                    key={file.key}
                    button
                    selected={editingFile?.key === file.key}
                    onClick={() => handleEditConfig(file.key, file.name)}
                    sx={{
                      '&.Mui-selected': {
                        bgcolor: 'rgba(0,243,255,0.1)',
                        borderLeft: '3px solid #00f3ff'
                      },
                      '&:hover': { bgcolor: 'rgba(0,243,255,0.05)' }
                    }}
                  >
                    <Box sx={{ mr: 2, color: editingFile?.key === file.key ? '#00f3ff' : 'rgba(255,255,255,0.5)' }}>
                      {file.icon}
                    </Box>
                    <ListItemText 
                      primary={file.name} 
                      primaryTypographyProps={{ 
                        sx: { 
                          color: editingFile?.key === file.key ? '#00f3ff' : 'rgba(255,255,255,0.7)',
                          fontSize: '13px',
                          fontFamily: 'Orbitron'
                        } 
                      }} 
                    />
                  </ListItem>
                ))}
              </List>
            </Box>

            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              {editingFile && editingFile.key !== 'gf_pattern' ? (
                <Paper sx={{ bgcolor: 'rgba(0,0,0,0.3)', p: 2, border: '1px solid rgba(0,243,255,0.2)', width: '100%' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography sx={{ color: '#00f3ff', fontFamily: 'Orbitron', fontSize: '14px' }}>
                      {editingFile.name}
                    </Typography>
                    <Button 
                      size="small" 
                      variant="contained" 
                      startIcon={<Save size={16} />}
                      onClick={handleSaveConfig}
                      disabled={updateConfig.isPending}
                      sx={{ bgcolor: '#00f3ff', color: '#000', fontWeight: 'bold', '&:hover': { bgcolor: '#00d8e4' } }}
                    >
                      UPDATE CONFIG
                    </Button>
                  </Box>
                  <TextField
                    multiline
                    fullWidth
                    rows={28}
                    value={fileContent}
                    onChange={(e) => setFileContent(e.target.value)}
                    variant="standard"
                    InputProps={{
                      disableUnderline: true,
                      sx: { 
                        fontFamily: 'monospace', 
                        color: '#a9b7c6', 
                        bgcolor: '#1e1e1e', 
                        p: 2,
                        fontSize: '13px',
                        border: '1px solid rgba(0,243,255,0.1)'
                      }
                    }}
                  />
                </Paper>
              ) : (
                <Box sx={{ 
                  height: '400px', 
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  bgcolor: 'rgba(0,0,0,0.1)',
                  borderRadius: 1,
                  p: 5,
                  border: '1px dashed rgba(255,255,255,0.1)'
                }}>
                  <Settings size={48} color="rgba(0,243,255,0.2)" />
                  <Typography sx={{ color: 'rgba(255,255,255,0.3)', mt: 2, fontFamily: 'Orbitron', fontSize: '12px' }}>
                    SELECT A TOOL CONFIGURATION TO EDIT
                  </Typography>
                </Box>
              )}
            </Box>
          </Box>
        </TabPanel>
      </TacticalPanel>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity}
          sx={{ width: '100%', bgcolor: snackbar.severity === 'success' ? '#1b5e20' : '#d32f2f', color: '#fff' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};
