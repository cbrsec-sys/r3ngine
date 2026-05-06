import React from 'react';
import { 
  Box, 
  Typography, 
  Grid,
  Card,
  CardContent,
  Avatar
} from '@mui/material';
import { Users, User } from 'lucide-react';
import { TacticalPanel } from '../../../../components/TacticalPanel';

interface Employee {
  id: number;
  name: string;
  designation?: string;
}

interface EmployeeSectionProps {
  employees: Employee[];
}

export const EmployeeSection: React.FC<EmployeeSectionProps> = ({ employees }) => {
  if (!employees || employees.length === 0) return null;

  return (
    <TacticalPanel title="DISCOVERED EMPLOYEES" icon={<Users size={18} />}>
      <Grid container spacing={2}>
        {employees.map((employee) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={employee.id}>
            <Card sx={{ 
              background: 'rgba(255, 255, 255, 0.03)', 
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: 0,
              '&:hover': {
                borderColor: 'primary.main',
                background: 'rgba(255, 255, 255, 0.05)'
              }
            }}>
              <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, '&:last-child': { pb: 2 } }}>
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
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </TacticalPanel>
  );
};
