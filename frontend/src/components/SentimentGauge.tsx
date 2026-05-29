import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

interface FearGreedFactor {
  score: number;
  weight: number;
  label: string;
}

interface SentimentGaugeProps {
  value?: number;
  label?: string;
  factors?: Record<string, FearGreedFactor>;
  height?: number;
  theme?: 'dark' | 'light';
}

function getSentimentLabel(value: number): string {
  if (value <= 20) return '极度恐惧';
  if (value <= 35) return '恐惧';
  if (value <= 45) return '偏恐惧';
  if (value <= 55) return '中性';
  if (value <= 65) return '偏贪婪';
  if (value <= 80) return '贪婪';
  return '极度贪婪';
}

function getFactorColor(score: number): string {
  if (score <= 30) return '#f85149';
  if (score <= 70) return '#e6c73a';
  return '#3fb950';
}

export default function SentimentGauge({ value = 50, label, factors, height = 260, theme: themeMode = 'dark' }: SentimentGaugeProps) {
  const sentimentLabel = label || getSentimentLabel(value);

  const factorList = factors
    ? Object.values(factors).sort((a, b) => b.weight - a.weight)
    : [];

  const option = useMemo(() => {
    const textColor = themeMode === 'dark' ? '#e6edf3' : '#1f1f1f';

    return {
      backgroundColor: 'transparent',
      series: [
        {
          type: 'gauge',
          startAngle: 200,
          endAngle: -20,
          min: 0,
          max: 100,
          splitNumber: 10,
          itemStyle: {
            color: value <= 30 ? '#f85149' : value <= 70 ? '#e6c73a' : '#3fb950',
          },
          progress: {
            show: true,
            width: 18,
          },
          pointer: {
            show: true,
            length: '60%',
            width: 4,
            itemStyle: {
              color: value <= 30 ? '#f85149' : value <= 70 ? '#e6c73a' : '#3fb950',
            },
          },
          axisLine: {
            lineStyle: {
              width: 18,
              color: [
                [0.3, '#f85149'],
                [0.7, '#e6c73a'],
                [1, '#3fb950'],
              ],
            },
          },
          axisTick: {
            distance: -22,
            length: 6,
            lineStyle: { color: '#fff', width: 1 },
          },
          splitLine: {
            distance: -26,
            length: 10,
            lineStyle: { color: '#fff', width: 2 },
          },
          axisLabel: {
            distance: -18,
            color: textColor,
            fontSize: 10,
          },
          detail: {
            valueAnimation: true,
            formatter: `{value}\n${sentimentLabel}`,
            color: textColor,
            fontSize: 18,
            fontWeight: 'bold',
            offsetCenter: [0, '30%'],
          },
          title: {
            show: true,
            offsetCenter: [0, '55%'],
            color: textColor,
            fontSize: 13,
          },
          data: [
            {
              value: value,
              name: '市场情绪指数',
            },
          ],
        },
      ],
    };
  }, [value, sentimentLabel, themeMode]);

  return (
    <div>
      <ReactECharts option={option} style={{ height: factorList.length > 0 ? height - 60 : height, width: '100%' }} />
      {factorList.length > 0 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 24, padding: '4px 16px 8px', flexWrap: 'wrap' }}>
          {factorList.map((f) => (
            <div key={f.label} style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={{ fontSize: 11, color: themeMode === 'dark' ? '#8b949e' : '#666', marginBottom: 2 }}>
                {f.label}
              </div>
              <div style={{ fontSize: 16, fontWeight: 600, color: getFactorColor(f.score) }}>
                {f.score}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
