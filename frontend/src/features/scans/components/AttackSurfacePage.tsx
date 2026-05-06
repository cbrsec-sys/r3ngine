import React from 'react';
import { useParams } from '@tanstack/react-router';
import { Box, Typography, Button, Stack } from '@mui/material';
import { ChevronLeft } from 'lucide-react';
import { Link as RouterLink } from '@tanstack/react-router';
import { AttackSurfaceTab } from './AttackSurfaceTab';

export const AttackSurfacePage: React.FC = () => {
  const { projectSlug, scanId } = useParams({ strict: false }) as any;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 1 }}>
            <Button
              component={RouterLink}
              to={`/${projectSlug}/scans`}
              startIcon={<ChevronLeft size={16} />}
              sx={{
                color: 'rgba(255,255,255,0.5)',
                fontFamily: 'Orbitron',
                fontSize: '0.7rem',
                '&:hover': { color: '#00f3ff', bgcolor: 'transparent' }
              }}
            >
              BACK TO SCANS
            </Button>
          </Stack>
          {/* <Typography variant="h5" sx={{ fontWeight: 900, fontFamily: 'Orbitron', color: '#fff', letterSpacing: 2 }}>
            ATTACK SURFACE MAP
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', fontFamily: 'Orbitron', fontSize: '0.7rem' }}>
            VISUALIZING INFRASTRUCTURE NODES AND RELATIONSHIPS FOR SCAN #{scanId}
          </Typography> */}
        </Box>
      </Box>

      <AttackSurfaceTab
        projectSlug={projectSlug}
        scanId={parseInt(scanId)}
      />
    </Box>
  );
};
