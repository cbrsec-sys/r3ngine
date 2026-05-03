import React from 'react';
import {
  Box,
  Card,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Button,
  LinearProgress,
  Tooltip
} from '@mui/material';
import {
  Folder,
  Plus,
  Trash2,
  ChevronRight,
  ExternalLink
} from 'lucide-react';
import { useProjects, useDeleteProject } from './api';
import { Link } from '@tanstack/react-router';
import { AddProjectModal } from './components/AddProjectModal';

export const ProjectsPage: React.FC = () => {
  const { data: projects, isLoading } = useProjects();
  const { mutate: deleteProject } = useDeleteProject();
  const [isAddModalOpen, setIsAddModalOpen] = React.useState(false);

  const handleDelete = (id: number, name: string) => {
    if (window.confirm(`Are you sure you want to delete ${name}? You won't be able to revert this, all targets and scan results also will be deleted!`)) {
      deleteProject(id);
    }
  };

  if (isLoading) return <LinearProgress sx={{ bgcolor: 'rgba(0, 243, 255, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: '#00f3ff' } }} />;

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontFamily: 'Orbitron', fontWeight: 900, color: '#fff', letterSpacing: 2 }}>
            ALL PROJECTS
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(0, 243, 255, 0.6)', fontFamily: 'Orbitron', letterSpacing: 1 }}>
            Central Control / Project Management
          </Typography>
        </Box>
        <Button
          variant="contained"
          onClick={() => setIsAddModalOpen(true)}
          startIcon={<Plus size={18} />}
          sx={{
            bgcolor: 'rgba(0, 243, 255, 0.1)',
            color: '#00f3ff',
            fontFamily: 'Orbitron',
            fontWeight: 800,
            border: '1px solid rgba(0, 243, 255, 0.3)',
            px: 3,
            '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.2)', borderColor: '#00f3ff' }
          }}
        >
          CREATE NEW PROJECT
        </Button>
      </Box>

      {/* Projects Table Card */}
      <Card sx={{
        bgcolor: 'rgba(10, 10, 25, 0.8)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        borderRadius: 3,
        overflow: 'hidden'
      }}>
        <TableContainer>
          <Table>
            <TableHead sx={{ bgcolor: 'rgba(50, 20, 80, 0.3)' }}>
              <TableRow>
                <TableCell sx={{ ...headerStyles, pl: 10 }}>PROJECT NAME</TableCell>
                <TableCell sx={headerStyles}>SLUG</TableCell>
                <TableCell sx={{ ...headerStyles, textAlign: 'center' }}>ACTIONS</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {projects?.map((project) => (
                <TableRow
                  key={project.id}
                  sx={{
                    '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.03)' },
                    transition: 'all 0.2s'
                  }}
                >
                  <TableCell sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', pl: 10 }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                      <Typography variant="body1" sx={{ fontWeight: 800, color: '#fff' }}>
                        {project.name}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.4)', mt: 0.5 }}>
                        Created {project.insert_date_humanized || project.insert_date}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                    <Chip
                      label={project.slug}
                      size="small"
                      sx={{
                        bgcolor: 'rgba(0, 243, 255, 0.05)',
                        color: '#00f3ff',
                        fontWeight: 700,
                        fontSize: '0.65rem',
                        borderRadius: 1,
                        height: 24,
                        border: '1px solid rgba(0, 243, 255, 0.2)'
                      }}
                    />
                  </TableCell>
                  <TableCell sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', textAlign: 'center' }}>
                    <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                      <Button
                        component={Link}
                        to={`/${project.slug}/dashboard`}
                        size="small"
                        variant="outlined"
                        startIcon={<ChevronRight size={14} />}
                        sx={{
                          borderColor: 'rgba(0, 243, 255, 0.3)',
                          color: '#00f3ff',
                          fontFamily: 'Orbitron',
                          fontSize: '0.65rem',
                          fontWeight: 700,
                          '&:hover': { borderColor: '#00f3ff', bgcolor: 'rgba(0, 243, 255, 0.05)' }
                        }}
                      >
                        OPEN_DASHBOARD
                      </Button>
                      <IconButton
                        onClick={() => handleDelete(project.id, project.name)}
                        size="small"
                        sx={{
                          color: '#ff003c',
                          bgcolor: 'rgba(255, 0, 60, 0.05)',
                          borderRadius: 1,
                          '&:hover': { bgcolor: 'rgba(255, 0, 60, 0.15)' }
                        }}
                      >
                        <Trash2 size={16} />
                      </IconButton>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <AddProjectModal
        open={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
      />
    </Box>
  );
};

const headerStyles = {
  color: '#fff',
  fontWeight: 800,
  fontFamily: 'Orbitron',
  fontSize: '0.75rem',
  letterSpacing: 1,
  borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
  py: 2
};
