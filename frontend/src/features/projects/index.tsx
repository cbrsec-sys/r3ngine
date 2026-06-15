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
  Tooltip,
  useTheme
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
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';

  const handleDelete = (id: number, name: string) => {
    if (window.confirm(`Are you sure you want to delete ${name}? You won't be able to revert this, all targets and scan results also will be deleted!`)) {
      deleteProject(id);
    }
  };

  if (isLoading) return <LinearProgress sx={{ bgcolor: isLight ? 'rgba(2, 132, 199, 0.1)' : 'rgba(0, 243, 255, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: isLight ? 'primary.main' : '#00f3ff' } }} />;

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontFamily: 'Orbitron', fontWeight: 900, color: 'text.primary', letterSpacing: 2 }}>
            PROJECTS
          </Typography>
          <Typography variant="caption" sx={{ color: isLight ? 'primary.main' : 'rgba(0, 243, 255, 0.6)', fontFamily: 'Orbitron', letterSpacing: 1 }}>
            Central Control / Project Management
          </Typography>
        </Box>
        <Button
          variant="contained"
          onClick={() => setIsAddModalOpen(true)}
          startIcon={<Plus size={18} />}
          sx={{
            bgcolor: isLight ? 'primary.main' : 'rgba(0, 243, 255, 0.1)',
            color: isLight ? '#fff' : '#00f3ff',
            fontFamily: 'Orbitron',
            fontWeight: 800,
            border: isLight ? 'none' : '1px solid rgba(0, 243, 255, 0.3)',
            px: 3,
            '&:hover': { bgcolor: isLight ? 'primary.dark' : 'rgba(0, 243, 255, 0.2)', borderColor: isLight ? 'none' : '#00f3ff' }
          }}
        >
          CREATE NEW PROJECT
        </Button>
      </Box>

      {/* Projects Table Card */}
      <Card sx={{
        bgcolor: isLight ? 'background.paper' : 'rgba(10, 10, 25, 0.8)',
        backdropFilter: 'blur(10px)',
        border: isLight ? '1px solid rgba(0, 0, 0, 0.08)' : '1px solid rgba(255, 255, 255, 0.05)',
        borderRadius: 3,
        overflow: 'hidden'
      }}>
        <TableContainer>
          <Table>
            <TableHead sx={{ bgcolor: isLight ? 'action.hover' : 'rgba(50, 20, 80, 0.3)' }}>
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
                     '&:hover': { bgcolor: 'action.hover' },
                     transition: 'all 0.2s'
                   }}
                >
                  <TableCell sx={{ borderBottom: isLight ? '1px solid rgba(0, 0, 0, 0.08)' : '1px solid rgba(255, 255, 255, 0.05)', pl: 10 }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                      <Typography variant="body1" sx={{ fontWeight: 800, color: 'text.primary' }}>
                        {project.name}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.5 }}>
                        Created {project.insert_date_humanized || project.insert_date}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell sx={{ borderBottom: isLight ? '1px solid rgba(0, 0, 0, 0.08)' : '1px solid rgba(255, 255, 255, 0.05)' }}>
                    <Chip
                      label={project.slug}
                      size="small"
                      sx={{
                        bgcolor: isLight ? 'rgba(2, 132, 199, 0.05)' : 'rgba(0, 243, 255, 0.05)',
                        color: isLight ? 'primary.main' : '#00f3ff',
                        fontWeight: 700,
                        fontSize: '0.65rem',
                        borderRadius: 1,
                        height: 24,
                        border: isLight ? '1px solid rgba(2, 132, 199, 0.2)' : '1px solid rgba(0, 243, 255, 0.2)'
                      }}
                    />
                  </TableCell>
                  <TableCell sx={{ borderBottom: isLight ? '1px solid rgba(0, 0, 0, 0.08)' : '1px solid rgba(255, 255, 255, 0.05)', textAlign: 'center' }}>
                    <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                      <Button
                        component={Link}
                        to={`/${project.slug}/dashboard`}
                        size="small"
                        variant="outlined"
                        startIcon={<ChevronRight size={14} />}
                        sx={{
                          borderColor: isLight ? 'rgba(2, 132, 199, 0.3)' : 'rgba(0, 243, 255, 0.3)',
                          color: isLight ? 'primary.main' : '#00f3ff',
                          fontFamily: 'Orbitron',
                          fontSize: '0.65rem',
                          fontWeight: 700,
                          '&:hover': { borderColor: isLight ? 'primary.main' : '#00f3ff', bgcolor: isLight ? 'rgba(2, 132, 199, 0.05)' : 'rgba(0, 243, 255, 0.05)' }
                        }}
                      >
                        OPEN DASHBOARD
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
  color: 'text.primary',
  fontWeight: 800,
  fontFamily: 'Orbitron',
  fontSize: '0.75rem',
  letterSpacing: 1,
  borderBottom: '1px solid',
  borderColor: 'divider',
  py: 2
};
