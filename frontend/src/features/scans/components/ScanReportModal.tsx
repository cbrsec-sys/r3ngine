import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Checkbox,
  IconButton,
  Stack,
  Divider,
  CircularProgress,
  TextField,
  Collapse
} from '@mui/material';
import { X, FileText, Shield, FileSearch, Download, MessageSquare, ChevronDown, ChevronUp } from 'lucide-react';
import { useThemeTokens } from '../../../theme/useThemeTokens';

const SectionTitle = ({ title, icon }: { title: string, icon?: React.ReactNode }) => {
  const { tokens } = useThemeTokens();
  return (
    <Typography sx={{
      color: tokens.accent.primary,
      fontFamily: 'Orbitron',
      fontSize: '0.75rem',
      fontWeight: 800,
      mb: 2,
      display: 'flex',
      alignItems: 'center',
      gap: 1
    }}>
      {icon} {title}
    </Typography>
  );
};

interface ScanReportModalProps {
  open: boolean;
  onClose: () => void;
  scanId: number;
}

export const ScanReportModal: React.FC<ScanReportModalProps> = ({ open, onClose, scanId }) => {
  const { tokens } = useThemeTokens();
  const [reportType, setReportType] = useState('full');
  const [reportTemplate, setReportTemplate] = useState('modern');
  const [ignoreInfoVuln, setIgnoreInfoVuln] = useState(false);
  const [includeAttackSurface, setIncludeAttackSurface] = useState(false);
  const [includeAttackPaths, setIncludeAttackPaths] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState<string | null>(null);
  const [reportUrl, setReportUrl] = useState<string | null>(null);
  const [comments, setComments] = useState('');
  const [commentsExpanded, setCommentsExpanded] = useState(false);

  const pollReportStatus = async (reportId: number) => {
    setIsGenerating(true);
    setGenerationStatus('Generating report...');
    
    const checkStatus = async () => {
      try {
        const response = await fetch(`/scan/report/status/${reportId}`, {
          credentials: 'include'
        });
        if (!response.ok) throw new Error('Failed to check status');
        
        const data = await response.json();
        
        if (data.status === 2) { // Success
          setIsGenerating(false);
          setGenerationStatus('Report successfully generated!');
          setReportUrl(data.report_url);
          
          // Try to auto-open only if it's the first time reaching success
          if (data.report_url) {
            const win = window.open(data.report_url, '_blank');
            if (!win) {
              setGenerationStatus('Report ready! Please click the download button below (Popup was blocked).');
            }
          }
        } else if (data.status === 0) { // Failed
          setIsGenerating(false);
          setGenerationStatus(`Error: ${data.error_message || 'Unknown error'}`);
        } else {
          // Continue polling
          setTimeout(checkStatus, 3000);
        }
      } catch (error) {
        setIsGenerating(false);
        setGenerationStatus('Failed to check report status');
      }
    };
    
    checkStatus();
  };

  const initiateReport = async (download: boolean) => {
    setGenerationStatus('Initiating report generation...');
    setIsGenerating(true);
    
    try {
      const params = new URLSearchParams({
        report_type: reportType,
        report_template: reportTemplate,
        ignore_info_vuln: ignoreInfoVuln ? 'True' : 'False',
        include_attack_surface_map: includeAttackSurface ? 'True' : 'False',
        include_attack_paths: includeAttackPaths ? 'True' : 'False',
        download: download ? 'True' : 'False',
        comments: comments
      });
      
      const response = await fetch(`/scan/create_report/${scanId}?${params.toString()}`, {
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('Failed to initiate report');
      
      const data = await response.json();
      if (data.status && data.report_id) {
        pollReportStatus(data.report_id);
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (error) {
      setIsGenerating(false);
      setGenerationStatus('Failed to initiate report generation');
    }
  };

  const handleDownload = () => initiateReport(true);
  const handlePreview = () => initiateReport(false);

  return (
    <Dialog
      open={open}
      onClose={isGenerating ? undefined : onClose}
      maxWidth="sm"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            bgcolor: 'background.default',
            backgroundImage: 'linear-gradient(rgba(0, 243, 255, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 243, 255, 0.02) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
            border: `1px solid ${tokens.accent.primary}33`,
            borderRadius: 0,
            boxShadow: `0 0 30px rgba(0, 0, 0, 0.5), 0 0 10px ${tokens.accent.primary}15`,
          }
        }
      }}
    >
      <DialogTitle sx={{
        m: 0,
        p: 2,
        bgcolor: `${tokens.accent.primary}0D`,
        borderBottom: `1px solid ${tokens.accent.primary}15`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
          <FileText size={20} color={tokens.accent.primary} />
          <Typography sx={{
            fontFamily: 'Orbitron',
            fontWeight: 900,
            color: 'text.primary',
            letterSpacing: '0.1rem',
            fontSize: '1rem'
          }}>
            GENERATE SCAN REPORT
          </Typography>
        </Stack>
        {!isGenerating && (
          <IconButton onClick={onClose} sx={{ color: 'text.secondary', '&:hover': { color: '#ff003c' } }}>
            <X size={20} />
          </IconButton>
        )}
      </DialogTitle>

      <DialogContent sx={{ p: 3, mt: 2 }}>
        <Stack spacing={4}>
          {generationStatus && (
            <Box sx={{ 
              p: 2, 
              bgcolor: reportUrl ? 'rgba(0, 255, 127, 0.05)' : `${tokens.accent.primary}0D`, 
              border: `1px solid ${reportUrl ? 'rgba(0, 255, 127, 0.2)' : `${tokens.accent.primary}33`}`,
              borderRadius: 1,
              display: 'flex',
              alignItems: 'center',
              gap: 2
            }}>
              {isGenerating && <CircularProgress size={20} sx={{ color: tokens.accent.primary }} />}
              {!isGenerating && reportUrl && <Shield size={20} color="#00ff7f" />}
              <Typography sx={{ color: reportUrl ? '#00ff7f' : tokens.accent.primary, fontSize: '0.8rem', fontWeight: 700, fontFamily: 'Orbitron' }}>
                {generationStatus}
              </Typography>
            </Box>
          )}

          <Box sx={{ opacity: isGenerating ? 0.5 : 1, pointerEvents: isGenerating ? 'none' : 'auto' }}>
            <Typography sx={{
              color: tokens.accent.primary,
              fontFamily: 'Orbitron',
              fontSize: '0.75rem',
              fontWeight: 800,
              mt: 1, // Added padding/margin above
              mb: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }}>
              <FileSearch size={14} /> SELECT REPORT TYPE
            </Typography>
            <FormControl component="fieldset">
              <RadioGroup value={reportType} onChange={(e) => setReportType(e.target.value)}>
                <Stack spacing={1}>
                  <FormControlLabel
                    value="full"
                    control={<Radio sx={{ color: `${tokens.accent.primary}33`, '&.Mui-checked': { color: tokens.accent.primary } }} />}
                    label={
                      <Box>
                        <Typography sx={{ color: 'text.primary', fontSize: '0.85rem', fontWeight: 700, fontFamily: 'Orbitron' }}>Full Scan Report</Typography>
                        <Typography sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>Includes all findings: subdomains, endpoints, and vulnerabilities.</Typography>
                      </Box>
                    }
                  />
                  <FormControlLabel
                    value="vulnerability"
                    control={<Radio sx={{ color: `${tokens.accent.primary}33`, '&.Mui-checked': { color: tokens.accent.primary } }} />}
                    label={
                      <Box>
                        <Typography sx={{ color: 'text.primary', fontSize: '0.85rem', fontWeight: 700, fontFamily: 'Orbitron' }}>Vulnerability Report</Typography>
                        <Typography sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>Focuses specifically on detected security vulnerabilities.</Typography>
                      </Box>
                    }
                  />
                </Stack>
              </RadioGroup>
            </FormControl>
          </Box>

          <Divider sx={{ borderColor: `${tokens.accent.primary}15` }} />

          <Box sx={{ opacity: isGenerating ? 0.5 : 1, pointerEvents: isGenerating ? 'none' : 'auto' }}>
            <Typography sx={{
              color: tokens.accent.primary,
              fontFamily: 'Orbitron',
              fontSize: '0.75rem',
              fontWeight: 800,
              mb: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }}>
              <Shield size={14} /> REPORT SETTINGS
            </Typography>
            <Stack spacing={2}>
              <Box>
                <Typography sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', fontWeight: 800, mb: 1, fontFamily: 'Orbitron' }}>TEMPLATE</Typography>
                <RadioGroup row value={reportTemplate} onChange={(e) => {
                  const val = e.target.value;
                  setReportTemplate(val);
                  if (val !== 'enterprise' && val !== 'cyber_pro') {
                    setIncludeAttackSurface(false);
                    setIncludeAttackPaths(false);
                  }
                }}>
                  <FormControlLabel
                    value="default"
                    control={<Radio size="small" sx={{ color: `${tokens.accent.primary}33`, '&.Mui-checked': { color: tokens.accent.primary } }} />}
                    label={<Typography sx={{ color: 'text.primary', fontSize: '0.8rem', fontWeight: 600 }}>Default</Typography>}
                  />
                  <FormControlLabel
                    value="modern"
                    control={<Radio size="small" sx={{ color: `${tokens.accent.primary}33`, '&.Mui-checked': { color: tokens.accent.primary } }} />}
                    label={<Typography sx={{ color: 'text.primary', fontSize: '0.8rem', fontWeight: 600 }}>Modern (V2)</Typography>}
                  />
                  <FormControlLabel
                    value="enterprise"
                    control={<Radio size="small" sx={{ color: `${tokens.accent.primary}33`, '&.Mui-checked': { color: tokens.accent.primary } }} />}
                    label={<Typography sx={{ color: 'text.primary', fontSize: '0.8rem', fontWeight: 600 }}>Enterprise</Typography>}
                  />
                  <FormControlLabel
                    value="cyber_pro"
                    control={<Radio size="small" sx={{ color: `${tokens.accent.primary}33`, '&.Mui-checked': { color: tokens.accent.primary } }} />}
                    label={<Typography sx={{ color: 'text.primary', fontSize: '0.8rem', fontWeight: 600 }}>Cyber Pro</Typography>}
                  />
                </RadioGroup>
              </Box>

              <Stack spacing={1}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={ignoreInfoVuln}
                      onChange={(e) => setIgnoreInfoVuln(e.target.checked)}
                      sx={{ color: `${tokens.accent.primary}33`, '&.Mui-checked': { color: tokens.accent.primary } }}
                    />
                  }
                  label={<Typography sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.8rem', fontWeight: 600 }}>Ignore Information Vulnerabilities</Typography>}
                />

                <FormControlLabel
                  control={
                    <Checkbox
                      checked={includeAttackSurface}
                      disabled={reportTemplate !== 'enterprise' && reportTemplate !== 'cyber_pro'}
                      onChange={(e) => setIncludeAttackSurface(e.target.checked)}
                      sx={{ 
                        color: `${tokens.accent.primary}15`, 
                        '&.Mui-checked': { color: tokens.accent.primary },
                        '&.Mui-disabled': { color: 'rgba(255,255,255,0.05)' }
                      }}
                    />
                  }
                  label={
                    <Box>
                      <Typography sx={{ 
                        color: (reportTemplate === 'enterprise' || reportTemplate === 'cyber_pro') ? 'rgba(255,255,255,0.7)' : 'rgba(255,255,255,0.2)', 
                        fontSize: '0.8rem', 
                        fontWeight: 600,
                        transition: 'color 0.2s'
                      }}>
                        Include Attack Surface Map
                      </Typography>
                      {reportTemplate !== 'enterprise' && reportTemplate !== 'cyber_pro' && (
                        <Typography sx={{ color: `${tokens.accent.primary}4D`, fontSize: '0.65rem' }}>Only available for Enterprise/Pro templates</Typography>
                      )}
                    </Box>
                  }
                />

                <FormControlLabel
                  control={
                    <Checkbox
                      checked={includeAttackPaths}
                      disabled={reportTemplate !== 'enterprise' && reportTemplate !== 'cyber_pro'}
                      onChange={(e) => setIncludeAttackPaths(e.target.checked)}
                      sx={{ 
                        color: 'rgba(0,243,255,0.1)', 
                        '&.Mui-checked': { color: '#00f3ff' },
                        '&.Mui-disabled': { color: 'rgba(255,255,255,0.05)' }
                      }}
                    />
                  }
                  label={
                    <Box>
                      <Typography sx={{ 
                        color: (reportTemplate === 'enterprise' || reportTemplate === 'cyber_pro') ? 'rgba(255,255,255,0.7)' : 'rgba(255,255,255,0.2)', 
                        fontSize: '0.8rem', 
                        fontWeight: 600,
                        transition: 'color 0.2s'
                      }}>
                        Include Attack Paths
                      </Typography>
                      {reportTemplate !== 'enterprise' && reportTemplate !== 'cyber_pro' && (
                        <Typography sx={{ color: 'rgba(0,243,255,0.3)', fontSize: '0.65rem' }}>Only available for Enterprise/Pro templates</Typography>
                      )}
                    </Box>
                  }
                />
              </Stack>
            </Stack>
          </Box>

          <Divider sx={{ borderColor: `${tokens.accent.primary}15` }} />

          <Box sx={{ opacity: isGenerating ? 0.5 : 1, pointerEvents: isGenerating ? 'none' : 'auto' }}>
            <Box
              onClick={() => setCommentsExpanded(!commentsExpanded)}
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                userSelect: 'none',
                mb: commentsExpanded ? 2 : 0,
                '&:hover': {
                  opacity: 0.8
                }
              }}
            >
              <Typography sx={{
                color: tokens.accent.primary,
                fontFamily: 'Orbitron',
                fontSize: '0.75rem',
                fontWeight: 800,
                display: 'flex',
                alignItems: 'center',
                gap: 1
              }}>
                <MessageSquare size={14} /> ASSESSMENT COMMENTS (OPTIONAL)
              </Typography>
              {commentsExpanded ? <ChevronUp size={16} color={tokens.accent.primary} /> : <ChevronDown size={16} color={tokens.accent.primary} />}
            </Box>
            
            <Collapse in={commentsExpanded}>
              <TextField
                fullWidth
                multiline
                rows={4}
                placeholder="Enter any comments or notes about the assessment to insert into the {comments} placeholder..."
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                sx={getFieldStyles(tokens)}
              />
            </Collapse>
          </Box>
        </Stack>
      </DialogContent>

      <DialogActions sx={{ p: 3, bgcolor: 'rgba(0, 243, 255, 0.02)', borderTop: `1px solid ${tokens.accent.primary}15` }}>
        <Button
          onClick={onClose}
          disabled={isGenerating}
          sx={{
            color: 'text.secondary',
            fontFamily: 'Orbitron',
            fontWeight: 800,
            fontSize: '0.7rem',
            mr: 'auto',
            '&:hover': { color: 'text.primary' }
          }}
        >
          CANCEL
        </Button>
        {reportUrl ? (
          <Button
            href={reportUrl}
            target="_blank"
            variant="contained"
            startIcon={<Download size={16} />}
            sx={{
              bgcolor: '#00ff7f',
              color: '#000',
              fontFamily: 'Orbitron',
              fontWeight: 900,
              fontSize: '0.75rem',
              px: 4,
              '&:hover': { bgcolor: '#00e672' }
            }}
          >
            DOWNLOAD NOW
          </Button>
        ) : (
          <>
            <Button
              onClick={handlePreview}
              disabled={isGenerating}
              sx={{
                color: tokens.accent.primary,
                fontFamily: 'Orbitron',
                fontWeight: 800,
                fontSize: '0.7rem',
                border: `1px solid ${tokens.accent.primary}4D`,
                px: 2,
                '&:hover': { bgcolor: `${tokens.accent.primary}0D`, borderColor: tokens.accent.primary }
              }}
            >
              PREVIEW
            </Button>
            <Button
              onClick={handleDownload}
              variant="contained"
              disabled={isGenerating}
              startIcon={isGenerating ? <CircularProgress size={16} sx={{ color: '#000' }} /> : <Download size={16} />}
              sx={{
                bgcolor: tokens.accent.primary,
                color: '#000',
                fontFamily: 'Orbitron',
                fontWeight: 900,
                fontSize: '0.7rem',
                px: 3,
                '&:hover': { bgcolor: '#00d8e4' }
              }}
            >
              {isGenerating ? 'GENERATING...' : 'GENERATE & DOWNLOAD'}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

const getFieldStyles = (tokens: any) => ({
  '& .MuiOutlinedInput-root': {
    color: 'text.primary',
    '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
    '&:hover fieldset': { borderColor: `${tokens.accent.primary}4D` },
    '&.Mui-focused fieldset': { borderColor: tokens.accent.primary },
    bgcolor: 'rgba(255,255,255,0.03)',
  },
  '& .MuiInputLabel-root': {
    color: 'text.secondary',
    '&.Mui-focused': { color: tokens.accent.primary }
  },
});

