import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

export default function KLineChart({
  data = [],
  indicators = {},
  title = '',
  height = 600,
  theme: themeMode = 'dark',
}) {
  const option = useMemo(() => {
    if (!data || data.length === 0) return {};

    const dates = data.map((d) => d[0]);
    const ohlc = data.map((d) => [d[1], d[4], d[2], d[3]]);
    const volumes = data.map((d) => d[5]);

    const textColor = themeMode === 'dark' ? '#e6edf3' : '#1f1f1f';
    const subTextColor = themeMode === 'dark' ? '#8b949e' : '#666666';
    const gridBorderColor = themeMode === 'dark' ? '#30363d' : '#d9d9d9';

    const maColors = ['#e6c73a', '#58a6ff', '#f97583', '#a371f7', '#3fb950', '#f85149'];
    const maPeriods = indicators.ma_periods || [5, 10, 20, 60];
    const showMACD = indicators.macd !== false;
    const showVolume = indicators.volume !== false;

    const gridCount = 1 + (showVolume ? 1 : 0) + (showMACD ? 1 : 0);
    const gridHeight = Math.floor(60 / gridCount);
    const grids = [];
    const xAxes = [];
    const yAxes = [];
    const seriesList = [];
    let currentTop = 8;

    grids.push({
      left: 60,
      right: 30,
      top: `${currentTop + 4}%`,
      height: `${gridHeight}%`,
    });
    xAxes.push({
      type: 'category',
      data: dates,
      gridIndex: 0,
      axisLabel: { show: false },
      axisLine: { lineStyle: { color: gridBorderColor } },
      axisTick: { show: false },
    });
    yAxes.push({
      scale: true,
      gridIndex: 0,
      splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.3 } },
      axisLabel: { color: subTextColor },
      axisLine: { lineStyle: { color: gridBorderColor } },
    });

    seriesList.push({
      name: 'K线',
      type: 'candlestick',
      data: ohlc,
      xAxisIndex: 0,
      yAxisIndex: 0,
      itemStyle: {
        color: '#f85149',
        color0: '#3fb950',
        borderColor: '#f85149',
        borderColor0: '#3fb950',
      },
    });

    maPeriods.forEach((period, idx) => {
      const maData = data.map((_, i) => {
        if (i < period - 1) return null;
        let sum = 0;
        for (let j = 0; j < period; j++) {
          sum += Number(data[i - j][4]);
        }
        return (sum / period).toFixed(2);
      });
      seriesList.push({
        name: `MA${period}`,
        type: 'line',
        data: maData,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 1,
          color: maColors[idx % maColors.length],
        },
      });
    });

    currentTop += gridHeight + 4;

    if (showVolume) {
      grids.push({
        left: 60,
        right: 30,
        top: `${currentTop + 2}%`,
        height: `${gridHeight - 4}%`,
      });
      xAxes.push({
        type: 'category',
        data: dates,
        gridIndex: grids.length - 1,
        axisLabel: { show: grids.length === gridCount, color: subTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: gridBorderColor } },
        axisTick: { show: false },
      });
      yAxes.push({
        gridIndex: grids.length - 1,
        splitNumber: 2,
        splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.3 } },
        axisLabel: {
          color: subTextColor,
          fontSize: 10,
          formatter: (v) => {
            if (v >= 1e8) return `${(v / 1e8).toFixed(0)}亿`;
            if (v >= 1e4) return `${(v / 1e4).toFixed(0)}万`;
            return v;
          },
        },
        axisLine: { lineStyle: { color: gridBorderColor } },
      });
      seriesList.push({
        name: '成交量',
        type: 'bar',
        data: volumes.map((v, i) => ({
          value: v,
          itemStyle: {
            color: ohlc[i][0] >= ohlc[i][1] ? 'rgba(248,81,73,0.7)' : 'rgba(63,185,80,0.7)',
          },
        })),
        xAxisIndex: xAxes.length - 1,
        yAxisIndex: yAxes.length - 1,
      });
      currentTop += gridHeight;
    }

    if (showMACD) {
      const closePrices = data.map((d) => Number(d[4]));
      const ema12 = calcEMA(closePrices, 12);
      const ema26 = calcEMA(closePrices, 26);
      const dif = ema12.map((v, i) => (v !== null && ema26[i] !== null ? +(v - ema26[i]).toFixed(4) : null));
      const dea = calcEMA(dif.filter((v) => v !== null), 9);
      const deaFull = [];
      let deaIdx = 0;
      for (let i = 0; i < dif.length; i++) {
        if (dif[i] !== null) {
          deaFull.push(dea[deaIdx] !== undefined ? +dea[deaIdx].toFixed(4) : null);
          deaIdx++;
        } else {
          deaFull.push(null);
        }
      }
      const macdBar = dif.map((v, i) => {
        if (v !== null && deaFull[i] !== null) {
          return +((v - deaFull[i]) * 2).toFixed(4);
        }
        return null;
      });

      grids.push({
        left: 60,
        right: 30,
        top: `${currentTop + 2}%`,
        height: `${gridHeight - 4}%`,
      });
      xAxes.push({
        type: 'category',
        data: dates,
        gridIndex: grids.length - 1,
        axisLabel: { show: true, color: subTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: gridBorderColor } },
        axisTick: { show: false },
      });
      yAxes.push({
        gridIndex: grids.length - 1,
        splitNumber: 2,
        splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.3 } },
        axisLabel: { color: subTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: gridBorderColor } },
      });
      const xAxisIdx = xAxes.length - 1;
      const yAxisIdx = yAxes.length - 1;
      seriesList.push({
        name: 'MACD',
        type: 'bar',
        data: macdBar.map((v) => ({
          value: v,
          itemStyle: { color: v !== null && v >= 0 ? '#f85149' : '#3fb950' },
        })),
        xAxisIndex: xAxisIdx,
        yAxisIndex: yAxisIdx,
      });
      seriesList.push({
        name: 'DIF',
        type: 'line',
        data: dif,
        xAxisIndex: xAxisIdx,
        yAxisIndex: yAxisIdx,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: '#58a6ff' },
      });
      seriesList.push({
        name: 'DEA',
        type: 'line',
        data: deaFull,
        xAxisIndex: xAxisIdx,
        yAxisIndex: yAxisIdx,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: '#e6c73a' },
      });
    }

    const dataZoom = [
      {
        type: 'inside',
        xAxisIndex: xAxes.map((_, i) => i),
        start: Math.max(0, 100 - Math.min(100, (60 / data.length) * 100)),
        end: 100,
      },
      {
        type: 'slider',
        xAxisIndex: xAxes.map((_, i) => i),
        bottom: 5,
        height: 20,
        borderColor: gridBorderColor,
        backgroundColor: themeMode === 'dark' ? '#161b22' : '#f5f5f5',
        dataBackground: {
          lineStyle: { color: subTextColor },
          areaStyle: { color: subTextColor, opacity: 0.1 },
        },
        textStyle: { color: subTextColor },
      },
    ];

    return {
      animation: true,
      backgroundColor: 'transparent',
      title: {
        text: title,
        left: 'center',
        top: 0,
        textStyle: { color: textColor, fontSize: 14 },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: themeMode === 'dark' ? '#1c2028' : '#ffffff',
        borderColor: gridBorderColor,
        textStyle: { color: textColor, fontSize: 12 },
        formatter: (params) => {
          if (!params || params.length === 0) return '';
          const idx = params[0].dataIndex;
          const d = data[idx];
          if (!d) return '';
          const date = d[0];
          const open = Number(d[1]).toFixed(2);
          const close = Number(d[4]).toFixed(2);
          const high = Number(d[2]).toFixed(2);
          const low = Number(d[3]).toFixed(2);
          const vol = d[5];
          let volStr;
          if (vol >= 1e8) volStr = `${(vol / 1e8).toFixed(2)}亿`;
          else if (vol >= 1e4) volStr = `${(vol / 1e4).toFixed(2)}万`;
          else volStr = vol;
          let html = `<div style="font-size:12px"><b>${date}</b><br/>`;
          html += `开盘: ${open} 收盘: ${close}<br/>`;
          html += `最高: ${high} 最低: ${low}<br/>`;
          html += `成交量: ${volStr}</div>`;
          return html;
        },
      },
      legend: {
        data: seriesList.filter((s) => s.type !== 'candlestick').map((s) => s.name),
        top: 24,
        textStyle: { color: subTextColor, fontSize: 11 },
        itemWidth: 14,
        itemHeight: 2,
      },
      grid: grids,
      xAxis: xAxes,
      yAxis: yAxes,
      series: seriesList,
      dataZoom,
    };
  }, [data, indicators, title, themeMode]);

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
        暂无K线数据
      </div>
    );
  }

  return <ReactECharts option={option} style={{ height, width: '100%' }} />;
}

function calcEMA(data, period) {
  const result = [];
  const k = 2 / (period + 1);
  let ema = null;
  for (let i = 0; i < data.length; i++) {
    if (data[i] === null || data[i] === undefined) {
      result.push(null);
      continue;
    }
    if (ema === null) {
      ema = data[i];
    } else {
      ema = data[i] * k + ema * (1 - k);
    }
    result.push(ema);
  }
  return result;
}
