import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Table, Spin, Typography, Empty } from 'antd';
import ReactECharts from 'echarts-for-react';
import MarketOverview from '../components/MarketOverview';
import SentimentGauge from '../components/SentimentGauge';
import api from '../utils/api';
import { formatPercent, getPercentColor } from '../utils/formatters';

const { Title } = Typography;

export default function Dashboard({ isDark }) {
  const [overview, setOverview] = useState(null);
  const [sectors, setSectors] = useState([]);
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    setLoading(true);
    try {
      const [ovRes, secRes, sigRes] = await Promise.allSettled([
        api.get('/market/overview'),
        api.get('/market/sectors'),
        api.get('/trend/signals'),
      ]);
      if (ovRes.status === 'fulfilled') setOverview(ovRes.value);
      if (secRes.status === 'fulfilled') {
        const sd = Array.isArray(secRes.value) ? secRes.value : [];
        setSectors(sd.slice(0, 10));
      }
      if (sigRes.status === 'fulfilled') {
        setSignals(Array.isArray(sigRes.value) ? sigRes.value.slice(0, 10) : []);
      }
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false);
    }
  }

  const upDownOption = buildUpDownChart(overview, isDark);
  const sectorBarOption = buildSectorBarChart(sectors, isDark);
  const sentimentValue = overview?.sentiment ?? 50;

  const signalColumns = [
    { title: '股票代码', dataIndex: 'stock_code', key: 'stock_code' },
    { title: '股票名称', dataIndex: 'stock_name', key: 'stock_name' },
    {
      title: '信号类型',
      dataIndex: 'signal_type',
      key: 'signal_type',
      render: (v) => (
        <span style={{ color: v === '买入' || v === 'BUY' ? '#f85149' : '#3fb950', fontWeight: 600 }}>
          {v}
        </span>
      ),
    },
    { title: '信号日期', dataIndex: 'signal_date', key: 'signal_date' },
    {
      title: '信号强度',
      dataIndex: 'strength',
      key: 'strength',
      render: (v) => {
        if (v === null || v === undefined) return '--';
        const pct = Math.round(v * 100);
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div
              style={{
                flex: 1,
                height: 6,
                background: 'var(--color-border)',
                borderRadius: 3,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${pct}%`,
                  height: '100%',
                  background: pct > 60 ? '#f85149' : pct > 30 ? '#e6c73a' : '#3fb950',
                  borderRadius: 3,
                }}
              />
            </div>
            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{pct}%</span>
          </div>
        );
      },
    },
  ];

  return (
    <Spin spinning={loading} size="large">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <Title level={4} style={{ margin: 0, color: 'var(--color-text)' }}>
          市场总览
        </Title>

        <MarketOverview data={overview?.indices} loading={loading} />

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={14}>
            <Card
              title="涨跌家数统计"
              styles={{ body: { padding: '12px 16px' } }}
            >
              {upDownOption && upDownOption.series ? (
                <ReactECharts option={upDownOption} style={{ height: 280 }} />
              ) : (
                <Empty description="暂无涨跌数据" />
              )}
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card title="市场情绪" styles={{ body: { padding: '0 16px' } }}>
              <SentimentGauge value={sentimentValue} theme={isDark ? 'dark' : 'light'} />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={14}>
            <Card title="热门板块 TOP10" styles={{ body: { padding: '12px 16px' } }}>
              {sectors.length > 0 ? (
                <ReactECharts option={sectorBarOption} style={{ height: 320 }} />
              ) : (
                <Empty description="暂无板块数据" />
              )}
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card title="今日策略信号" styles={{ body: { padding: '0' } }}>
              <Table
                dataSource={signals}
                columns={signalColumns}
                rowKey={(r) => `${r.stock_code}-${r.signal_date}-${r.signal_type}`}
                size="small"
                pagination={false}
                locale={{ emptyText: <Empty description="暂无策略信号" /> }}
                scroll={{ x: 400 }}
              />
            </Card>
          </Col>
        </Row>
      </div>
    </Spin>
  );
}

function buildUpDownChart(overview, isDark) {
  if (!overview) return {};
  const up = overview.up_count ?? overview.up ?? 0;
  const down = overview.down_count ?? overview.down ?? 0;
  const flat = overview.flat_count ?? overview.flat ?? 0;

  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: ['上涨', '下跌', '平盘'],
      axisLabel: { color: isDark ? '#8b949e' : '#666666' },
      axisLine: { lineStyle: { color: isDark ? '#30363d' : '#d9d9d9' } },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: isDark ? '#30363d' : '#d9d9d9', opacity: 0.3 } },
      axisLabel: { color: isDark ? '#8b949e' : '#666666' },
    },
    series: [
      {
        type: 'bar',
        data: [
          { value: up, itemStyle: { color: '#f85149' } },
          { value: down, itemStyle: { color: '#3fb950' } },
          { value: flat, itemStyle: { color: '#8b949e' } },
        ],
        barWidth: '40%',
        label: { show: true, position: 'top', color: isDark ? '#e6edf3' : '#1f1f1f' },
      },
    ],
  };
}

function buildSectorBarChart(sectors, isDark) {
  if (!sectors || sectors.length === 0) return {};
  const sorted = [...sectors].sort((a, b) => (a.change_pct || 0) - (b.change_pct || 0));

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: isDark ? '#1c2028' : '#ffffff',
      borderColor: isDark ? '#30363d' : '#d9d9d9',
      textStyle: { color: isDark ? '#e6edf3' : '#1f1f1f' },
    },
    grid: { left: 80, right: 30, top: 10, bottom: 20 },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: isDark ? '#30363d' : '#d9d9d9', opacity: 0.3 } },
      axisLabel: {
        color: isDark ? '#8b949e' : '#666666',
        formatter: '{value}%',
      },
    },
    yAxis: {
      type: 'category',
      data: sorted.map((s) => s.name),
      axisLabel: { color: isDark ? '#e6edf3' : '#1f1f1f', fontSize: 11 },
      axisLine: { lineStyle: { color: isDark ? '#30363d' : '#d9d9d9' } },
    },
    series: [
      {
        type: 'bar',
        data: sorted.map((s) => ({
          value: s.change_pct ?? s.change ?? 0,
          itemStyle: {
            color: (s.change_pct || 0) >= 0 ? '#f85149' : '#3fb950',
          },
        })),
        barWidth: '60%',
        label: {
          show: true,
          position: 'right',
          formatter: (p) => `${p.value > 0 ? '+' : ''}${p.value.toFixed(2)}%`,
          color: isDark ? '#e6edf3' : '#1f1f1f',
          fontSize: 11,
        },
      },
    ],
  };
}
