import React, { useMemo } from 'react';
import { useTheme, alpha } from '@mui/material';
import ReactECharts from 'echarts-for-react';

export interface TimeSeriesDataPoint {
  timestamp: number;
  [key: string]: number;
}

export interface TimeSeriesSeries {
  key: string;
  name: string;
  color: string;
}

export interface TimeSeriesChartProps {
  data: TimeSeriesDataPoint[];
  series: TimeSeriesSeries[];
  title: string;
  yAxisLabel?: string;
  yAxisMax?: number;
  height?: number;
}

export const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  data,
  series,
  title,
  yAxisLabel,
  yAxisMax,
  height = 300,
}) => {
  const theme = useTheme();

  const option = useMemo(() => {
    // Handle empty or invalid data
    if (!Array.isArray(data) || data.length === 0) {
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

    // Convert data to format expected by ECharts
    const timestamps = data.map(d => d.timestamp * 1000); // Convert to milliseconds

    const seriesData = series.map(s => ({
      name: s.name,
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: data.map(d => d[s.key] || null),
      itemStyle: { color: s.color },
      lineStyle: { width: 2, shadowBlur: 10, shadowColor: alpha(s.color, 0.5) },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: alpha(s.color, 0.2) },
            { offset: 1, color: 'rgba(0, 0, 0, 0)' },
          ],
        },
      },
    }));

    return {
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
        trigger: 'axis',
        backgroundColor: 'rgba(5, 5, 10, 0.95)',
        borderColor: alpha(theme.palette.primary.main, 0.3),
        textStyle: { color: '#fff', fontSize: 11, fontFamily: 'monospace' },
        borderWidth: 1,
        borderRadius: 4,
      },
      grid: { top: 60, bottom: 40, left: 50, right: 20 },
      xAxis: {
        type: 'time',
        splitLine: { show: false },
        axisLine: { lineStyle: { color: alpha(theme.palette.text.primary, 0.1) } },
        axisLabel: { color: alpha(theme.palette.text.primary, 0.4), fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        name: yAxisLabel,
        max: yAxisMax,
        splitLine: { lineStyle: { color: alpha(theme.palette.text.primary, 0.05) } },
        axisLine: { show: false },
        axisLabel: { color: alpha(theme.palette.text.primary, 0.4), fontSize: 10 },
      },
      legend: {
        top: 45,
        right: 20,
        textStyle: { color: alpha(theme.palette.text.primary, 0.7), fontSize: 11 },
      },
      series: seriesData,
    };
  }, [data, series, title, theme, yAxisLabel, yAxisMax]);

  return <ReactECharts option={option} style={{ height: `${height}px` }} />;
};
