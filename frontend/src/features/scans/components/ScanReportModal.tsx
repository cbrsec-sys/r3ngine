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
  Divider
} from '@mui/material';
import { X, FileText, Shield, FileSearch, Download } from 'lucide-react';

interface ScanReportModalProps {
  open: boolean;
  onClose: () => void;
  scanId: number;
}

export const ScanReportModal: React.FC<ScanReportModalProps> = ({ open, onClose, scanId }) => {
  const [reportType, setReportType] = useState('full');
  const [reportTemplate, setReportTemplate] = useState('modern');
  const [ignoreInfoVuln, setIgnoreInfoVuln] = useState(false);
  const [includeAttackSurface, setIncludeAttackSurface] = useState(false);

  const handleDownload = () => {
    const url = `/scan/create_report/${scanId}?report_type=${reportType}&report_template=${reportTemplate}&ignore_info_vuln=${ignoreInfoVuln ? 'True' : 'False'}&include_attack_surface_map=${includeAttackSurface ? 'True' : 'False'}&download=True`;
    window.open(url, '_blank');
    onClose();
  };

  const handlePreview = () => {
    const url = `/scan/create_report/${scanId}?report_type=${reportType}&report_template=${reportTemplate}&ignore_info_vuln=${ignoreInfoVuln ? 'True' : 'False'}&include_attack_surface_map=${includeAttackSurface ? 'True' : 'False'}&download=False`;
    window.open(url, '_blank');
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            bgcolor: '#0d0c14',
            backgroundImage: 'linear-gradient(rgba(0, 243, 255, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 243, 255, 0.02) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
            border: '1px solid rgba(0, 243, 255, 0.2)',
            borderRadius: 0,
            boxShadow: '0 0 30px rgba(0, 0, 0, 0.5), 0 0 10px rgba(0, 243, 255, 0.1)',
          }
        }
      }}
    >
      <DialogTitle sx={{
        m: 0,
        p: 2,
        bgcolor: 'rgba(0, 243, 255, 0.05)',
        borderBottom: '1px solid rgba(0, 243, 255, 0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
          <FileText size={20} color="#00f3ff" />
          <Typography sx={{
            fontFamily: 'Orbitron',
            fontWeight: 900,
            color: '#fff',
            letterSpacing: '0.1rem',
            fontSize: '1rem'
          }}>
            GENERATE SCAN REPORT
          </Typography>
        </Stack>
        <IconButton onClick={onClose} sx={{ color: 'rgba(255,255,255,0.5)', '&:hover': { color: '#ff003c' } }}>
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 3 }}>
        <Stack spacing={4}>
          <Box>
            <Typography sx={{
              color: '#00f3ff',
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
                    control={<Radio sx={{ color: 'rgba(0,243,255,0.2)', '&.Mui-checked': { color: '#00f3ff' } }} />}
                    label={
                      <Box>
                        <Typography sx={{ color: '#fff', fontSize: '0.85rem', fontWeight: 700, fontFamily: 'Orbitron' }}>Full Scan Report</Typography>
                        <Typography sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem' }}>Includes all findings: subdomains, endpoints, and vulnerabilities.</Typography>
                      </Box>
                    }
                  />
                  <FormControlLabel
                    value="vulnerability"
                    control={<Radio sx={{ color: 'rgba(0,243,255,0.2)', '&.Mui-checked': { color: '#00f3ff' } }} />}
                    label={
                      <Box>
                        <Typography sx={{ color: '#fff', fontSize: '0.85rem', fontWeight: 700, fontFamily: 'Orbitron' }}>Vulnerability Report</Typography>
                        <Typography sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem' }}>Focuses specifically on detected security vulnerabilities.</Typography>
                      </Box>
                    }
                  />
                </Stack>
              </RadioGroup>
            </FormControl>
          </Box>

          <Divider sx={{ borderColor: 'rgba(0, 243, 255, 0.1)' }} />

          <Box>
            <Typography sx={{
              color: '#00f3ff',
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
                  if (val !== 'enterprise') setIncludeAttackSurface(false);
                }}>
                  <FormControlLabel
                    value="default"
                    control={<Radio size="small" sx={{ color: 'rgba(0,243,255,0.2)', '&.Mui-checked': { color: '#00f3ff' } }} />}
                    label={<Typography sx={{ color: '#fff', fontSize: '0.8rem', fontWeight: 600 }}>Default</Typography>}
                  />
                  <FormControlLabel
                    value="modern"
                    control={<Radio size="small" sx={{ color: 'rgba(0,243,255,0.2)', '&.Mui-checked': { color: '#00f3ff' } }} />}
                    label={<Typography sx={{ color: '#fff', fontSize: '0.8rem', fontWeight: 600 }}>Modern (V2)</Typography>}
                  />
                  <FormControlLabel
                    value="enterprise"
                    control={<Radio size="small" sx={{ color: 'rgba(0,243,255,0.2)', '&.Mui-checked': { color: '#00f3ff' } }} />}
                    label={<Typography sx={{ color: '#fff', fontSize: '0.8rem', fontWeight: 600 }}>Enterprise</Typography>}
                  />
                </RadioGroup>
              </Box>

              <Stack spacing={1}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={ignoreInfoVuln}
                      onChange={(e) => setIgnoreInfoVuln(e.target.checked)}
                      sx={{ color: 'rgba(0,243,255,0.2)', '&.Mui-checked': { color: '#00f3ff' } }}
                    />
                  }
                  label={<Typography sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.8rem', fontWeight: 600 }}>Ignore Information Vulnerabilities</Typography>}
                />

                <FormControlLabel
                  control={
                    <Checkbox
                      checked={includeAttackSurface}
                      disabled={reportTemplate !== 'enterprise'}
                      onChange={(e) => setIncludeAttackSurface(e.target.checked)}
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
                        color: reportTemplate === 'enterprise' ? 'rgba(255,255,255,0.7)' : 'rgba(255,255,255,0.2)', 
                        fontSize: '0.8rem', 
                        fontWeight: 600,
                        transition: 'color 0.2s'
                      }}>
                        Include Attack Surface Map
                      </Typography>
                      {reportTemplate !== 'enterprise' && (
                        <Typography sx={{ color: 'rgba(0,243,255,0.3)', fontSize: '0.65rem' }}>Only available for Enterprise template</Typography>
                      )}
                    </Box>
                  }
                />
              </Stack>
            </Stack>
          </Box>
        </Stack>
      </DialogContent>

      <DialogActions sx={{ p: 3, bgcolor: 'rgba(0, 243, 255, 0.02)', borderTop: '1px solid rgba(0, 243, 255, 0.1)' }}>
        <Button
          onClick={onClose}
          sx={{
            color: 'rgba(255,255,255,0.5)',
            fontFamily: 'Orbitron',
            fontWeight: 800,
            fontSize: '0.7rem',
            mr: 'auto',
            '&:hover': { color: '#fff' }
          }}
        >
          CANCEL
        </Button>
        <Button
          onClick={handlePreview}
          sx={{
            color: '#00f3ff',
            fontFamily: 'Orbitron',
            fontWeight: 800,
            fontSize: '0.7rem',
            border: '1px solid rgba(0, 243, 255, 0.3)',
            px: 2,
            '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.05)', borderColor: '#00f3ff' }
          }}
        >
          PREVIEW
        </Button>
        <Button
          onClick={handleDownload}
          variant="contained"
          startIcon={<Download size={16} />}
          sx={{
            bgcolor: '#00f3ff',
            color: '#000',
            fontFamily: 'Orbitron',
            fontWeight: 900,
            fontSize: '0.7rem',
            px: 3,
            '&:hover': { bgcolor: '#00d8e4' }
          }}
        >
          GENERATE & DOWNLOAD
        </Button>
      </DialogActions>
    </Dialog>
  );
};
