import { create } from 'zustand';

interface StressState {
  selectedEndpoint: string | null;
  selectedTimeRange: [string, string] | null;
  selectedMetric: "latency" | "errors" | "throughput";
  
  setSelectedEndpoint: (endpoint: string | null) => void;
  setSelectedTimeRange: (range: [string, string] | null) => void;
  setSelectedMetric: (metric: "latency" | "errors" | "throughput") => void;
  resetSelections: () => void;
}

export const useStressStore = create<StressState>((set) => ({
  selectedEndpoint: null,
  selectedTimeRange: null,
  selectedMetric: "latency",
  
  setSelectedEndpoint: (endpoint) => set({ selectedEndpoint: endpoint }),
  setSelectedTimeRange: (range) => set({ selectedTimeRange: range }),
  setSelectedMetric: (metric) => set({ selectedMetric: metric }),
  resetSelections: () => set({ selectedEndpoint: null, selectedTimeRange: null, selectedMetric: "latency" }),
}));
