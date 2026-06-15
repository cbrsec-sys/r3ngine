// frontend/src/features/plugins/store/pluginCardRegistry.ts
import { create } from 'zustand';
import type React from 'react';

export interface PluginCardRegistration {
  slug: string;
  ScanCard?: React.ComponentType<{ scanId: number }>;
  TargetCard?: React.ComponentType<{ targetId: number }>;
  DashboardCard?: React.ComponentType;
}

interface PluginCardRegistryState {
  registrations: PluginCardRegistration[];
  registerPluginCards: (registration: PluginCardRegistration) => void;
}

export const usePluginCardRegistry = create<PluginCardRegistryState>((set) => ({
  registrations: [],
  registerPluginCards: (registration) =>
    set((state) => {
      // Replace existing registration for same slug, or append
      const existing = state.registrations.findIndex((r) => r.slug === registration.slug);
      if (existing >= 0) {
        const updated = [...state.registrations];
        updated[existing] = registration;
        return { registrations: updated };
      }
      return { registrations: [...state.registrations, registration] };
    }),
}));

// Convenience export so plugins can import directly without the hook
export const registerPluginCards = (registration: PluginCardRegistration): void =>
  usePluginCardRegistry.getState().registerPluginCards(registration);
