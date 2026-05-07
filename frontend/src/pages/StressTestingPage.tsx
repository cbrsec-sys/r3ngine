import React from 'react';
import { LatencyChart } from '../components/scan/StressTab/LatencyChart';
import { ThroughputChart } from '../components/scan/StressTab/ThroughputChart';
import { StressHeatmap } from '../components/scan/StressTab/StressHeatmap';
import { ErrorDistribution } from '../components/scan/StressTab/ErrorDistribution';
import { EndpointTable } from '../components/scan/StressTab/EndpointTable';
import { DrilldownPanel } from '../components/scan/StressTab/DrilldownPanel';
import { useStressStore } from '../store/stressStore';
import { useParams, Link as RouterLink } from 'react-router-dom';
import { useStressTelemetry } from '../features/scans/api';
import { ArrowLeft } from 'lucide-react';

export const StressTestingPage: React.FC = () => {
  const { projectSlug, scanId } = useParams();
  const { selectedEndpoint } = useStressStore();
  const { data, isLoading: loading } = useStressTelemetry(scanId);

  if (loading) {
    return <div className="p-8 text-center text-gray-400">Loading stress test telemetry...</div>;
  }

  if (!data || data.length === 0) {
    return <div className="p-8 text-center text-gray-400">No stress test results available for this scan.</div>;
  }

  // Filter data based on selected endpoint for general charts if needed, 
  // or pass full data and let charts handle their own filtering
  // TODO: Properly type data and d variable used in data.filter
  const filteredData = selectedEndpoint ? data.filter((d: any) => d.endpoint === selectedEndpoint) : data;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <RouterLink to={`/${projectSlug}/scan/detail/${scanId}`} className="text-gray-400 hover:text-[#00f3ff] transition-colors">
            <ArrowLeft size={24} />
          </RouterLink>
          <h2 className="text-2xl font-bold text-gray-100">Adaptive Stress & Resilience Analysis</h2>
        </div>
        <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors">
          Export Report Snapshot
        </button>
      </div>

      {/* Primary KPI Cards (Mocked for layout) */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 p-4 rounded-lg">
          <div className="text-sm text-gray-400 mb-1">Max Concurrent Users</div>
          <div className="text-2xl font-bold text-white">500</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 p-4 rounded-lg">
          <div className="text-sm text-gray-400 mb-1">Peak Throughput</div>
          <div className="text-2xl font-bold text-green-400">1,240 RPS</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 p-4 rounded-lg">
          <div className="text-sm text-gray-400 mb-1">Global Error Rate</div>
          <div className="text-2xl font-bold text-red-400">2.4%</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 p-4 rounded-lg">
          <div className="text-sm text-gray-400 mb-1">Endpoints Saturated</div>
          <div className="text-2xl font-bold text-yellow-400">3 / 15</div>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LatencyChart data={filteredData} />
        <ThroughputChart data={filteredData} />
      </div>

      {/* Secondary Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StressHeatmap data={data} />
        <ErrorDistribution data={data} />
      </div>

      {/* Table and Drilldown */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-1">
          <EndpointTable data={data} />
        </div>
        <div className="xl:col-span-2">
          <DrilldownPanel data={data} />
        </div>
      </div>
    </div>
  );
};
