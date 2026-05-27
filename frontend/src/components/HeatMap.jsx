import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

export default function HeatMap({ data = [], height = 500, theme: themeMode = 'dark' }) {
  const option = useMemo(() => {
    if (!data || data.length === 0) return {};

    const textColor = themeMode === 'dark' ? '#e6edf3' : '#1f1f1f';
    const bgColor = themeMode === 'dark' ? '#161b22' : '#ffffff';

    const treeData = data.map((item) => ({
      name: item.name,
      value: item.value || item.market_cap || 1,
      change: item.change || item.change_pct || 0,
      itemStyle: {
        color: getSectorColor(item.change || item.change_pct || 0),
      },
      label: {
        show: true,
        formatter: `${item.name}\n${(item.change || item.change_pct || 0) > 0 ? '+' : ''}${(item.change || item.change_pct || 0).toFixed(2)}%`,
        color: Math.abs(item.change || item.change_pct || 0) > 3 ? '#fff' : textColor,
        fontSize: 12,
        lineHeight: 18,
      },
    }));

    return {
      backgroundColor: bgColor,
      tooltip: {
        formatter: (params) => {
          const d = params.data;
          const ch = d.change || 0;
          const color = ch >= 0 ? '#f85149' : '#3fb950';
          return `<div style="font-size:13px">
            <b>${d.name}</b><br/>
            平均涨跌幅: <span style="color:${color}">${ch > 0 ? '+' : ''}${ch.toFixed(2)}%</span><br/>
            ${d.leading_stock ? `领涨股: ${d.leading_stock}` : ''}
          </div>`;
        },
      },
      series: [
        {
          type: 'treemap',
          width: '96%',
          height: '90%',
          roam: false,
          nodeClick: false,
          breadcrumb: { show: false },
          data: treeData,
          levels: [
            {
              itemStyle: {
                borderColor: bgColor,
                borderWidth: 2,
                gapWidth: 2,
              },
            },
          ],
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
        暂无板块数据
      </div>
    );
  }

  return <ReactECharts option={option} style={{ height, width: '100%' }} />;
}

function getSectorColor(change) {
  if (change >= 5) return '#c22538';
  if (change >= 3) return '#e84040';
  if (change >= 1) return '#f85149';
  if (change > -1) return '#6e7681';
  if (change > -3) return '#3fb950';
  if (change > -5) return '#2ea043';
  return '#1a7f37';
}
