import React from 'react';
import { Box, InputBase, Stack, Button } from '@mui/material';
import { Search, Maximize, RefreshCw, Download, Sparkles } from 'lucide-react';
import { useGraphStore } from '../../../store/useGraphStore';

interface Props {
  searchQuery: string;
  onSearch: (query: string) => void;
  onResetZoom: () => void;
  onRefreshLayout: () => void;
  onExport: () => void;
}

export const GraphControlPanel: React.FC<Props> = ({
  searchQuery,
  onSearch,
  onResetZoom,
  onRefreshLayout,
  onExport
}) => {
  return (
    <Box sx={{ p: 2, display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
       <Box sx={{ 
          display: 'flex', 
          bgcolor: 'rgba(255,255,255,0.03)', 
          borderRadius: 1, 
          border: '1px solid rgba(0, 243, 255, 0.3)',
          width: '400px',
          boxShadow: '0 0 10px rgba(0, 243, 255, 0.1)',
          alignItems: 'center'
       }}>
          <Box sx={{ p: 1, color: '#00f3ff' }}><Sparkles size={16} /></Box>
          <InputBase 
            placeholder="Ask AI: e.g., 'Show me critical endpoints'" 
            value={searchQuery}
            onChange={(e) => onSearch(e.target.value)}
            sx={{ flex: 1, color: '#fff', fontSize: '0.8rem', fontStyle: 'italic' }} 
          />
       </Box>
       <Stack direction="row" spacing={1}>
          <Button size="small" startIcon={<Maximize size={14} />} onClick={onResetZoom} sx={{ bgcolor: 'rgba(33,150,243,0.1)', color: '#2196f3', fontSize: '0.7rem', fontWeight: 800 }}>RESET ZOOM</Button>
          <Button size="small" startIcon={<RefreshCw size={14} />} onClick={onRefreshLayout} sx={{ bgcolor: 'rgba(112,0,255,0.1)', color: '#7000ff', fontSize: '0.7rem', fontWeight: 800 }}>RELAYOUT</Button>
          <Button size="small" startIcon={<Download size={14} />} onClick={onExport} sx={{ bgcolor: 'rgba(0,255,170,0.1)', color: '#00ffaa', fontSize: '0.7rem', fontWeight: 800 }}>EXPORT PNG</Button>
       </Stack>
    </Box>
  );
};
