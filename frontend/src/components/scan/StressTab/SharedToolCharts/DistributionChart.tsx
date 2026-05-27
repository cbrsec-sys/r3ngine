import React, { useMemo } from 'react';
import { useTheme, alpha } from '@mui/material';
import ReactECharts from 'echarts-for-react';

export interface DistributionChartProps {
  data: { [category: string]: number };
  title: string;
  type: 'bar' | 'pie';
  colorMap?: { [category: string]: string };
  height?: number;
}

// Default color palette
const DEFAULT_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#06b6d4',
];

export const DistributionChart: React.FC<DistributionChartProps> = ({
  data,
  title,
  type = 'bar',
  colorMap = {},
  height = 300,
}) => {
  const theme = useTheme();

  const option = useMemo(() => {
    if (!data || Object.keys(data).length === 0) {
      return {
        backgroundColor: 'transparent',
        title: {
          text: 'NO DATA',
          textStyle: {
            color: alpha(theme.palette.text.primary, 0.3),
            fontFamily: 'Orbitron',
            fontSize: 12,
          },
        },
      };
    }

    const categories = Object.keys(data).sort((a, b) => data[b] - data[a]);
    const values = categories.map(cat => data[cat]);
    const colors = categories.map((cat, idx) => colorMap[cat] || DEFAULT_COLORS[idx % DEFAULT_COLORS.length]);
    const total = values.reduce((sum, v) => sum + v, 0);

    const baseConfig = {
      backgroundColor: 'transparent',
      animation: false,
      title: {
        text: title.toUpperCase(),
        textStyle: {
          color: theme.palette.primary.main,
          fontFamily: 'Orbitron',
          fontSize: 12,
          fontWeight: 800,
          letterSpacing: 1,
        },
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(5, 5, 10, 0.95)',
        borderColor: alpha(theme.palette.primary.main, 0.3),
        textStyle: { color: '#fff', fontSize: 11, fontFamily: 'monospace' },
        borderWidth: 1,
        borderRadius: 4,
      },
    };

    if (type === 'pie') {
      return {
        ...baseConfig,
        series: [
          {
            type: 'pie',
            radius: '75%',
            data: categories.map((cat, idx) => ({
              value: values[idx],
              name: cat,
              itemStyle: { color: colors[idx] },
            })),
            label: {
              formatter: '{b}: {c} ({d}%)',
              color: alpha(theme.palette.text.primary, 0.8),
              fontSize: 11,
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)',
              },
            },
          },
        ],
        legend: {
          bottom: 10,
          left: 'center',
          textStyle: { color: alpha(theme.palette.text.primary, 0.7), fontSize: 10 },
        },
      };
    }

    // Bar chart
    return {
      ...baseConfig,
      grid: { top: 60, bottom: 40, left: 60, right: 20 },
      xAxis: {
        type: 'category',
        data: categories,
        axisLine: { lineStyle: { color: alpha(theme.palette.text.primary, 0.1) } },
        axisLabel: { color: alpha(theme.palette.text.primary, 0.4), fontSize: 10, rotate: 30 },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: alpha(theme.palette.text.primary, 0.05) } },
        axisLine: { show: false },
        axisLabel: { color: alpha(theme.palette.text.primary, 0.4), fontSize: 10 },
      },
      series: [
        {
          type: 'bar',
          data: values.map((v, idx) => ({
            value: v,
            itemStyle: { color: colors[idx] },
          })),
          label: {
            show: true,
            position: 'top',
            color: alpha(theme.palette.text.primary, 0.6),
            fontSize: 10,
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.3)',
            },
          },
        },
      ],
    };
  }, [data, title, type, theme, colorMap]);

  return <ReactECharts option={option} style={{ height: `${height}px` }} />;
};
