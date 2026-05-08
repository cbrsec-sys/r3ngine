import React from 'react';
import {
  Box,
  Typography,
  Divider,
  Paper
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
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { Plugin } from '../api/pluginsApi';

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
  } = useSortable({ id: plugin.slug });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <Box
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      sx={{
        p: 2,
        mb: 1,
        background: 'rgba(255, 255, 255, 0.05)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '8px',
        cursor: 'grab',
        '&:active': { cursor: 'grabbing' }
      }}
    >
      <Typography variant="subtitle2">{plugin.name}</Typography>
      <Typography variant="caption" color="text.secondary">v{plugin.version}</Typography>
    </Box>
  );
};

const PipelineBuilder: React.FC<Props> = ({ plugins }) => {
  if (!Array.isArray(plugins)) return null;

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      // In a real app, we'd update the order_weight here via API
      console.log(`Moving ${active.id} to position of ${over.id}`);
    }
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>Scan Pipeline</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
        Drag and drop plugins to customize their execution order relative to core engines.
      </Typography>

      <Box sx={{ position: 'relative', pl: 4 }}>
        {/* Timeline Line */}
        <Box sx={{
          position: 'absolute',
          left: '12px',
          top: 0,
          bottom: 0,
          width: '2px',
          background: 'linear-gradient(to bottom, #0076FF, #FF00E5)'
        }} />

        {CORE_STEPS?.length > 0 && CORE_STEPS.map((step, index) => {
          const pluginsBefore = plugins.filter(p => p.anchor_step === step && p.runtime_position === 'BEFORE');
          const pluginsAfter = plugins.filter(p => p.anchor_step === step && p.runtime_position === 'AFTER');

          return (
            <Box key={step} sx={{ mb: 6 }}>
              {/* Plugins Before */}
              {pluginsBefore.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={handleDragEnd}
                  >
                    <SortableContext
                      items={pluginsBefore.map(p => p.slug)}
                      strategy={verticalListSortingStrategy}
                    >
                      {pluginsBefore.map(p => <SortableItem key={p.slug} plugin={p} />)}
                    </SortableContext>
                  </DndContext>
                </Box>
              )}

              {/* Core Step Marker */}
              <Box sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                mb: 2,
                position: 'relative'
              }}>
                <Box sx={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  bgcolor: '#0076FF',
                  border: '4px solid #121212',
                  position: 'absolute',
                  left: '-23px'
                }} />
                <Paper sx={{
                  p: 2,
                  flexGrow: 1,
                  background: 'rgba(0, 118, 255, 0.1)',
                  border: '1px solid #0076FF',
                  borderRadius: '12px'
                }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: "bold" }}>{step}</Typography>
                  <Typography variant="caption" color="text.secondary">Core reNgine Task</Typography>
                </Paper>
              </Box>

              {/* Plugins After */}
              {pluginsAfter.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={handleDragEnd}
                  >
                    <SortableContext
                      items={pluginsAfter.map(p => p.slug)}
                      strategy={verticalListSortingStrategy}
                    >
                      {pluginsAfter.map(p => <SortableItem key={p.slug} plugin={p} />)}
                    </SortableContext>
                  </DndContext>
                </Box>
              )}
            </Box>
          );
        }) || (
            <Box sx={{ textAlign: "center", py: 10 }}>
              <Typography variant="h6" color="text.secondary" sx={{ justifyContent: "center" }}>
                No plugins installed yet.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ justifyContent: "center" }}>
                Upload a plugin archive to get started.
              </Typography>
            </Box>
          )}
      </Box>
    </Box>
  );
};

export default PipelineBuilder;
