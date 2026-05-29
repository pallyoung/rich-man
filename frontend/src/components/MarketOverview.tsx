import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, ClockCircleOutlined } from '@ant-design/icons';
import type { MarketIndex } from '../types';

interface MarketOverviewProps {
  data?: MarketIndex[];
  loading?: boolean;
}

const defaultIndices: MarketIndex[] = [
  { name: '上证指数', code: 'sh000001' },
  { name: '深证成指', code: 'sz399001' },
  { name: '创业板指', code: 'sz399006' },
  { name: '科创50', code: 'sh000688' },
];

function isStaleData(dataDate?: string): boolean {
  if (!dataDate) return false;
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  return dataDate !== today;
}

export default function MarketOverview({ data, loading = false }: MarketOverviewProps) {
  const indices = data && data.length > 0 ? data : defaultIndices;
  const stale = indices.some((i) => isStaleData(i.data_date));
  const dataDate = indices[0]?.data_date;

  return (
    <div>
      {stale && dataDate && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginBottom: 10,
          padding: '6px 12px',
          borderRadius: 6,
          background: 'rgba(250, 173, 20, 0.1)',
          border: '1px solid rgba(250, 173, 20, 0.3)',
          color: '#faad14',
          fontSize: 13,
        }}>
          <ClockCircleOutlined />
          <span>当前显示的是 <b>{dataDate}</b> 的收盘数据，非实时行情</span>
        </div>
      )}
      <Row gutter={[16, 16]}>
        {indices.map((item) => {
          const price = item.price ?? item.current_price ?? '--';
          const change = item.change ?? '--';
          const changePct = item.change_pct ?? item.pct_change ?? '--';
          const isUp = Number(change) > 0;
          const isDown = Number(change) < 0;
          const color = isUp ? 'var(--color-danger)' : isDown ? 'var(--color-success)' : 'var(--color-text-secondary)';

          return (
            <Col xs={24} sm={12} lg={6} key={item.code || item.name}>
              <Card
                hoverable
                loading={loading}
                style={{ borderTop: `3px solid ${color}` }}
                styles={{ body: { padding: '16px 20px' } }}
              >
                <Statistic
                  title={
                    <span style={{ fontSize: 15, fontWeight: 600 }}>
                      {item.name}
                    </span>
                  }
                  value={price as number}
                  precision={2}
                  valueStyle={{ color, fontSize: 24, fontWeight: 700 }}
                  prefix={
                    isUp ? (
                      <ArrowUpOutlined />
                    ) : isDown ? (
                      <ArrowDownOutlined />
                    ) : (
                      <MinusOutlined />
                    )
                  }
                  suffix={
                    <span style={{ fontSize: 14, marginLeft: 8 }}>
                      {isUp ? '+' : ''}
                      {typeof change === 'number' ? change.toFixed(2) : change}
                      {' '}
                      ({typeof changePct === 'number' ? `${changePct > 0 ? '+' : ''}${changePct.toFixed(2)}%` : changePct})
                    </span>
                  }
                />
              </Card>
            </Col>
          );
        })}
      </Row>
    </div>
  );
}
