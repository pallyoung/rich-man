import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, List, Spin, Typography, Tag, Input, Tabs, Empty, Space, Avatar,
} from 'antd';
import {
  ClockCircleOutlined, GlobalOutlined, FileTextOutlined, SearchOutlined, FireOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import SentimentGauge from '../components/SentimentGauge';
import api from '../utils/api';

const { Title, Text, Paragraph } = Typography;

export default function NewsCenter({ isDark }) {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sentiment, setSentiment] = useState({ score: 50, keywords: [] });
  const [sentimentLoading, setSentimentLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('latest');
  const [announceCode, setAnnounceCode] = useState('');
  const [announcements, setAnnouncements] = useState([]);
  const [announceLoading, setAnnounceLoading] = useState(false);

  useEffect(() => {
    fetchNews();
    fetchSentiment();
  }, []);

  async function fetchNews() {
    setLoading(true);
    try {
      const res = await api.get('/news/latest', { params: { limit: 30 } });
      setNews(Array.isArray(res) ? res : []);
    } catch {
      setNews([]);
    } finally {
      setLoading(false);
    }
  }

  async function fetchSentiment() {
    setSentimentLoading(true);
    try {
      const res = await api.get('/news/sentiment');
      if (res) {
        setSentiment({
          score: res.sentiment_index ?? res.score ?? res.sentiment ?? 50,
          keywords: res.news_sentiments
            ? res.news_sentiments.map(n => n.title).slice(0, 8)
            : res.keywords || [],
        });
      }
    } catch {
      // keep default
    } finally {
      setSentimentLoading(false);
    }
  }

  const fetchAnnouncements = useCallback(async (code) => {
    if (!code.trim()) return;
    setAnnounceLoading(true);
    try {
      const res = await api.get('/news/announcements', { params: { stock_code: code.trim() } });
      setAnnouncements(Array.isArray(res) ? res : []);
    } catch {
      setAnnouncements([]);
    } finally {
      setAnnounceLoading(false);
    }
  }, []);

  const keywordOption = buildKeywordCloud(sentiment.keywords, isDark);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <Title level={4} style={{ margin: 0, color: 'var(--color-text)' }}>
        资讯中心
      </Title>

      <Row gutter={20}>
        <Col xs={24} lg={17}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'latest',
                label: '最新资讯',
                children: (
                  <Spin spinning={loading}>
                    {news.length > 0 ? (
                      <List
                        itemLayout="vertical"
                        dataSource={news}
                        pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条资讯` }}
                        renderItem={(item) => (
                          <List.Item
                            style={{
                              padding: '16px 20px',
                              marginBottom: 8,
                              background: 'var(--color-card-bg)',
                              borderRadius: 8,
                              border: '1px solid var(--color-border)',
                            }}
                            actions={[
                              <Space key="source">
                                <GlobalOutlined />
                                <Text style={{ color: 'var(--color-text-secondary)' }}>{item.source || '未知来源'}</Text>
                              </Space>,
                              <Space key="time">
                                <ClockCircleOutlined />
                                <Text style={{ color: 'var(--color-text-secondary)' }}>{item.time || item.publish_time || '--'}</Text>
                              </Space>,
                            ]}
                          >
                            <List.Item.Meta
                              title={
                                <a
                                  href={item.url || '#'}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{ color: 'var(--color-text)', fontSize: 15, fontWeight: 600 }}
                                >
                                  {item.title}
                                </a>
                              }
                              description={
                                <Paragraph
                                  ellipsis={{ rows: 2 }}
                                  style={{ color: 'var(--color-text-secondary)', margin: '8px 0 0' }}
                                >
                                  {item.summary || item.content || ''}
                                </Paragraph>
                              }
                            />
                            {item.tags && (
                              <Space size={4} style={{ marginTop: 8 }}>
                                {(Array.isArray(item.tags) ? item.tags : [item.tags]).map((t) => (
                                  <Tag key={t} size="small">{t}</Tag>
                                ))}
                              </Space>
                            )}
                          </List.Item>
                        )}
                      />
                    ) : (
                      <Empty description="暂无资讯" />
                    )}
                  </Spin>
                ),
              },
              {
                key: 'announcements',
                label: '个股公告',
                children: (
                  <div>
                    <Space style={{ marginBottom: 16 }}>
                      <Input
                        value={announceCode}
                        onChange={(e) => setAnnounceCode(e.target.value)}
                        onPressEnter={() => fetchAnnouncements(announceCode)}
                        placeholder="输入股票代码查询公告"
                        prefix={<SearchOutlined />}
                        style={{ width: 300 }}
                      />
                      <button
                        style={{
                          padding: '4px 16px',
                          background: 'var(--color-primary)',
                          color: '#fff',
                          border: 'none',
                          borderRadius: 6,
                          cursor: 'pointer',
                        }}
                        onClick={() => fetchAnnouncements(announceCode)}
                      >
                        查询
                      </button>
                    </Space>
                    <Spin spinning={announceLoading}>
                      {announcements.length > 0 ? (
                        <List
                          dataSource={announcements}
                          pagination={{ pageSize: 10 }}
                          renderItem={(item) => (
                            <List.Item
                              style={{
                                padding: '12px 16px',
                                background: 'var(--color-card-bg)',
                                borderRadius: 6,
                                border: '1px solid var(--color-border)',
                                marginBottom: 8,
                              }}
                            >
                              <List.Item.Meta
                                avatar={<Avatar icon={<FileTextOutlined />} style={{ background: 'var(--color-primary)' }} />}
                                title={
                                  <a
                                    href={item.url || '#'}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ color: 'var(--color-text)' }}
                                  >
                                    {item.title}
                                  </a>
                                }
                                description={
                                  <Space>
                                    <Text style={{ color: 'var(--color-text-secondary)', fontSize: 12 }}>
                                      {item.date || item.publish_time || '--'}
                                    </Text>
                                    {item.type && <Tag>{item.type}</Tag>}
                                  </Space>
                                }
                              />
                            </List.Item>
                          )}
                        />
                      ) : (
                        <Empty description="请输入股票代码查询公告" />
                      )}
                    </Spin>
                  </div>
                ),
              },
            ]}
          />
        </Col>

        <Col xs={24} lg={7}>
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            <Card title="市场情绪" styles={{ body: { padding: '0 12px' } }}>
              <Spin spinning={sentimentLoading}>
                <SentimentGauge value={sentiment.score} theme={isDark ? 'dark' : 'light'} />
              </Spin>
            </Card>

            <Card title="热点关键词" styles={{ body: { padding: '12px' } }}>
              {sentiment.keywords && sentiment.keywords.length > 0 ? (
                <ReactECharts option={keywordOption} style={{ height: 280 }} />
              ) : (
                <Empty description="暂无关键词数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  );
}

function buildKeywordCloud(keywords, isDark) {
  if (!keywords || keywords.length === 0) return {};

  const textColor = isDark ? '#e6edf3' : '#1f1f1f';
  const subTextColor = isDark ? '#8b949e' : '#666666';
  const gridBorderColor = isDark ? '#30363d' : '#d9d9d9';

  const sorted = [...keywords]
    .map((kw) => ({
      name: typeof kw === 'string' ? kw : kw.text || kw.name,
      value: typeof kw === 'object' ? kw.weight || kw.count || 10 : 10,
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);

  const colors = ['#58a6ff', '#f97583', '#e6c73a', '#3fb950', '#a371f7', '#f85149', '#79c0ff', '#ffa657', '#d2a8ff', '#7ee787'];

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: isDark ? '#1c2028' : '#ffffff',
      borderColor: gridBorderColor,
      textStyle: { color: textColor },
    },
    grid: { left: 10, right: 40, top: 10, bottom: 10, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: gridBorderColor, opacity: 0.3 } },
      axisLabel: { color: subTextColor, fontSize: 10 },
    },
    yAxis: {
      type: 'category',
      data: sorted.map((s) => s.name).reverse(),
      axisLabel: { color: textColor, fontSize: 12 },
      axisLine: { lineStyle: { color: gridBorderColor } },
    },
    series: [
      {
        type: 'bar',
        data: sorted
          .map((s) => s.value)
          .reverse()
          .map((v, i) => ({
            value: v,
            itemStyle: { color: colors[(sorted.length - 1 - i) % colors.length] },
          })),
        barWidth: '60%',
        label: {
          show: true,
          position: 'right',
          color: subTextColor,
          fontSize: 11,
        },
      },
    ],
  };
}
