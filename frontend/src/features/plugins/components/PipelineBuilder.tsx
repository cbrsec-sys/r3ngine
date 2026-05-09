import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  Tooltip,
  CircularProgress
} from '@mui/material';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors
} from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { 
  ChevronRight, 
  GripVertical, 
  Shield, 
  Cpu,
  Layers
} from 'lucide-react';
import type { Plugin } from '../api/pluginsApi';
import { useUpdatePluginWeight } from '../api/pluginsApi';

interface Props {
  plugins: Plugin[];
}

const CORE_STEPS = [
  'SubdomainDiscovery',
  'PortScan',
  'FetchURL',
  'VulnerabilityScan',
  'Reporting'
];

const SortableItem = ({ plugin }: { plugin: Plugin }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: plugin.slug });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 100 : 1,
    position: 'relative' as const,
  };

  return (
    <Box
      ref={setNodeRef}
      style={style}
      sx={{
        p: 1.5,
        mb: 1,
        bgcolor: isDragging ? 'rgba(0, 243, 255, 0.15)' : 'rgba(255, 255, 255, 0.02)',
        border: '1px solid',
        borderColor: isDragging ? '#00f3ff' : 'rgba(255, 255, 255, 0.05)',
        borderRadius: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        transition: '0.2s',
        '&:hover': {
          bgcolor: 'rgba(255, 255, 255, 0.05)',
          borderColor: 'rgba(255, 255, 255, 0.1)'
        }
      }}
    >
      <Box {...attributes} {...listeners} sx={{ cursor: 'grab', display: 'flex', color: 'rgba(255,255,255,0.2)' }}>
        <GripVertical size={18} />
      </Box>
      <Box sx={{ flexGrow: 1 }}>
        <Typography sx={{ fontSize: '0.85rem', fontWeight: 800, color: '#fff', fontFamily: 'Orbitron' }}>
          {plugin.name.toUpperCase()}
        </Typography>
        <Typography sx={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', fontWeight: 600 }}>
          VERSION: {plugin.version}
        </Typography>
      </Box>
      <Tooltip title="Plugin Extension">
        <Layers size={14} color="#00ffaa" />
      </Tooltip>
    </Box>
  );
};

const PipelineBuilder: React.FC<Props> = ({ plugins }) => {
  const updateWeightMutation = useUpdatePluginWeight();
  
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  if (!Array.isArray(plugins)) return null;

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      // Logic for updating weight would go here
      // For now we just trigger the mutation if we had a proper list management
      console.log(`Reordering ${active.id} and ${over.id}`);
    }
  };

  return (
    <Box>
      <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', mb: 4 }}>
        <Cpu size={20} color="#00f3ff" />
        <Box>
          <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 900, letterSpacing: 1, color: '#fff', fontSize: '1.1rem' }}>
            EXECUTION PIPELINE
          </Typography>
          <Typography sx={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', fontWeight: 600 }}>
            SEQUENTIAL ORCHESTRATION OF CORE ENGINES AND PLUGIN EXTENSIONS
          </Typography>
        </Box>
      </Stack>

      <Box sx={{ position: 'relative', pl: 6 }}>
        {/* Connection Path */}
        <Box sx={{
          position: 'absolute',
          left: '24px',
          top: 0,
          bottom: 0,
          width: '2px',
          bgcolor: 'rgba(255,255,255,0.05)',
          '&::after': {
            content: '""',
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: 0,
            right: 0,
            background: 'linear-gradient(to bottom, #00f3ff 0%, transparent 100%)',
            opacity: 0.3
          }
        }} />

        {CORE_STEPS.map((step, stepIdx) => {
          const pluginsBefore = plugins.filter(p => p.anchor_step === step && p.runtime_position === 'BEFORE');
          const pluginsAfter = plugins.filter(p => p.anchor_step === step && p.runtime_position === 'AFTER');

          return (
            <Box key={step} sx={{ mb: 6, position: 'relative' }}>
              {/* Step Sequence Number */}
              <Box sx={{
                position: 'absolute',
                left: '-62px',
                top: 0,
                width: '30px',
                textAlign: 'right'
              }}>
                <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 900, color: 'rgba(255,255,255,0.1)', fontSize: '1.5rem' }}>
                  {(stepIdx + 1).toString().padStart(2, '0')}
                </Typography>
              </Box>

              {/* Plugins BEFORE */}
              {pluginsBefore.length > 0 && (
                <Box sx={{ mb: 2, ml: 2 }}>
                  <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                    <SortableContext items={pluginsBefore.map(p => p.slug)} strategy={verticalListSortingStrategy}>
                      {pluginsBefore.map(p => <SortableItem key={p.slug} plugin={p} />)}
                    </SortableContext>
                  </DndContext>
                </Box>
              )}

              {/* Core Step Node */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, mb: 2 }}>
                <Box sx={{
                  width: '12px',
                  height: '12px',
                  borderRadius: 0,
                  bgcolor: '#00f3ff',
                  boxShadow: '0 0 10px #00f3ff',
                  position: 'absolute',
                  left: '-31px',
                  zIndex: 2,
                  transform: 'rotate(45deg)'
                }} />
                
                <Paper sx={{
                  p: 2.5,
                  flexGrow: 1,
                  bgcolor: 'rgba(0, 243, 255, 0.03)',
                  border: '1px solid rgba(0, 243, 255, 0.1)',
                  borderRadius: 0,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  position: 'relative',
                  overflow: 'hidden',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '3px',
                    height: '100%',
                    bgcolor: '#00f3ff'
                  }
                }}>
                  <Box>
                    <Typography sx={{ fontFamily: 'Orbitron', fontWeight: 900, letterSpacing: 1, color: '#fff', fontSize: '0.9rem' }}>
                      {step.toUpperCase()}
                    </Typography>
                    <Typography sx={{ fontSize: '0.65rem', color: 'rgba(0, 243, 255, 0.5)', fontWeight: 800, letterSpacing: 0.5 }}>
                      SYSTEM CORE ENGINE
                    </Typography>
                  </Box>
                  <Shield size={20} color="rgba(0, 243, 255, 0.2)" />
                </Paper>
              </Box>

              {/* Plugins AFTER */}
              {pluginsAfter.length > 0 && (
                <Box sx={{ mt: 2, ml: 2 }}>
                  <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                    <SortableContext items={pluginsAfter.map(p => p.slug)} strategy={verticalListSortingStrategy}>
                      {pluginsAfter.map(p => <SortableItem key={p.slug} plugin={p} />)}
                    </SortableContext>
                  </DndContext>
                </Box>
              )}
            </Box>
          );
        })}

        {/* End of Pipeline Marker */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, ml: 2, opacity: 0.5 }}>
           <ChevronRight size={16} color="#fff" style={{ marginLeft: -12 }} />
           <Typography sx={{ fontFamily: 'Orbitron', fontSize: '0.6rem', fontWeight: 900, letterSpacing: 2, color: 'rgba(255,255,255,0.3)' }}>
             PIPELINE TERMINATED
           </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default PipelineBuilder;
