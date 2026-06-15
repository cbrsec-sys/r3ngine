// frontend/src/features/plugins/components/PluginCardSlot.tsx
import React from 'react';
import { Box } from '@mui/material';
import { usePluginCardRegistry } from '../store/pluginCardRegistry';

type SlotContext =
  | { type: 'scan'; scanId: number }
  | { type: 'target'; targetId: number }
  | { type: 'dashboard' };

interface PluginCardSlotProps {
  context: SlotContext;
}

const PluginCardSlot: React.FC<PluginCardSlotProps> = ({ context }) => {
  const { registrations } = usePluginCardRegistry();

  const cards = registrations.flatMap((reg) => {
    if (context.type === 'scan' && reg.ScanCard) {
      const Card = reg.ScanCard;
      return [<Card key={reg.slug} scanId={context.scanId} />];
    }
    if (context.type === 'target' && reg.TargetCard) {
      const Card = reg.TargetCard;
      return [<Card key={reg.slug} targetId={context.targetId} />];
    }
    if (context.type === 'dashboard' && reg.DashboardCard) {
      const Card = reg.DashboardCard;
      return [<Card key={reg.slug} />];
    }
    return [];
  });

  if (cards.length === 0) return null;

  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(auto-fill, minmax(340px, 1fr))' }, gap: 2, mt: 2 }}>
      {cards}
    </Box>
  );
};

export default PluginCardSlot;
