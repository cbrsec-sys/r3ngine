import { create } from 'zustand';

export interface TelemetryPoint {
  timestamp: number;
  tool: string;
  endpoint: string;
  latency?: number;
  avg_latency?: number;
  p95_latency?: number;
  throughput_rps?: number;
  error_rate?: number;
  packet_loss?: number;
  [key: string]: any;
}

interface StressState {
  selectedEndpoint: string | null;
  selectedTimeRange: [number, number] | null;
  selectedMetric: "latency" | "errors" | "throughput";
  isScanning: boolean;
  telemetryData: TelemetryPoint[];
  
  setSelectedEndpoint: (endpoint: string | null) => void;
  setSelectedTimeRange: (range: [number, number] | null) => void;
  setSelectedMetric: (metric: "latency" | "errors" | "throughput") => void;
  setScanning: (isScanning: boolean) => void;
  addTelemetryPoint: (point: TelemetryPoint) => void;
  clearTelemetry: () => void;
  resetSelections: () => void;
}

export const useStressStore = create<StressState>((set) => ({
  selectedEndpoint: null,
  selectedTimeRange: null,
  selectedMetric: "latency",
  isScanning: false,
  telemetryData: [],
  
  setSelectedEndpoint: (endpoint) => set({ selectedEndpoint: endpoint }),
  setSelectedTimeRange: (range) => set({ selectedTimeRange: range }),
  setSelectedMetric: (metric) => set({ selectedMetric: metric }),
  setScanning: (isScanning) => set({ isScanning }),
  
  addTelemetryPoint: (point) => set((state) => {
    // Keep last 5000 points to avoid memory issues
    const newData = [...state.telemetryData, point];
    if (newData.length > 5000) {
      newData.shift();
    }
    return { telemetryData: newData };
  }),
  
  clearTelemetry: () => set({ telemetryData: [] }),
  
  resetSelections: () => set({ 
    selectedEndpoint: null, 
    selectedTimeRange: null, 
    selectedMetric: "latency" 
  }),
}));
