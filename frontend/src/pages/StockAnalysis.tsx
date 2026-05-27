import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Row, Col, Spin, Typography, Descriptions, Tabs, Table, Checkbox,
  Space, Empty, Tag,
} from 'antd';
import type { TableColumnsType } from 'antd';
import {
  FullscreenOutlined, FullscreenExitOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import StockSearch from '../components/StockSearch';
import KLineChart from '../components/KLineChart';
import { apiGet, apiPost } from '../utils/api';
import { formatPrice, formatPercent, formatVolume, formatAmount } from '../utils/formatters';
import type { StockRealtime, KLineItem, KLineObject, FundamentalRow, IntradayPoint, IndicatorConfig } from '../types';

const { Title, Text } = Typography;

interface StockAnalysisProps {
  isDark: boolean;
}

interface MAOption {
  label: string;
  value: number;
}

interface IndicatorCheckbox {
  label: string;
  value: string;
}

const maOptions: MAOption[] = [
  { label: 'MA5', value: 5 },
  { label: 'MA10', value: 10 },
  { label: 'MA20', value: 20 },
  { label: 'MA60', value: 60 },
  { label: 'MA120', value: 120 },
  { label: 'MA250', value: 250 },
];

const indicatorCheckboxes: IndicatorCheckbox[] = [
  { label: 'MACD', value: 'macd' },
  { label: 'KDJ', value: 'kdj' },
  { label: 'RSI', value: 'rsi' },
  { label: 'BOLL', value: 'boll' },
];

export default function StockAnalysis({ isDark }: StockAnalysisProps) {
  const { code } = useParams<{ code?: string }>();
  const navigate = useNavigate();
  const [stockInfo, setStockInfo] = useState<StockRealtime | null>(null);
  const [klineData, setKlineData] = useState<KLineItem[]>([]);
  const [fundamental, setFundamental] = useState<FundamentalRow[]>([]);
  const [intradayData, setIntradayData] = useState<IntradayPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [selectedMA, setSelectedMA] = useState<number[]>([5, 10, 20, 60]);
  const [selectedIndicators, setSelectedIndicators] = useState<string[]>(['macd']);
  const [activeBottomTab, setActiveBottomTab] = useState<string>('fundamental');

  const fetchStockData = useCallback(async (stockCode: string) => {
    if (!stockCode) return;
    setLoading(true);
    try {
      const [infoRes, klineRes, fundRes, intradayRes] = await Promise.allSettled([
        apiGet(`/stock/${stockCode}/realtime`),
        apiGet(`/stock/${stockCode}/kline`, { period: 'daily', count: 250 }),
        apiGet(`/stock/${stockCode}/fundamental`),
        apiGet(`/stock/${stockCode}/intraday`),
      ]);
      if (infoRes.status === 'fulfilled') setStockInfo(infoRes.value as StockRealtime);
      if (klineRes.status === 'fulfilled') {
        const kr = klineRes.value;
        const raw: (KLineItem | KLineObject)[] = Array.isArray(kr) ? kr as (KLineItem | KLineObject)[] : ((kr as { data?: KLineItem[]; kline?: KLineItem[] })?.data || (kr as { data?: KLineItem[]; kline?: KLineItem[] })?.kline || []);
        const kd: KLineItem[] = raw.map((d) => {
          if (Array.isArray(d)) return d as KLineItem;
          const obj = d as KLineObject;
          return [obj.date, obj.open, obj.high, obj.low, obj.close, obj.volume] as KLineItem;
        });
        setKlineData(kd);
      }
      if (fundRes.status === 'fulfilled') {
        const fd = fundRes.value;
        const list: FundamentalRow[] = Array.isArray(fd)
          ? fd as FundamentalRow[]
          : ((fd as { list?: FundamentalRow[] })?.list || Object.entries(fd as Record<string, unknown>).map(([k, v]) => ({ field: k, value: String(v) })));
        setFundamental(list);
      }
      if (intradayRes.status === 'fulfilled') {
        const id = Array.isArray(intradayRes.value) ? intradayRes.value as IntradayPoint[] : [];
        setIntradayData(id);
      }
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (code) fetchStockData(code);
  }, [code, fetchStockData]);

  const handleSearchSelect = (val: string) => {
    navigate(`/stock/${val}`);
  };

  const klineIndicators: IndicatorConfig = {
    ma_periods: selectedMA,
    macd: selectedIndicators.includes('macd'),
    kdj: selectedIndicators.includes('kdj'),
    rsi: selectedIndicators.includes('rsi'),
    boll: selectedIndicators.includes('boll'),
  };

  const price = stockInfo?.price ?? stockInfo?.current_price;
  const change = stockInfo?.change;
  const changePct = stockInfo?.change_pct ?? stockInfo?.pct_change;
  const isUp = Number(change) > 0;
  const isDown = Number(change) < 0;
  const priceColor = isUp ? 'var(--color-danger)' : isDown ? 'var(--color-success)' : 'var(--color-text-secondary)';

  const fundamentalColumns: TableColumnsType<FundamentalRow> = fundamental.length > 0
    ? Object.keys(fundamental[0] || {}).map((k) => ({
        title: k,
        dataIndex: k,
        key: k,
        ellipsis: true,
      }))
    : [];

  const intradayOption = buildIntradayOption(intradayData, isDark);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Row gutter={16} align="middle">
        <Col flex="auto">
          <StockSearch onSelect={handleSearchSelect} />
        </Col>
        {stockInfo && (
          <Col>
            <Tag color="var(--color-primary)" style={{ fontSize: 13, padding: '2px 10px' }}>
              {stockInfo.industry || stockInfo.sector || ''}
            </Tag>
          </Col>
        )}
      </Row>

      {!code && (
        <Card>
          <Empty description="请输入股票代码开始分析" />
        </Card>
      )}

      {code && (
        <Spin spinning={loading} size="large">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {stockInfo && (
              <Card styles={{ body: { padding: '16px 24px' } }}>
                <Row gutter={24} align="middle">
                  <Col>
                    <Title level={4} style={{ margin: 0, color: 'var(--color-text)' }}>
                      {stockInfo.name}{' '}
                      <Text type="secondary" style={{ fontSize: 14 }}>{stockInfo.code}</Text>
                    </Title>
                  </Col>
                  <Col>
                    <span style={{ fontSize: 28, fontWeight: 700, color: priceColor }}>
                      {formatPrice(price as number)}
                    </span>
                  </Col>
                  <Col>
                    <span style={{ fontSize: 16, fontWeight: 600, color: priceColor }}>
                      {isUp ? '+' : ''}{typeof change === 'number' ? change.toFixed(2) : '--'}
                    </span>
                  </Col>
                  <Col>
                    <span style={{ fontSize: 16, fontWeight: 600, color: priceColor }}>
                      {typeof changePct === 'number' ? formatPercent(changePct) : '--'}
                    </span>
                  </Col>
                </Row>
              </Card>
            )}

            <Row gutter={16}>
              <Col xs={24} lg={20}>
                <Card styles={{ body: { padding: 0 } }}>
                  <div style={{ position: 'relative' }}>
                    <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 2 }}>
                      <Space>
                        <Tag
                          icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                          style={{ cursor: 'pointer' }}
                          onClick={() => setIsFullscreen(!isFullscreen)}
                        >
                          {isFullscreen ? '退出全屏' : '全屏'}
                        </Tag>
                      </Space>
                    </div>
                    <KLineChart
                      data={klineData}
                      indicators={klineIndicators}
                      title=""
                      height={isFullscreen ? window.innerHeight - 200 : 600}
                      theme={isDark ? 'dark' : 'light'}
                    />
                  </div>
                </Card>
              </Col>
              <Col xs={24} lg={4}>
                <Card size="small" styles={{ body: { padding: 12 } }}>
                  <div style={{ marginBottom: 16 }}>
                    <Text strong style={{ display: 'block', marginBottom: 8, color: 'var(--color-text)' }}>
                      均线选择
                    </Text>
                    <Checkbox.Group
                      value={selectedMA}
                      onChange={setSelectedMA}
                      style={{ display: 'flex', flexDirection: 'column', gap: 6 }}
                    >
                      {maOptions.map((o) => (
                        <Checkbox key={o.value} value={o.value}>
                          {o.label}
                        </Checkbox>
                      ))}
                    </Checkbox.Group>
                  </div>
                  <div>
                    <Text strong style={{ display: 'block', marginBottom: 8, color: 'var(--color-text)' }}>
                      副图指标
                    </Text>
                    <Checkbox.Group
                      value={selectedIndicators}
                      onChange={setSelectedIndicators}
                      style={{ display: 'flex', flexDirection: 'column', gap: 6 }}
                    >
                      {indicatorCheckboxes.map((o) => (
                        <Checkbox key={o.value} value={o.value}>
                          {o.label}
                        </Checkbox>
                      ))}
                    </Checkbox.Group>
                  </div>
                </Card>
              </Col>
            </Row>

            <Card styles={{ body: { padding: '0 16px 16px' } }}>
              <Tabs
                activeKey={activeBottomTab}
                onChange={setActiveBottomTab}
                items={[
                  {
                    key: 'fundamental',
                    label: '基本面',
                    children: fundamental.length > 0 ? (
                      <Table<FundamentalRow>
                        dataSource={fundamental}
                        columns={fundamentalColumns}
                        rowKey={(_, i) => String(i)}
                        size="small"
                        pagination={false}
                        scroll={{ x: 600 }}
                        locale={{ emptyText: <Empty description="暂无基本面数据" /> }}
                      />
                    ) : (
                      <Empty description="暂无基本面数据" />
                    ),
                  },
                  {
                    key: 'intraday',
                    label: '分时图',
                    children: intradayData.length > 0 ? (
                      <ReactECharts option={intradayOption} style={{ height: 300 }} />
                    ) : (
                      <Empty description="暂无分时数据" />
                    ),
                  },
                ]}
              />
            </Card>
          </div>
        </Spin>
      )}
    </div>
  );
}

function buildIntradayOption(data: IntradayPoint[], isDark: boolean): Record<string, unknown> {
  if (!data || data.length === 0) return {};
  const textColor = isDark ? '#e6edf3' : '#1f1f1f';
  const subTextColor = isDark ? '#8b949e' : '#666666';
  const gridBorderColor = isDark ? '#30363d' : '#d9d9d9';

  const times = data.map((d) => d.time);
  const prices = data.map((d) => d.price);
  const volumes = data.map((d) => d.volume);

  const basePrice = prices[0];

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: isDark ? '#1c2028' : '#ffffff',
      borderColor: gridBorderColor,
      textStyle: { color: textColor },
    },
    grid: [
      { left: 60, right: 30, top: 10, height: '55%' },
      { left: 60, right: 30, top: '75%', height: '18%' },
    ],
    xAxis: [
      {
        type: 'category',
        data: times,
        gridIndex: 0,
        axisLabel: { show: false },
        axisLine: { lineStyle: { color: gridBorderColor } },
      },
      {
        type: 'category',
        data: times,
        gridIndex: 1,
        axisLabel: { color: subTextColor, fontSize: 10 },
        axisLine: { lineStyle: { color: gridBorderColor } },
      },
    ],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.3 } },
        axisLabel: { color: subTextColor },
      },
      {
        type: 'value',
        gridIndex: 1,
        splitNumber: 2,
        splitLine: { show: false },
        axisLabel: {
          color: subTextColor,
          fontSize: 10,
          formatter: (v: number) => (v >= 1e4 ? `${(v / 1e4).toFixed(0)}万` : String(v)),
        },
      },
    ],
    series: [
      {
        name: '价格',
        type: 'line',
        data: prices,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#58a6ff' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(88,166,255,0.2)' },
              { offset: 1, color: 'rgba(88,166,255,0)' },
            ],
          },
        },
        markLine: {
          silent: true,
          symbol: 'none',
          data: [{ yAxis: basePrice, lineStyle: { color: '#e6c73a', type: 'dashed', width: 1 } }],
          label: { show: true, formatter: basePrice.toFixed(2), color: subTextColor },
        },
      },
      {
        name: '成交量',
        type: 'bar',
        data: volumes.map((v, i) => ({
          value: v,
          itemStyle: {
            color: i > 0 && prices[i] >= prices[i - 1] ? 'rgba(248,81,73,0.5)' : 'rgba(63,185,80,0.5)',
          },
        })),
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
    ],
  };
}
