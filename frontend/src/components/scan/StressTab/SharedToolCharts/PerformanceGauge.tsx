import React, { useMemo } from 'react';
import { useTheme, alpha } from '@mui/material';
import ReactECharts from 'echarts-for-react';

export interface ColorRange {
  min: number;
  max: number;
  color: string;
}

export interface PerformanceGaugeProps {
  value: number;
  max: number;
  title: string;
  unit: string;
  colorRanges: ColorRange[];
  size?: number;
}

export const PerformanceGauge: React.FC<PerformanceGaugeProps> = ({
  value = 0,
  max = 100,
  title = '',
  unit = '',
  colorRanges = [],
  size = 200,
}) => {
  const theme = useTheme();

  // Ensure valid data types
  const validValue = typeof value === 'number' ? Math.min(value, max) : 0;
  const validMax = typeof max === 'number' && max > 0 ? max : 100;
  const validTitle = typeof title === 'string' ? title : '';
  const validUnit = typeof unit === 'string' ? unit : '';
  const validColorRanges = Array.isArray(colorRanges) ? colorRanges : [];

  const option = useMemo(() => {
    // Handle empty color ranges
    if (!Array.isArray(validColorRanges) || validColorRanges.length === 0) {
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

    // Find the color for the current value
    let valueColor = '#3b82f6';
    for (const range of validColorRanges) {
      if (typeof range === 'object' && range !== null && 'min' in range && 'max' in range && 'color' in range) {
        if (validValue >= range.min && validValue <= range.max) {
          valueColor = range.color;
          break;
        }
      }
    }

    // Build color ranges for axis line
    const axisLineColors = validColorRanges
      .filter(r => typeof r === 'object' && 'max' in r && 'color' in r)
      .map(r => [Math.min(r.max / validMax, 1), r.color]);

    return {
      backgroundColor: 'transparent',
      animation: false,
      title: {
        text: validTitle.toUpperCase(),
        textStyle: {
          color: theme.palette.primary.main,
          fontFamily: 'Orbitron',
          fontSize: 11,
          fontWeight: 800,
          letterSpacing: 1,
        },
        left: 'center',
        top: '10%',
      },
      series: [
        {
          type: 'gauge',
          startAngle: 225,
          endAngle: -45,
          radius: '85%',
          center: ['50%', '60%'],
          min: 0,
          max: validMax,
          splitNumber: 8,
          axisLine: {
            lineStyle: {
              width: 30,
              color: axisLineColors.length > 0 ? axisLineColors : [[1, '#3b82f6']],
            },
          },
          pointer: {
            itemStyle: {
              color: 'auto',
              shadowColor: 'rgba(0, 0, 0, 0.5)',
              shadowBlur: 10,
            },
          },
          axisTick: {
            distance: -30,
            length: 8,
            lineStyle: {
              color: alpha(theme.palette.text.primary, 0.2),
              width: 2,
            },
          },
          splitLine: {
            distance: -30,
            length: 30,
            lineStyle: {
              color: alpha(theme.palette.text.primary, 0.1),
              width: 4,
            },
          },
          axisLabel: {
            color: 'auto',
            distance: 40,
            fontSize: 10,
            fontWeight: 700,
          },
          detail: {
            valueAnimation: false,
            formatter: `{value} ${validUnit}`,
            color: valueColor,
            fontSize: 24,
            fontWeight: 700,
            fontFamily: 'Orbitron',
          },
          data: [{ value: validValue, name: '' }],
        },
      ],
    };
  }, [validValue, validMax, validTitle, validUnit, validColorRanges, theme]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '100%' }}>
      <ReactECharts option={option} style={{ width: '100%', height: `${size}px` }} />
    </div>
  );
};
