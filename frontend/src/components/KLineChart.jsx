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
    const showMACD = indicators.macd === true;
    const showKDJ = indicators.kdj === true;
    const showRSI = indicators.rsi === true;
    const showBOLL = indicators.boll === true;
    const showVolume = indicators.volume !== false;

    // Count sub-charts
    let subChartCount = 0;
    if (showVolume) subChartCount++;
    if (showMACD) subChartCount++;
    if (showKDJ) subChartCount++;
    if (showRSI) subChartCount++;

    const mainGridHeight = subChartCount === 0 ? 70 : subChartCount === 1 ? 55 : subChartCount === 2 ? 42 : 32;
    const subGridHeight = subChartCount <= 1 ? 18 : subChartCount === 2 ? 16 : 13;

    const grids = [];
    const xAxes = [];
    const yAxes = [];
    const seriesList = [];
    let currentTop = 8;

    // Main chart grid (candlestick + MA + BOLL)
    grids.push({
      left: 60, right: 30,
      top: `${currentTop + 4}%`,
      height: `${mainGridHeight}%`,
    });
    xAxes.push({
      type: 'category', data: dates, gridIndex: 0,
      axisLabel: { show: false },
      axisLine: { lineStyle: { color: gridBorderColor } },
      axisTick: { show: false },
    });
    yAxes.push({
      scale: true, gridIndex: 0,
      splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.3 } },
      axisLabel: { color: subTextColor },
      axisLine: { lineStyle: { color: gridBorderColor } },
    });

    // Candlestick
    seriesList.push({
      name: 'K线', type: 'candlestick', data: ohlc,
      xAxisIndex: 0, yAxisIndex: 0,
      itemStyle: {
        color: '#f85149', color0: '#3fb950',
        borderColor: '#f85149', borderColor0: '#3fb950',
      },
    });

    // MA lines
    maPeriods.forEach((period, idx) => {
      const maData = data.map((_, i) => {
        if (i < period - 1) return null;
        let sum = 0;
        for (let j = 0; j < period; j++) sum += Number(data[i - j][4]);
        return +(sum / period).toFixed(2);
      });
      seriesList.push({
        name: `MA${period}`, type: 'line', data: maData,
        xAxisIndex: 0, yAxisIndex: 0,
        smooth: true, symbol: 'none',
        lineStyle: { width: 1, color: maColors[idx % maColors.length] },
      });
    });

    // BOLL bands overlay
    if (showBOLL) {
      const closePrices = data.map((d) => Number(d[4]));
      const bollPeriod = 20;
      const bollK = 2;
      const mid = [], upper = [], lower = [];
      for (let i = 0; i < closePrices.length; i++) {
        if (i < bollPeriod - 1) {
          mid.push(null); upper.push(null); lower.push(null);
          continue;
        }
        let sum = 0;
        for (let j = 0; j < bollPeriod; j++) sum += closePrices[i - j];
        const avg = sum / bollPeriod;
        let sqSum = 0;
        for (let j = 0; j < bollPeriod; j++) sqSum += (closePrices[i - j] - avg) ** 2;
        const std = Math.sqrt(sqSum / bollPeriod);
        mid.push(+avg.toFixed(2));
        upper.push(+(avg + bollK * std).toFixed(2));
        lower.push(+(avg - bollK * std).toFixed(2));
      }
      seriesList.push(
        { name: 'BOLL上轨', type: 'line', data: upper, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#a371f7', type: 'dashed' } },
        { name: 'BOLL中轨', type: 'line', data: mid, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#e6c73a' } },
        { name: 'BOLL下轨', type: 'line', data: lower, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#a371f7', type: 'dashed' } },
      );
    }

    currentTop += mainGridHeight + 4;

    // Volume sub-chart
    if (showVolume) {
      grids.push({
        left: 60, right: 30,
        top: `${currentTop + 2}%`,
        height: `${subGridHeight}%`,
      });
      const xi = grids.length - 1;
      xAxes.push({
        type: 'category', data: dates, gridIndex: xi,
        axisLabel: { show: subChartCount <= 1, color: subTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: gridBorderColor } },
        axisTick: { show: false },
      });
      yAxes.push({
        gridIndex: xi, splitNumber: 2,
        splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.3 } },
        axisLabel: {
          color: subTextColor, fontSize: 10,
          formatter: (v) => {
            if (v >= 1e8) return `${(v / 1e8).toFixed(0)}亿`;
            if (v >= 1e4) return `${(v / 1e4).toFixed(0)}万`;
            return v;
          },
        },
        axisLine: { lineStyle: { color: gridBorderColor } },
      });
      seriesList.push({
        name: '成交量', type: 'bar',
        data: volumes.map((v, i) => ({
          value: v,
          itemStyle: { color: ohlc[i][0] >= ohlc[i][1] ? 'rgba(248,81,73,0.7)' : 'rgba(63,185,80,0.7)' },
        })),
        xAxisIndex: xi, yAxisIndex: xi,
      });
      currentTop += subGridHeight + 2;
    }

    // MACD sub-chart
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
        if (v !== null && deaFull[i] !== null) return +((v - deaFull[i]) * 2).toFixed(4);
        return null;
      });

      grids.push({
        left: 60, right: 30,
        top: `${currentTop + 2}%`,
        height: `${subGridHeight}%`,
      });
      const xi = grids.length - 1;
      const isLastSub = !showKDJ && !showRSI;
      xAxes.push({
        type: 'category', data: dates, gridIndex: xi,
        axisLabel: { show: isLastSub, color: subTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: gridBorderColor } },
        axisTick: { show: false },
      });
      yAxes.push({
        gridIndex: xi, splitNumber: 2,
        splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.3 } },
        axisLabel: { color: subTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: gridBorderColor } },
      });
      seriesList.push(
        {
          name: 'MACD', type: 'bar',
          data: macdBar.map((v) => ({
            value: v,
            itemStyle: { color: v !== null && v >= 0 ? '#f85149' : '#3fb950' },
          })),
          xAxisIndex: xi, yAxisIndex: xi,
        },
        { name: 'DIF', type: 'line', data: dif, xAxisIndex: xi, yAxisIndex: xi, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#58a6ff' } },
        { name: 'DEA', type: 'line', data: deaFull, xAxisIndex: xi, yAxisIndex: xi, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#e6c73a' } },
      );
      currentTop += subGridHeight + 2;
    }

    // KDJ sub-chart
    if (showKDJ) {
      const closePrices = data.map((d) => Number(d[4]));
      const highPrices = data.map((d) => Number(d[2]));
      const lowPrices = data.map((d) => Number(d[3]));
      const { kValues, dValues, jValues } = calcKDJ(closePrices, highPrices, lowPrices);

      grids.push({
        left: 60, right: 30,
        top: `${currentTop + 2}%`,
        height: `${subGridHeight}%`,
      });
      const xi = grids.length - 1;
      const isLastSub = !showRSI;
      xAxes.push({
        type: 'category', data: dates, gridIndex: xi,
        axisLabel: { show: isLastSub, color: subTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: gridBorderColor } },
        axisTick: { show: false },
      });
      yAxes.push({
        gridIndex: xi, splitNumber: 2,
        splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.3 } },
        axisLabel: { color: subTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: gridBorderColor } },
      });
      seriesList.push(
        { name: 'K', type: 'line', data: kValues, xAxisIndex: xi, yAxisIndex: xi, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#58a6ff' } },
        { name: 'D', type: 'line', data: dValues, xAxisIndex: xi, yAxisIndex: xi, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#e6c73a' } },
        { name: 'J', type: 'line', data: jValues, xAxisIndex: xi, yAxisIndex: xi, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#a371f7' } },
      );
      currentTop += subGridHeight + 2;
    }

    // RSI sub-chart
    if (showRSI) {
      const closePrices = data.map((d) => Number(d[4]));
      const rsi6 = calcRSI(closePrices, 6);
      const rsi12 = calcRSI(closePrices, 12);
      const rsi24 = calcRSI(closePrices, 24);

      grids.push({
        left: 60, right: 30,
        top: `${currentTop + 2}%`,
        height: `${subGridHeight}%`,
      });
      const xi = grids.length - 1;
      xAxes.push({
        type: 'category', data: dates, gridIndex: xi,
        axisLabel: { show: true, color: subTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: gridBorderColor } },
        axisTick: { show: false },
      });
      yAxes.push({
        gridIndex: xi, splitNumber: 2, min: 0, max: 100,
        splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.3 } },
        axisLabel: { color: subTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: gridBorderColor } },
      });
      seriesList.push(
        { name: 'RSI6', type: 'line', data: rsi6, xAxisIndex: xi, yAxisIndex: xi, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#58a6ff' } },
        { name: 'RSI12', type: 'line', data: rsi12, xAxisIndex: xi, yAxisIndex: xi, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#e6c73a' } },
        { name: 'RSI24', type: 'line', data: rsi24, xAxisIndex: xi, yAxisIndex: xi, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#a371f7' } },
      );
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
        bottom: 5, height: 20,
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
        text: title, left: 'center', top: 0,
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
        itemWidth: 14, itemHeight: 2,
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
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8b949e' }}>
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
    if (ema === null) ema = data[i];
    else ema = data[i] * k + ema * (1 - k);
    result.push(ema);
  }
  return result;
}

function calcKDJ(closePrices, highPrices, lowPrices, n = 9, m1 = 3, m2 = 3) {
  const len = closePrices.length;
  const kValues = new Array(len).fill(null);
  const dValues = new Array(len).fill(null);
  const jValues = new Array(len).fill(null);

  let prevK = 50, prevD = 50;
  for (let i = 0; i < len; i++) {
    const start = Math.max(0, i - n + 1);
    let lowN = Infinity, highN = -Infinity;
    for (let j = start; j <= i; j++) {
      if (lowPrices[j] < lowN) lowN = lowPrices[j];
      if (highPrices[j] > highN) highN = highPrices[j];
    }
    const range = highN - lowN;
    const rsv = range === 0 ? 50 : ((closePrices[i] - lowN) / range) * 100;

    const k = ((m1 - 1) / m1) * prevK + (1 / m1) * rsv;
    const d = ((m2 - 1) / m2) * prevD + (1 / m2) * k;
    const j = 3 * k - 2 * d;

    kValues[i] = +k.toFixed(2);
    dValues[i] = +d.toFixed(2);
    jValues[i] = +j.toFixed(2);
    prevK = k;
    prevD = d;
  }
  return { kValues, dValues, jValues };
}

function calcRSI(closePrices, period) {
  const result = new Array(closePrices.length).fill(null);
  const alpha = 1.0 / period;
  let avgGain = 0, avgLoss = 0;

  // Initialize with first `period` changes
  for (let i = 1; i <= period && i < closePrices.length; i++) {
    const change = closePrices[i] - closePrices[i - 1];
    if (change > 0) avgGain += change;
    else avgLoss += Math.abs(change);
  }
  avgGain /= period;
  avgLoss /= period;

  if (period < closePrices.length) {
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    result[period] = +(100 - 100 / (1 + rs)).toFixed(2);
  }

  for (let i = period + 1; i < closePrices.length; i++) {
    const change = closePrices[i] - closePrices[i - 1];
    const gain = change > 0 ? change : 0;
    const loss = change < 0 ? Math.abs(change) : 0;
    avgGain = avgGain * (1 - alpha) + gain * alpha;
    avgLoss = avgLoss * (1 - alpha) + loss * alpha;
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    result[i] = +(100 - 100 / (1 + rs)).toFixed(2);
  }
  return result;
}
