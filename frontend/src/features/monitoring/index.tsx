import React from 'react';
import { useParams } from '@tanstack/react-router';
import { 
  Activity, 
  Globe, 
  Link as LinkIcon, 
  Lock, 
  Monitor,
  Search,
  ExternalLink,
  Clock,
  ChevronRight
} from 'lucide-react';

import { KpiCard } from '../../components/KpiCard';
import { TacticalPanel } from '../../components/TacticalPanel';
import { useMonitoringDiscoveries, useMonitoringStats } from './api/index';
import { Grid, Container, Box, Typography } from '@mui/material';
import { formatDiscoveryContent } from './utils/formatters';
import { Target, Shield } from 'lucide-react';

export const MonitoringPage: React.FC = () => {
  const { projectSlug } = useParams({ from: '/$projectSlug/monitoring' });

  const { data: stats, isLoading: statsLoading } = useMonitoringStats(projectSlug);
  const { data: discoveries, isLoading: discoveriesLoading } = useMonitoringDiscoveries(projectSlug);

  const kpis = [
    {
      title: 'TOTAL DISCOVERIES',
      value: stats?.total_discoveries || 0,
      icon: Monitor,
      color: '#00f3ff',
      subtitle: 'All Monitored Assets'
    },
    {
      title: 'SUBDOMAINS',
      value: stats?.subdomain_discoveries || 0,
      icon: Globe,
      color: '#7000ff',
      subtitle: 'Newly Detected Hosts'
    },
    {
      title: 'ENDPOINTS',
      value: stats?.endpoint_discoveries || 0,
      icon: LinkIcon,
      color: '#ff00f7',
      subtitle: 'New Directories/Files'
    },
    {
      title: 'LOGINS',
      value: stats?.login_discoveries || 0,
      icon: Lock,
      color: '#ffae00',
      subtitle: 'Auth Portals Found'
    }
  ];

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Top Header Row - MUI Pattern */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'between', mb: 4, width: '100%' }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h5" sx={{
            fontWeight: 900,
            fontFamily: 'Orbitron',
            letterSpacing: 3,
            color: '#fff',
            textTransform: 'uppercase'
          }}>
            Continuous Monitoring Dashboard
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography sx={{ fontSize: '10px', fontWeight: 800, color: 'text.secondary', letterSpacing: 2 }}>DASHBOARD</Typography>
          <ChevronRight size={12} style={{ color: '#ff00f7' }} />
          <Typography sx={{ fontSize: '10px', fontWeight: 800, color: '#fff', letterSpacing: 2 }}>MONITORING</Typography>
        </Box>
      </Box>

      {/* KPI Stats Grid - MUI Grid for stability */}
      <Grid container spacing={3} sx={{ mb: 6 }}>
        {kpis.map((kpi, index) => (
          <Grid key={index} xs={12} sm={6} md={3}>
            <KpiCard 
              title={kpi.title}
              value={kpi.value}
              icon={kpi.icon}
              color={kpi.color}
              subtitle={statsLoading ? 'Loading...' : kpi.subtitle}
            />
          </Grid>
        ))}
      </Grid>

      {/* Main Tactical Panel - Legacy Structural Mapping */}
      <TacticalPanel className="mt-4">
        <Box sx={{ p: 1 }}>
          <Typography variant="h6" sx={{ 
            fontSize: '0.85rem', 
            fontWeight: 900, 
            textTransform: 'uppercase', 
            letterSpacing: 4, 
            color: '#00f3ff', 
            fontFamily: 'Orbitron',
            mb: 4,
            px: 2
          }}>
            Recent Discoveries
          </Typography>

          {/* Filters Bar - Styled after Image 7 */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3, px: 2, gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Typography sx={{ fontSize: '10px', fontWeight: 900, color: 'rgba(255,255,255,0.4)', letterSpacing: 2 }}>RESULTS :</Typography>
              <select style={{ 
                background: 'rgba(5, 5, 15, 0.6)', 
                border: '1px solid rgba(255, 255, 255, 0.1)', 
                color: '#fff', 
                fontSize: '11px', 
                fontWeight: 700, 
                borderRadius: '50px', 
                padding: '6px 20px', 
                outline: 'none',
                cursor: 'pointer'
              }}>
                <option>25</option>
                <option>50</option>
                <option>100</option>
              </select>
            </Box>
            
            <Box sx={{ position: 'relative', flex: 1, maxWidth: 400 }}>
              <input 
                placeholder="Search discoveries..." 
                style={{ 
                  width: '100%',
                  background: 'rgba(5, 5, 15, 0.6)', 
                  border: '1px solid rgba(255, 255, 255, 0.1)', 
                  color: '#fff', 
                  fontSize: '11px', 
                  borderRadius: '50px', 
                  padding: '10px 45px 10px 20px', 
                  outline: 'none'
                }}
              />
              <Search size={16} style={{ position: 'absolute', right: 15, top: '50%', transform: 'translateY(-50%)', color: 'rgba(255,255,255,0.3)' }} />
            </Box>
          </Box>

          {/* Table Container - MUI Pattern */}
          <Box sx={{ overflowX: 'auto', px: 1 }}>
            <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 8px' }}>
              <thead>
                <tr>
                  <th style={{ padding: '8px 16px', textAlign: 'center', width: 40 }}>
                    <Box sx={{ width: 16, height: 16, border: '1px solid rgba(255,255,255,0.2)', borderRadius: '4px' }} />
                  </th>
                  {['TYPE', 'TARGET', 'DISCOVERY', 'DETAILS', 'DATE', 'ACTION'].map((head) => (
                    <th key={head} style={{ 
                      padding: '8px 16px', 
                      textAlign: 'left', 
                      fontSize: '11px', 
                      fontWeight: 900, 
                      color: 'rgba(255,255,255,0.4)', 
                      letterSpacing: 2,
                      fontFamily: 'Orbitron'
                    }}>
                      {head}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {discoveriesLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td colSpan={7} style={{ height: 60, background: 'rgba(255,255,255,0.02)', borderRadius: 8 }} />
                    </tr>
                  ))
                ) : discoveries?.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ padding: '60px', textAlign: 'center', background: 'rgba(255,255,255,0.02)', borderRadius: 8 }}>
                      <Typography sx={{ fontSize: '11px', fontWeight: 900, color: 'rgba(255,255,255,0.2)', fontFamily: 'Orbitron', letterSpacing: 2 }}>
                        NO DATA AVAILABLE IN TABLE
                      </Typography>
                    </td>
                  </tr>
                ) : (
                  discoveries?.map((discovery) => (
                    <tr key={discovery.id} style={{ background: 'rgba(255,255,255,0.02)', transition: 'all 0.2s' }}>
                      <td style={{ padding: '12px 16px', textAlign: 'center', borderTopLeftRadius: 8, borderBottomLeftRadius: 8 }}>
                        <Box sx={{ width: 16, height: 16, border: '1px solid rgba(255,255,255,0.2)', borderRadius: '4px', margin: 'auto' }} />
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <Box sx={{ 
                          display: 'inline-block',
                          px: 1.5, 
                          py: 0.5, 
                          borderRadius: '50px', 
                          fontSize: '9px', 
                          fontWeight: 900, 
                          bgcolor: discovery.discovery_type === 'subdomain' ? 'rgba(52, 211, 153, 0.1)' : 'rgba(34, 211, 238, 0.1)',
                          color: discovery.discovery_type === 'subdomain' ? '#10b981' : '#00f3ff',
                          border: `1px solid ${discovery.discovery_type === 'subdomain' ? 'rgba(52, 211, 153, 0.2)' : 'rgba(34, 211, 238, 0.2)'}`,
                          letterSpacing: 1
                        }}>
                          {discovery.discovery_type.toUpperCase()}
                        </Box>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                          <Typography sx={{ fontSize: '13px', fontWeight: 800, color: '#fff', fontFamily: 'monospace' }}>{discovery.domain_name}</Typography>
                          <Typography sx={{ fontSize: '9px', fontWeight: 700, color: 'rgba(0, 243, 255, 0.5)', display: 'flex', alignItems: 'center', gap: 0.5, cursor: 'pointer', '&:hover': { color: '#00f3ff' } }}>
                            RECENT SCAN <ExternalLink size={10} />
                          </Typography>
                        </Box>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <Typography sx={{ 
                          fontSize: '11px', 
                          color: 'rgba(255,255,255,0.5)', 
                          fontFamily: 'monospace', 
                          maxWidth: 250, 
                          overflow: 'hidden', 
                          textOverflow: 'ellipsis', 
                          whiteSpace: 'nowrap' 
                        }}>
                          {formatDiscoveryContent(discovery)}
                        </Typography>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <Box sx={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          gap: 1, 
                          px: 2, 
                          py: 0.8, 
                          border: '1px solid rgba(0, 243, 255, 0.2)', 
                          borderRadius: '4px',
                          color: '#00f3ff',
                          fontSize: '9px',
                          fontWeight: 800,
                          cursor: 'pointer',
                          width: 'fit-content',
                          '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.05)' }
                        }}>
                          <Activity size={12} />
                          DETAILS
                        </Box>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <Box sx={{ 
                          px: 1.5, 
                          py: 0.5, 
                          borderRadius: '50px', 
                          fontSize: '9px', 
                          fontWeight: 700, 
                          color: 'rgba(255,255,255,0.4)',
                          bgcolor: 'rgba(255,255,255,0.03)',
                          border: '1px solid rgba(255,255,255,0.05)',
                          width: 'fit-content'
                        }}>
                          {new Date(discovery.discovered_at).toLocaleDateString()}
                        </Box>
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', borderTopRightRadius: 8, borderBottomRightRadius: 8 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 1.5 }}>
                          <Box sx={{ 
                            px: 2, 
                            py: 0.8, 
                            border: '1px solid rgba(0, 243, 255, 0.5)', 
                            borderRadius: '4px',
                            color: '#00f3ff',
                            fontSize: '9px',
                            fontWeight: 900,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1,
                            '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.1)' }
                          }}>
                            <Target size={12} />
                            SUMMARY
                          </Box>
                          <ChevronRight size={18} style={{ color: 'rgba(255,255,255,0.2)' }} />
                        </Box>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </Box>
          
          {/* Footer - Legacy Pagination Layout */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 4, px: 2, pt: 3, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
            <Box sx={{ px: 2.5, py: 1.2, bgcolor: 'rgba(5, 5, 15, 0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 2 }}>
              <Typography sx={{ fontSize: '10px', fontWeight: 900, color: 'rgba(255,255,255,0.3)', letterSpacing: 1.5 }}>
                SHOWING <Box component="span" sx={{ color: '#00f3ff' }}>0</Box> TO <Box component="span" sx={{ color: '#00f3ff' }}>0</Box> OF <Box component="span" sx={{ color: '#00f3ff' }}>0</Box> ENTRIES
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Box sx={{ width: 36, height: 36, borderRadius: '50%', border: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.2)', cursor: 'not-allowed' }}>
                <ChevronRight size={18} style={{ transform: 'rotate(180deg)' }} />
              </Box>
              <Box sx={{ width: 36, height: 36, borderRadius: '50%', border: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.2)', cursor: 'not-allowed' }}>
                <ChevronRight size={18} />
              </Box>
            </Box>
          </Box>
        </Box>
      </TacticalPanel>
    </Container>
  );
};

