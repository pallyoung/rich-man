import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

export default function EquityCurve({ data = [], height = 400, theme: themeMode = 'dark' }) {
  const option = useMemo(() => {
    if (!data || data.length === 0) return {};

    const textColor = themeMode === 'dark' ? '#e6edf3' : '#1f1f1f';
    const subTextColor = themeMode === 'dark' ? '#8b949e' : '#666666';
    const gridBorderColor = themeMode === 'dark' ? '#30363d' : '#d9d9d9';

    const dates = data.map((d) => d.date);
    const equity = data.map((d) => d.equity);
    const benchmark = data.map((d) => d.benchmark ?? null);

    const maxEquity = [];
    let peak = equity[0];
    const drawdown = equity.map((v) => {
      if (v > peak) peak = v;
      maxEquity.push(peak);
      return +(((v - peak) / peak) * 100).toFixed(2);
    });

    const seriesList = [
      {
        name: '策略净值',
        type: 'line',
        data: equity,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#58a6ff' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(88,166,255,0.25)' },
              { offset: 1, color: 'rgba(88,166,255,0)' },
            ],
          },
        },
      },
    ];

    if (benchmark.some((v) => v !== null)) {
      seriesList.push({
        name: '基准净值',
        type: 'line',
        data: benchmark,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#e6c73a', type: 'dashed' },
      });
    }

    seriesList.push({
      name: '回撤',
      type: 'line',
      data: drawdown,
      smooth: true,
      symbol: 'none',
      xAxisIndex: 0,
      yAxisIndex: 1,
      lineStyle: { width: 1, color: '#f85149' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(248,81,73,0.3)' },
            { offset: 1, color: 'rgba(248,81,73,0)' },
          ],
        },
      },
    });

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: themeMode === 'dark' ? '#1c2028' : '#ffffff',
        borderColor: gridBorderColor,
        textStyle: { color: textColor, fontSize: 12 },
      },
      legend: {
        data: ['策略净值', '基准净值', '回撤'],
        top: 0,
        textStyle: { color: subTextColor },
        itemWidth: 14,
        itemHeight: 2,
      },
      grid: {
        left: 60,
        right: 60,
        top: 40,
        bottom: 30,
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: subTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: gridBorderColor } },
      },
      yAxis: [
        {
          type: 'value',
          name: '净值',
          nameTextStyle: { color: subTextColor },
          splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.3 } },
          axisLabel: { color: subTextColor },
        },
        {
          type: 'value',
          name: '回撤%',
          nameTextStyle: { color: subTextColor },
          splitLine: { show: false },
          axisLabel: { color: subTextColor, formatter: '{value}%' },
          max: 0,
        },
      ],
      series: seriesList,
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          bottom: 5,
          height: 18,
          borderColor: gridBorderColor,
          textStyle: { color: subTextColor },
        },
      ],
    };
  }, [data, themeMode]);

  if (!data || data.length === 0) {
    return (
      <div
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#8b949e',
        }}
      >
        暂无回测数据
      </div>
    );
  }

  return <ReactECharts option={option} style={{ height, width: '100%' }} />;
}
