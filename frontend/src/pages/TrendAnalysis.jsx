import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Table, Spin, Typography, Tag, Input, Button, Space, Empty,
} from 'antd';
import { SearchOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import api from '../utils/api';

const { Title, Text } = Typography;

export default function TrendAnalysis({ isDark }) {
  const [signals, setSignals] = useState([]);
  const [signalsLoading, setSignalsLoading] = useState(true);
  const [compareCodes, setCompareCodes] = useState([]);
  const [inputCode, setInputCode] = useState('');
  const [compareData, setCompareData] = useState([]);
  const [compareLoading, setCompareLoading] = useState(false);
  const [rotationData, setRotationData] = useState([]);
  const [rotationLoading, setRotationLoading] = useState(true);

  useEffect(() => {
    fetchSignals();
    fetchRotation();
  }, []);

  async function fetchSignals() {
    setSignalsLoading(true);
    try {
      const res = await api.get('/trend/signals');
      setSignals(Array.isArray(res) ? res : []);
    } catch {
      setSignals([]);
    } finally {
      setSignalsLoading(false);
    }
  }

  async function fetchRotation() {
    setRotationLoading(true);
    try {
      const res = await api.get('/trend/sector-rotation');
      setRotationData(Array.isArray(res) ? res : []);
    } catch {
      setRotationData([]);
    } finally {
      setRotationLoading(false);
    }
  }

  const fetchCompare = useCallback(async (codes) => {
    if (!codes || codes.length === 0) {
      setCompareData([]);
      return;
    }
    setCompareLoading(true);
    try {
      const res = await api.get('/trend/compare', { params: { codes: codes.join(',') } });
      setCompareData(Array.isArray(res) ? res : []);
    } catch {
      setCompareData([]);
    } finally {
      setCompareLoading(false);
    }
  }, []);

  const addCode = () => {
    const code = inputCode.trim();
    if (!code) return;
    if (compareCodes.includes(code)) {
      setInputCode('');
      return;
    }
    const next = [...compareCodes, code];
    setCompareCodes(next);
    setInputCode('');
    fetchCompare(next);
  };

  const removeCode = (code) => {
    const next = compareCodes.filter((c) => c !== code);
    setCompareCodes(next);
    fetchCompare(next);
  };

  const signalColumns = [
    {
      title: '股票代码',
      dataIndex: 'stock_code',
      key: 'stock_code',
      render: (v) => <Text strong style={{ color: 'var(--color-primary)' }}>{v}</Text>,
    },
    { title: '股票名称', dataIndex: 'stock_name', key: 'stock_name' },
    {
      title: '信号类型',
      dataIndex: 'signal_type',
      key: 'signal_type',
      render: (v) => {
        const isBuy = v === '买入' || v === 'BUY';
        return (
          <Tag color={isBuy ? 'red' : 'green'} style={{ fontWeight: 600 }}>
            {v}
          </Tag>
        );
      },
    },
    { title: '信号日期', dataIndex: 'signal_date', key: 'signal_date' },
    {
      title: '信号强度',
      dataIndex: 'strength',
      key: 'strength',
      render: (v) => {
        if (v === null || v === undefined) return '--';
        const pct = Math.round(Number(v) * 100);
        const color = pct > 70 ? '#f85149' : pct > 40 ? '#e6c73a' : '#3fb950';
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 6, background: 'var(--color-border)', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3 }} />
            </div>
            <span style={{ fontSize: 12, minWidth: 32, color: 'var(--color-text-secondary)' }}>{pct}%</span>
          </div>
        );
      },
    },
    {
      title: '趋势说明',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
  ];

  const compareChartOption = buildCompareChart(compareData, isDark);
  const rotationOption = buildRotationChart(rotationData, isDark);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <Title level={4} style={{ margin: 0, color: 'var(--color-text)' }}>
        趋势分析
      </Title>

      <Card title="策略信号仪表盘" styles={{ body: { padding: '0' } }}>
        <Spin spinning={signalsLoading}>
          <Table
            dataSource={signals}
            columns={signalColumns}
            rowKey={(r) => `${r.stock_code}-${r.signal_date}-${r.signal_type}`}
            pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条信号` }}
            scroll={{ x: 600 }}
            size="small"
            locale={{ emptyText: <Empty description="暂无策略信号" /> }}
          />
        </Spin>
      </Card>

      <Card title="多股对比分析" styles={{ body: { padding: '12px 16px' } }}>
        <Space style={{ marginBottom: 16 }} wrap>
          <Input
            value={inputCode}
            onChange={(e) => setInputCode(e.target.value)}
            onPressEnter={addCode}
            placeholder="输入股票代码"
            style={{ width: 200 }}
          />
          <Button icon={<PlusOutlined />} type="primary" onClick={addCode}>
            添加
          </Button>
          {compareCodes.map((c) => (
            <Tag
              key={c}
              closable
              onClose={() => removeCode(c)}
              color="var(--color-primary)"
            >
              {c}
            </Tag>
          ))}
        </Space>
        <Spin spinning={compareLoading}>
          {compareData.length > 0 || compareCodes.length > 0 ? (
            <ReactECharts option={compareChartOption} style={{ height: 400 }} />
          ) : (
            <Empty description="请输入股票代码进行对比" />
          )}
        </Spin>
      </Card>

      <Card title="板块轮动分析" styles={{ body: { padding: '12px 16px' } }}>
        <Spin spinning={rotationLoading}>
          {rotationData.length > 0 ? (
            <ReactECharts option={rotationOption} style={{ height: 450 }} />
          ) : (
            <Empty description="暂无板块轮动数据" />
          )}
        </Spin>
      </Card>
    </div>
  );
}

function buildCompareChart(data, isDark) {
  if (!data || data.length === 0) return {};

  const textColor = isDark ? '#e6edf3' : '#1f1f1f';
  const subTextColor = isDark ? '#8b949e' : '#666666';
  const gridBorderColor = isDark ? '#30363d' : '#d9d9d9';
  const colors = ['#58a6ff', '#f97583', '#e6c73a', '#3fb950', '#a371f7', '#f85149'];

  const seriesList = data.map((stock, idx) => {
    const basePrice = stock.prices?.[0] || stock.data?.[0]?.price || 1;
    const prices = (stock.prices || stock.data?.map((d) => d.price) || []).map(
      (p) => +((p / basePrice) * 100).toFixed(2)
    );
    return {
      name: stock.name || stock.code,
      type: 'line',
      data: prices,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 2, color: colors[idx % colors.length] },
    };
  });

  const dates = data[0]?.dates || data[0]?.data?.map((d) => d.date) || [];

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: isDark ? '#1c2028' : '#ffffff',
      borderColor: gridBorderColor,
      textStyle: { color: textColor },
    },
    legend: {
      data: data.map((s) => s.name || s.code),
      top: 0,
      textStyle: { color: subTextColor },
    },
    grid: { left: 60, right: 30, top: 40, bottom: 30 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { color: subTextColor, fontSize: 10 },
      axisLine: { lineStyle: { color: gridBorderColor } },
    },
    yAxis: {
      type: 'value',
      name: '归一化(%)',
      nameTextStyle: { color: subTextColor },
      splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.3 } },
      axisLabel: { color: subTextColor },
    },
    series: seriesList,
  };
}

function buildRotationChart(data, isDark) {
  if (!data || data.length === 0) return {};

  const textColor = isDark ? '#e6edf3' : '#1f1f1f';
  const subTextColor = isDark ? '#8b949e' : '#666666';
  const gridBorderColor = isDark ? '#30363d' : '#d9d9d9';

  const indicators = data.map((d) => ({ name: d.name, max: 100 }));
  const values = data.map((d) => d.score ?? d.value ?? 50);

  return {
    backgroundColor: 'transparent',
    tooltip: {
      backgroundColor: isDark ? '#1c2028' : '#ffffff',
      borderColor: gridBorderColor,
      textStyle: { color: textColor },
    },
    radar: {
      indicator: indicators,
      shape: 'polygon',
      splitNumber: 5,
      name: { textStyle: { color: textColor, fontSize: 12 } },
      splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.5 } },
      splitArea: { areaStyle: { color: ['transparent'] } },
      axisLine: { lineStyle: { color: gridBorderColor, opacity: 0.5 } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: values,
            name: '板块动量',
            lineStyle: { color: '#58a6ff', width: 2 },
            areaStyle: { color: 'rgba(88,166,255,0.2)' },
            itemStyle: { color: '#58a6ff' },
          },
        ],
      },
    ],
  };
}
