import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';
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

export default function MarketOverview({ data, loading = false }: MarketOverviewProps) {
  const indices = data && data.length > 0 ? data : defaultIndices;

  return (
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
  );
}
