import React from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow,
  Chip,
  IconButton,
  Tooltip
} from '@mui/material';
import { Eye, ExternalLink, ShieldAlert } from 'lucide-react';
import { Link } from '@tanstack/react-router';
import type { Discovery } from '../api';

export const DiscoveryTable: React.FC<{ discoveries: Discovery[], projectSlug: string }> = ({ discoveries, projectSlug }) => {
  const getTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'subdomain': return '#00ff62';
      case 'ip': return '#00f3ff';
      case 'vhost': return '#7000ff';
      case 'directory': return '#ff00ff';
      case 'login': return '#ff9f00';
      case 'status_change': return '#ff003c';
      default: return '#fff';
    }
  };

  return (
    <Card sx={{ 
      bgcolor: 'rgba(5, 5, 15, 0.6)', 
      backdropFilter: 'blur(10px)', 
      border: '1px solid rgba(255, 255, 255, 0.05)',
      mt: 3
    }}>
      <CardContent sx={{ p: 0 }}>
        <Box sx={{ p: 2, borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: 2 }}>
          <ShieldAlert size={20} color="#00f3ff" />
          <Typography variant="h6" sx={{ fontSize: '0.9rem', fontWeight: 900, fontFamily: 'Orbitron', letterSpacing: 1 }}>
            RECENT_DISCOVERIES_LOG
          </Typography>
        </Box>
        <TableContainer>
          <Table sx={{ minWidth: 650 }}>
            <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.02)' }}>
              <TableRow>
                <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontWeight: 700, fontSize: '0.7rem', textTransform: 'uppercase' }}>Type</TableCell>
                <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontWeight: 700, fontSize: '0.7rem', textTransform: 'uppercase' }}>Target</TableCell>
                <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontWeight: 700, fontSize: '0.7rem', textTransform: 'uppercase' }}>Discovery</TableCell>
                <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontWeight: 700, fontSize: '0.7rem', textTransform: 'uppercase' }}>Details</TableCell>
                <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontWeight: 700, fontSize: '0.7rem', textTransform: 'uppercase' }}>Date</TableCell>
                <TableCell sx={{ color: 'rgba(255,255,255,0.5)', fontWeight: 700, fontSize: '0.7rem', textTransform: 'uppercase', textAlign: 'right' }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {discoveries.map((discovery) => {
                const color = getTypeColor(discovery.discovery_type);
                return (
                  <TableRow key={discovery.id} sx={{ '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' }, borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                    <TableCell>
                      <Chip 
                        label={discovery.discovery_type.toUpperCase()} 
                        size="small" 
                        sx={{ 
                          height: 20, 
                          fontSize: '0.6rem', 
                          fontWeight: 900, 
                          bgcolor: `${color}15`, 
                          color: color,
                          border: `1px solid ${color}33`,
                          borderRadius: 0.5
                        }} 
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600, color: '#fff' }}>
                        {discovery.domain_name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.8rem' }}>
                        {discovery.content.name || discovery.content.url || 'N/A'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        {discovery.content.status && (
                          <Chip 
                            label={discovery.content.status} 
                            size="small" 
                            variant="outlined" 
                            sx={{ height: 18, fontSize: '0.6rem', color: 'rgba(255,255,255,0.5)' }} 
                          />
                        )}
                        {discovery.content.title && (
                          <Typography variant="caption" sx={{ opacity: 0.4 }}>
                            {discovery.content.title.substring(0, 30)}...
                          </Typography>
                        )}
                      </Box>
                    </TableCell>
                    <TableCell sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem' }}>
                      {new Date(discovery.discovered_at).toLocaleString()}
                    </TableCell>
                    <TableCell align="right">
                      {discovery.scan_history_id && (
                        <Tooltip title="View Scan History">
                          <IconButton 
                            component={Link} 
                            to={`/projects/${projectSlug}/scans/${discovery.scan_history_id}`}
                            size="small" 
                            sx={{ color: 'primary.main', '&:hover': { bgcolor: 'primary.main', color: '#000' } }}
                          >
                            <Eye size={16} />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
};
