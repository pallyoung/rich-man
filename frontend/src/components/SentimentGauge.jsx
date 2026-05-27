import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

export default function SentimentGauge({ value = 50, height = 260, theme: themeMode = 'dark' }) {
  const option = useMemo(() => {
    const textColor = themeMode === 'dark' ? '#e6edf3' : '#1f1f1f';

    let sentimentLabel = '中性';
    if (value <= 20) sentimentLabel = '极度恐惧';
    else if (value <= 30) sentimentLabel = '恐惧';
    else if (value <= 50) sentimentLabel = '偏恐惧';
    else if (value <= 70) sentimentLabel = '偏贪婪';
    else if (value <= 80) sentimentLabel = '贪婪';
    else sentimentLabel = '极度贪婪';

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
  }, [value, themeMode]);

  return <ReactECharts option={option} style={{ height, width: '100%' }} />;
}
