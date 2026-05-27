import React, { useState } from 'react';
import {
  Card, Row, Col, Select, DatePicker, InputNumber, Button, Table, Spin,
  Typography, Statistic, Space, Form, Input, Tabs, Empty,
} from 'antd';
import type { TableColumnsType } from 'antd';
import {
  LineChartOutlined, BarChartOutlined, TrophyOutlined,
  PercentageOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import EquityCurve from '../components/EquityCurve';
import { apiGet, apiPost } from '../utils/api';
import type { BacktestResult, TradeRecord, FactorResult } from '../types';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

interface QuantStrategyProps {
  isDark: boolean;
}

interface StrategyOption {
  value: string;
  label: string;
}

const strategies: StrategyOption[] = [
  { value: 'dual_ma', label: '双均线策略' },
  { value: 'macd', label: 'MACD策略' },
  { value: 'momentum', label: '动量策略' },
  { value: 'turtle', label: '海龟交易策略' },
];

const strategyDescs: Record<string, string> = {
  dual_ma: '双均线策略通过短期均线和长期均线的交叉来产生交易信号。当短期均线上穿长期均线时买入，下穿时卖出。',
  macd: 'MACD策略利用MACD指标的金叉和死叉作为买卖信号，结合MACD柱状图判断趋势强度。',
  momentum: '动量策略基于股票价格的动量变化，当动量由负转正时买入，由正转负时卖出。',
  turtle: '海龟交易策略是经典的趋势跟踪系统，当价格突破N日最高价时入场，跌破M日最低价时离场。',
};

export default function QuantStrategy({ isDark }: QuantStrategyProps) {
  const [strategy, setStrategy] = useState<string>('dual_ma');
  const [form] = Form.useForm();
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [equityCurve, setEquityCurve] = useState<BacktestResult['equity_curve']>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('backtest');

  const [factorResults, setFactorResults] = useState<FactorResult[]>([]);
  const [factorLoading, setFactorLoading] = useState<boolean>(false);
  const [factorCode, setFactorCode] = useState<string>('');

  async function runBacktest() {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const params = {
        strategy,
        stock_code: values.stock_code,
        start_date: values.date_range?.[0]?.format('YYYY-MM-DD'),
        end_date: values.date_range?.[1]?.format('YYYY-MM-DD'),
        initial_capital: values.initial_capital || 1000000,
        commission: values.commission || 0.0003,
        short_period: values.short_period,
        long_period: values.long_period,
      };
      const res = await apiPost('/quant/backtest', params);
      const result = res as BacktestResult;
      setBacktestResult(result);
      setEquityCurve(result?.equity_curve || []);
      setTrades(result?.trades || []);
    } catch {
      // handled by interceptor or form validation
    } finally {
      setLoading(false);
    }
  }

  async function runFactorSelect() {
    if (!factorCode.trim()) return;
    setFactorLoading(true);
    try {
      const res = await apiPost('/quant/factor-select', { stock_codes: factorCode.split(',').map((s) => s.trim()) });
      setFactorResults(Array.isArray(res) ? res as FactorResult[] : []);
    } catch {
      setFactorResults([]);
    } finally {
      setFactorLoading(false);
    }
  }

  const metrics = backtestResult?.metrics || {};
  const metricCards = [
    { title: '总收益', value: metrics.total_return, suffix: '%', color: (metrics.total_return || 0) >= 0 ? 'var(--color-danger)' : 'var(--color-success)', icon: <TrophyOutlined /> },
    { title: '年化收益', value: metrics.annual_return, suffix: '%', color: (metrics.annual_return || 0) >= 0 ? 'var(--color-danger)' : 'var(--color-success)', icon: <LineChartOutlined /> },
    { title: '最大回撤', value: metrics.max_drawdown, suffix: '%', color: 'var(--color-danger)', icon: <BarChartOutlined /> },
    { title: '夏普比率', value: metrics.sharpe_ratio, suffix: '', color: (metrics.sharpe_ratio || 0) >= 1 ? 'var(--color-success)' : 'var(--color-text-secondary)', icon: <ThunderboltOutlined /> },
    { title: '胜率', value: metrics.win_rate, suffix: '%', color: (metrics.win_rate || 0) >= 50 ? 'var(--color-success)' : 'var(--color-text-secondary)', icon: <PercentageOutlined /> },
  ];

  const tradeColumns: TableColumnsType<TradeRecord> = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 80,
      render: (v: string) => (
        <Text style={{ color: v === '买入' || v === 'BUY' ? 'var(--color-danger)' : 'var(--color-success)', fontWeight: 600 }}>
          {v}
        </Text>
      ),
    },
    { title: '价格', dataIndex: 'price', key: 'price', width: 100, render: (v: number | null) => v !== null ? Number(v).toFixed(2) : '--' },
    { title: '数量', dataIndex: 'shares', key: 'shares', width: 100, render: (v: number | null) => v !== null ? Number(v).toLocaleString() : '--' },
    {
      title: '盈亏',
      dataIndex: 'pnl',
      key: 'pnl',
      width: 100,
      render: (v: number | null | undefined) => {
        if (v === null || v === undefined) return '--';
        const num = Number(v);
        return (
          <Text style={{ color: num >= 0 ? 'var(--color-danger)' : 'var(--color-success)', fontWeight: 600 }}>
            {num >= 0 ? '+' : ''}{num.toFixed(2)}
          </Text>
        );
      },
    },
  ];

  const factorColumns: TableColumnsType<FactorResult> = [
    { title: '代码', dataIndex: 'code', key: 'code', width: 100 },
    { title: '名称', dataIndex: 'name', key: 'name', width: 100 },
    { title: '综合评分', dataIndex: 'score', key: 'score', width: 100, render: (v: number) => v !== undefined ? Number(v).toFixed(2) : '--' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <Title level={4} style={{ margin: 0, color: 'var(--color-text)' }}>
        量化策略
      </Title>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'backtest',
            label: '策略回测',
            children: (
              <Row gutter={20}>
                <Col xs={24} lg={7}>
                  <Card title="参数配置" styles={{ body: { padding: '16px' } }}>
                    <Form form={form} layout="vertical">
                      <Form.Item label="策略选择">
                        <Select
                          value={strategy}
                          onChange={setStrategy}
                          options={strategies}
                          style={{ width: '100%' }}
                        />
                      </Form.Item>
                      <div style={{ marginBottom: 16, color: 'var(--color-text-secondary)', fontSize: 13 }}>
                        {strategyDescs[strategy]}
                      </div>

                      <Form.Item name="stock_code" label="股票代码" rules={[{ required: true, message: '请输入股票代码' }]}>
                        <Input placeholder="如 600519" />
                      </Form.Item>

                      <Form.Item name="date_range" label="回测区间">
                        <RangePicker style={{ width: '100%' }} />
                      </Form.Item>

                      <Form.Item name="initial_capital" label="初始资金">
                        <InputNumber min={10000} step={100000} style={{ width: '100%' }} formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
                      </Form.Item>

                      <Form.Item name="commission" label="佣金率">
                        <InputNumber min={0} max={0.01} step={0.0001} style={{ width: '100%' }} />
                      </Form.Item>

                      {strategy === 'dual_ma' && (
                        <>
                          <Form.Item name="short_period" label="短期均线" initialValue={5}>
                            <InputNumber min={1} max={120} style={{ width: '100%' }} />
                          </Form.Item>
                          <Form.Item name="long_period" label="长期均线" initialValue={20}>
                            <InputNumber min={5} max={250} style={{ width: '100%' }} />
                          </Form.Item>
                        </>
                      )}

                      <Button
                        type="primary"
                        icon={<ThunderboltOutlined />}
                        block
                        size="large"
                        loading={loading}
                        onClick={runBacktest}
                      >
                        运行回测
                      </Button>
                    </Form>
                  </Card>
                </Col>

                <Col xs={24} lg={17}>
                  <Spin spinning={loading}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                      <Card styles={{ body: { padding: '16px' } }}>
                        <Row gutter={[16, 16]}>
                          {metricCards.map((m) => (
                            <Col xs={12} sm={8} key={m.title}>
                              <Statistic
                                title={m.title}
                                value={m.value !== null && m.value !== undefined ? Number(m.value).toFixed(2) : '--'}
                                suffix={m.suffix}
                                valueStyle={{ color: m.color, fontSize: 20, fontWeight: 700 }}
                                prefix={m.icon}
                              />
                            </Col>
                          ))}
                        </Row>
                      </Card>

                      <Card title="收益曲线" styles={{ body: { padding: '12px' } }}>
                        <EquityCurve
                          data={equityCurve}
                          height={380}
                          theme={isDark ? 'dark' : 'light'}
                        />
                      </Card>

                      <Card title="交易记录" styles={{ body: { padding: '0' } }}>
                        <Table<TradeRecord>
                          dataSource={trades}
                          columns={tradeColumns}
                          rowKey={(r) => `${r.date}-${r.action}-${r.price}`}
                          size="small"
                          pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 笔交易` }}
                          scroll={{ x: 500 }}
                          locale={{ emptyText: <Empty description="请运行回测查看交易记录" /> }}
                        />
                      </Card>
                    </div>
                  </Spin>
                </Col>
              </Row>
            ),
          },
          {
            key: 'factor',
            label: '多因子选股',
            children: (
              <Spin spinning={factorLoading}>
                <Card styles={{ body: { padding: '16px' } }}>
                  <Space style={{ marginBottom: 16 }} wrap>
                    <Input
                      value={factorCode}
                      onChange={(e) => setFactorCode(e.target.value)}
                      placeholder="输入股票代码，用逗号分隔 (如: 600519,000858,601318)"
                      style={{ width: 400 }}
                    />
                    <Button type="primary" loading={factorLoading} onClick={runFactorSelect}>
                      因子评分
                    </Button>
                  </Space>
                  {factorResults.length > 0 ? (
                    <Table<FactorResult>
                      dataSource={factorResults}
                      columns={factorColumns}
                      rowKey={(_, i) => String(i)}
                      size="small"
                      pagination={{ pageSize: 20 }}
                      scroll={{ x: 600 }}
                    />
                  ) : (
                    <Empty description="请输入股票代码进行因子分析" />
                  )}
                </Card>
              </Spin>
            ),
          },
        ]}
      />
    </div>
  );
}
