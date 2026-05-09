import React from 'react';
import { 
  Box, 
  Typography, 
  Grid,
  Card,
  CardContent,
  Avatar
} from '@mui/material';
import { Users, User, ExternalLink } from 'lucide-react';
import { TacticalPanel } from '../../../../components/TacticalPanel';

interface Employee {
  id: number;
  name: string;
  designation?: string;
  metadata?: {
    maigret?: {
      site: string;
      url: string;
    }[];
  };
}

interface EmployeeSectionProps {
  employees: Employee[];
}

export const EmployeeSection: React.FC<EmployeeSectionProps> = ({ employees }) => {
  if (!employees || employees.length === 0) return null;

  return (
    <TacticalPanel title="DISCOVERED EMPLOYEES & USERNAMES" icon={<Users size={18} />}>
      <Grid container spacing={2}>
        {employees.map((employee) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={employee.id}>
            <Card sx={{ 
              background: 'rgba(255, 255, 255, 0.03)', 
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: 0,
              height: '100%',
              '&:hover': {
                borderColor: 'primary.main',
                background: 'rgba(255, 255, 255, 0.05)'
              }
            }}>
              <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, '&:last-child': { pb: 2 } }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Avatar sx={{ bgcolor: 'primary.dark', borderRadius: 0 }}>
                    <User size={20} />
                  </Avatar>
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                      {employee.name}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      {employee.designation || 'Position unknown'}
                    </Typography>
                  </Box>
                </Box>
                
                {employee.metadata?.maigret && employee.metadata.maigret.length > 0 && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" sx={{ color: 'primary.light', fontWeight: 'bold', mb: 1, display: 'block' }}>
                      SOCIAL PROFILES
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {employee.metadata.maigret.map((profile, idx) => (
                        <Box 
                          key={idx}
                          component="a"
                          href={profile.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          sx={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: 0.5,
                            fontSize: '10px', 
                            px: 1, 
                            py: 0.5, 
                            background: 'rgba(33, 150, 243, 0.1)', 
                            color: 'info.light',
                            border: '1px solid rgba(33, 150, 243, 0.3)',
                            textDecoration: 'none',
                            '&:hover': {
                              background: 'rgba(33, 150, 243, 0.2)',
                              borderColor: 'info.main'
                            }
                          }}
                        >
                          {profile.site}
                          <ExternalLink size={10} />
                        </Box>
                      ))}
                    </Box>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </TacticalPanel>
  );
};
