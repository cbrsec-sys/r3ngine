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
  useTheme,
  alpha,
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
import { PageHeader } from '../../components/PageHeader';

export const ProjectsPage: React.FC = () => {
  const { data: projects, isLoading } = useProjects();
  const { mutate: deleteProject } = useDeleteProject();
  const [isAddModalOpen, setIsAddModalOpen] = React.useState(false);
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';

  const headerStyles = {
    color: isLight ? theme.palette.text.secondary : '#fff',
    fontWeight: 800,
    fontFamily: 'var(--r3-heading-font)',
    fontSize: '0.75rem',
    letterSpacing: 1,
    borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255, 255, 255, 0.05)'}`,
    py: 2
  };

  const handleDelete = (id: number, name: string) => {
    if (window.confirm(`Are you sure you want to delete ${name}? You won't be able to revert this, all targets and scan results also will be deleted!`)) {
      deleteProject(id);
    }
  };

  if (isLoading) return <LinearProgress color="primary" />;

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 0 }}>
        <PageHeader
          title="PROJECTS"
          subtitle="Central Control / Project Management"
        />
        <Button
          variant="contained"
          onClick={() => setIsAddModalOpen(true)}
          startIcon={<Plus size={18} />}
          sx={{
            bgcolor: isLight ? theme.palette.primary.main : 'rgba(0, 243, 255, 0.1)',
            color: isLight ? '#fff' : '#00f3ff',
            fontFamily: 'var(--r3-heading-font)',
            fontWeight: 800,
            border: isLight
              ? `1px solid ${theme.palette.primary.main}`
              : '1px solid rgba(0, 243, 255, 0.3)',
            px: 3,
            '&:hover': {
              bgcolor: isLight ? theme.palette.primary.dark : 'rgba(0, 243, 255, 0.2)',
              borderColor: isLight ? theme.palette.primary.dark : '#00f3ff',
            }
          }}
        >
          CREATE NEW PROJECT
        </Button>
      </Box>

      {/* Projects Table Card */}
      <Card sx={{
        bgcolor: isLight ? theme.palette.background.paper : 'rgba(10, 10, 25, 0.8)',
        backdropFilter: isLight ? 'none' : 'blur(10px)',
        border: `1px solid ${isLight ? theme.palette.divider : 'rgba(255, 255, 255, 0.05)'}`,
        borderRadius: 3,
        overflow: 'hidden',
        boxShadow: isLight ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
      }}>
        <TableContainer>
          <Table>
            <TableHead sx={{ bgcolor: isLight ? alpha(theme.palette.primary.main, 0.05) : 'rgba(50, 20, 80, 0.3)' }}>
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
                    '&:hover': { bgcolor: isLight ? alpha(theme.palette.primary.main, 0.04) : 'rgba(255, 255, 255, 0.03)' },
                    transition: 'all 0.2s'
                  }}
                >
                  <TableCell sx={{ borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255, 255, 255, 0.05)'}`, pl: 10 }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                      <Typography variant="body1" sx={{ fontWeight: 800, color: isLight ? theme.palette.text.primary : '#fff' }}>
                        {project.name}
                      </Typography>
                      <Typography variant="caption" sx={{ color: theme.palette.text.secondary, mt: 0.5 }}>
                        Created {project.insert_date_humanized || project.insert_date}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell sx={{ borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255, 255, 255, 0.05)'}` }}>
                    <Chip
                      label={project.slug}
                      size="small"
                      sx={{
                        bgcolor: alpha(theme.palette.primary.main, 0.08),
                        color: theme.palette.primary.main,
                        fontWeight: 700,
                        fontSize: '0.65rem',
                        borderRadius: 1,
                        height: 24,
                        border: `1px solid ${alpha(theme.palette.primary.main, 0.25)}`
                      }}
                    />
                  </TableCell>
                  <TableCell sx={{ borderBottom: `1px solid ${isLight ? theme.palette.divider : 'rgba(255, 255, 255, 0.05)'}`, textAlign: 'center' }}>
                    <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                      <Button
                        component={Link}
                        to={`/${project.slug}/dashboard`}
                        size="small"
                        variant="outlined"
                        startIcon={<ChevronRight size={14} />}
                        sx={{
                          borderColor: isLight ? alpha(theme.palette.primary.main, 0.4) : 'rgba(0, 243, 255, 0.3)',
                          color: theme.palette.primary.main,
                          fontFamily: 'var(--r3-heading-font)',
                          fontSize: '0.65rem',
                          fontWeight: 700,
                          '&:hover': {
                            borderColor: theme.palette.primary.main,
                            bgcolor: alpha(theme.palette.primary.main, 0.05)
                          }
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

