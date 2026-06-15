import { useThemeTokens } from '../../../theme/useThemeTokens';
import React from 'react';
import { ResponsiveBar } from '@nivo/bar';
import { useStressStore } from '../../../store/stressStore';

interface ErrorDistributionProps {
  data: any[];
}

export const ErrorDistribution: React.FC<ErrorDistributionProps> = ({ data }) => {
  const { tokens } = useThemeTokens();
  const { setSelectedEndpoint } = useStressStore();

  return (
    <div className="w-full h-96 bg-gray-900 rounded-lg p-4 border border-gray-800">
      <h3 className="text-lg font-bold text-gray-200 mb-2">Error Distribution</h3>
      <div className="h-[calc(100%-2rem)]">
        <ResponsiveBar
            data={data}
            keys={['error_rate']}
            indexBy="endpoint"
            animate={false}
            margin={{ top: 10, right: 10, bottom: 50, left: 60 }}
            padding={0.3}
            valueScale={{ type: 'linear' }}
            indexScale={{ type: 'band', round: true }}
            colors={{ scheme: 'reds' }}
            theme={{
                axis: {
                    ticks: {
                        text: { fill: '#ccc' }
                    },
                    legend: {
                        text: { fill: '#ccc' }
                    }
                },
                tooltip: {
                    container: { background: '#1f2937', color: '#f3f4f6' }
                }
            }}
            axisBottom={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: -45,
                legend: 'Endpoint',
                legendPosition: 'middle',
                legendOffset: 40
            }}
            axisLeft={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: 0,
                legend: 'Error Rate (%)',
                legendPosition: 'middle',
                legendOffset: -40
            }}
            labelSkipWidth={12}
            labelSkipHeight={12}
            labelTextColor="#ffffff"
            onClick={(node) => setSelectedEndpoint(node.data.endpoint as string)}
        />
      </div>
    </div>
  );
};
