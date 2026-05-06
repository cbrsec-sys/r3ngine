import React from 'react';
import { Box, Typography, Checkbox, IconButton, Tooltip, Paper, Stack } from '@mui/material';
import { AlertOctagon, Trash2, ExternalLink, MoreVertical } from 'lucide-react';
import type { TodoNote } from '../types/index';

interface TodoItemProps {
  note: TodoNote;
  onToggleStatus: (id: number) => void;
  onToggleImportant: (id: number) => void;
  onDelete: (id: number) => void;
  onClick: (note: TodoNote) => void;
}

export const TodoItem: React.FC<TodoItemProps> = ({ note, onToggleStatus, onToggleImportant, onDelete, onClick }) => {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        mb: 2,
        bgcolor: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        borderRadius: '12px',
        transition: 'all 0.3s ease',
        '&:hover': {
          bgcolor: 'rgba(255, 255, 255, 0.04)',
          borderColor: note.is_important ? 'rgba(255, 0, 60, 0.3)' : 'rgba(0, 243, 255, 0.3)',
          transform: 'translateX(4px)'
        }
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
        <Checkbox 
          checked={note.is_done}
          onChange={() => onToggleStatus(note.id)}
          sx={{ 
            p: 0,
            mt: 0.5,
            color: 'rgba(255, 255, 255, 0.2)',
            '&.Mui-checked': { color: '#00ff62' }
          }}
        />
        
        <Box sx={{ flexGrow: 1, cursor: 'pointer' }} onClick={() => onClick(note)}>
          <Typography sx={{ 
            fontSize: '0.9rem', 
            fontWeight: 700, 
            color: note.is_done ? 'rgba(255,255,255,0.3)' : '#fff',
            textDecoration: note.is_done ? 'line-through' : 'none',
            mb: 0.5
          }}>
            {note.title}
          </Typography>
          
          {(note.domain_name || note.subdomain_name) && (
            <Typography sx={{ 
              fontSize: '0.65rem', 
              color: '#00f3ff', 
              fontWeight: 800, 
              fontFamily: 'Orbitron',
              mb: 1
            }}>
              {note.domain_name} {note.subdomain_name ? `> ${note.subdomain_name}` : ''}
            </Typography>
          )}
          
          <Typography sx={{ 
            fontSize: '0.75rem', 
            color: note.is_done ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.5)',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden'
          }}>
            {note.description}
          </Typography>
        </Box>

        <Stack direction="row" spacing={1}>
          {note.is_important && (
            <Tooltip title="Important">
              <Box sx={{ color: '#ff003c' }}>
                <AlertOctagon size={18} />
              </Box>
            </Tooltip>
          )}
          
          <IconButton size="small" onClick={() => onToggleImportant(note.id)} sx={{ color: 'rgba(255,255,255,0.3)', '&:hover': { color: '#ff003c' } }}>
            <AlertOctagon size={16} />
          </IconButton>
          
          <IconButton size="small" onClick={() => onDelete(note.id)} sx={{ color: 'rgba(255,255,255,0.3)', '&:hover': { color: '#ff003c' } }}>
            <Trash2 size={16} />
          </IconButton>
        </Stack>
      </Box>
    </Paper>
  );
};
