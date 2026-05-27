import React, { useState, useEffect, useCallback } from 'react';
import { Card, Table, Tabs, Spin, Typography, Empty } from 'antd';
import type { TableColumnsType, TablePaginationConfig } from 'antd';
import type { SorterResult, FilterValue } from 'antd/es/table/interface';
import { useNavigate } from 'react-router-dom';
import HeatMap from '../components/HeatMap';
import { apiGet } from '../utils/api';
import { formatPrice, formatPercent, getPercentColor, formatVolume, formatAmount } from '../utils/formatters';
import type { StockRankItem, SectorData } from '../types';

const { Title } = Typography;

interface MarketCenterProps {
  isDark: boolean;
}

interface SortInfo {
  field: string;
  order: 'ascend' | 'descend';
}

export default function MarketCenter({ isDark }: MarketCenterProps) {
  const [activeTab, setActiveTab] = useState<string>('ranking');
  const [ranking, setRanking] = useState<StockRankItem[]>([]);
  const [sectors, setSectors] = useState<SectorData[]>([]);
  const [limitUp, setLimitUp] = useState<StockRankItem[]>([]);
  const [limitDown, setLimitDown] = useState<StockRankItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [pagination, setPagination] = useState<TablePaginationConfig>({ current: 1, pageSize: 20, total: 0 });
  const [sortInfo, setSortInfo] = useState<SortInfo>({ field: 'change_pct', order: 'descend' });
  const navigate = useNavigate();

  useEffect(() => {
    fetchRanking(pagination.current ?? 1, pagination.pageSize ?? 20, sortInfo);
  }, []);

  const fetchRanking = useCallback(
    async (page = 1, pageSize = 20, sort: SortInfo = { field: 'change_pct', order: 'descend' }) => {
      setLoading(true);
      try {
        const data = await apiGet<StockRankItem[] | { list?: StockRankItem[]; total?: number }>('/market/ranking', {
          page,
          page_size: pageSize,
          sort_by: sort.field || 'change_pct',
          sort_order: sort.order === 'ascend' ? 'asc' : 'desc',
        });
        const items = Array.isArray(data) ? data : data?.list || [];
        setRanking(items);
        setPagination((prev) => ({
          ...prev,
          current: page,
          pageSize,
          total: (Array.isArray(data) ? undefined : data?.total) || items.length,
        }));
      } catch {
        setRanking([]);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const fetchSectors = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiGet<SectorData[]>('/market/sectors');
      setSectors(Array.isArray(data) ? data : []);
    } catch {
      setSectors([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchLimitBoard = useCallback(async (type: 'limit_up' | 'limit_down') => {
    setLoading(true);
    try {
      const endpoint = type === 'limit_up' ? '/market/limit-up' : '/market/limit-down';
      const items = await apiGet<StockRankItem[]>(endpoint);
      if (type === 'limit_up') setLimitUp(Array.isArray(items) ? items : []);
      else setLimitDown(Array.isArray(items) ? items : []);
    } catch {
      if (type === 'limit_up') setLimitUp([]);
      else setLimitDown([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleTabChange = useCallback(
    (key: string) => {
      setActiveTab(key);
      if (key === 'ranking') {
        fetchRanking(1, pagination.pageSize ?? 20, sortInfo);
      } else if (key === 'heatmap') {
        fetchSectors();
      } else if (key === 'limit_up') {
        fetchLimitBoard('limit_up');
      } else if (key === 'limit_down') {
        fetchLimitBoard('limit_down');
      }
    },
    [pagination.pageSize, sortInfo, fetchRanking, fetchSectors, fetchLimitBoard]
  );

  const columns: TableColumnsType<StockRankItem> = [
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      width: 100,
      fixed: 'left',
      render: (v: string) => (
        <a onClick={() => navigate(`/stock/${v}`)} style={{ color: 'var(--color-primary)' }}>
          {v}
        </a>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 100,
      fixed: 'left',
    },
    {
      title: '最新价',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      render: (v: number) => formatPrice(v),
      sorter: true,
    },
    {
      title: '涨跌幅',
      dataIndex: 'change_pct',
      key: 'change_pct',
      width: 100,
      render: (v: number) => <span className={getPercentColor(v)}>{formatPercent(v)}</span>,
      sorter: true,
      defaultSortOrder: 'descend',
    },
    {
      title: '涨跌额',
      dataIndex: 'change',
      key: 'change',
      width: 100,
      render: (v: number) => {
        const num = Number(v);
        return (
          <span className={getPercentColor(num)}>
            {num > 0 ? '+' : ''}{typeof v === 'number' ? v.toFixed(2) : v}
          </span>
        );
      },
      sorter: true,
    },
    {
      title: '成交量',
      dataIndex: 'volume',
      key: 'volume',
      width: 110,
      render: (v: number) => formatVolume(v),
      sorter: true,
    },
    {
      title: '成交额',
      dataIndex: 'amount',
      key: 'amount',
      width: 110,
      render: (v: number) => formatAmount(v),
      sorter: true,
    },
    {
      title: '换手率',
      dataIndex: 'turnover_rate',
      key: 'turnover_rate',
      width: 100,
      render: (v: number | null) => (v !== null && v !== undefined ? `${Number(v).toFixed(2)}%` : '--'),
      sorter: true,
    },
    {
      title: '振幅',
      dataIndex: 'amplitude',
      key: 'amplitude',
      width: 100,
      render: (v: number | null) => (v !== null && v !== undefined ? `${Number(v).toFixed(2)}%` : '--'),
      sorter: true,
    },
  ];

  const handleTableChange = (
    pag: TablePaginationConfig,
    _filters: Record<string, FilterValue | null>,
    sorter: SorterResult<StockRankItem> | SorterResult<StockRankItem>[]
  ) => {
    const s = Array.isArray(sorter) ? sorter[0] : sorter;
    const newSort: SortInfo = {
      field: (s.field as string) || 'change_pct',
      order: s.order || 'descend',
    };
    setSortInfo(newSort);
    fetchRanking(pag.current ?? 1, pag.pageSize ?? 20, newSort);
  };

  const limitColumns = columns.filter((c) => ['code', 'name', 'price', 'change_pct', 'change', 'volume', 'amount'].includes(c.key as string));

  return (
    <div>
      <Title level={4} style={{ margin: '0 0 16px', color: 'var(--color-text)' }}>
        行情中心
      </Title>
      <Card styles={{ body: { padding: '0 16px 16px' } }}>
        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          items={[
            {
              key: 'ranking',
              label: '涨跌排行',
              children: (
                <Spin spinning={loading}>
                  <Table<StockRankItem>
                    dataSource={ranking}
                    columns={columns}
                    rowKey={(r) => r.code}
                    pagination={{ ...pagination, showSizeChanger: true, showTotal: (t) => `共 ${t} 只` }}
                    onChange={handleTableChange}
                    scroll={{ x: 1000 }}
                    size="small"
                    locale={{ emptyText: <Empty description="暂无排行数据" /> }}
                  />
                </Spin>
              ),
            },
            {
              key: 'heatmap',
              label: '板块热力图',
              children: (
                <Spin spinning={loading}>
                  <HeatMap data={sectors} height={500} theme={isDark ? 'dark' : 'light'} />
                </Spin>
              ),
            },
            {
              key: 'limit_up',
              label: '涨停板',
              children: (
                <Spin spinning={loading}>
                  <Table<StockRankItem>
                    dataSource={limitUp}
                    columns={limitColumns}
                    rowKey={(r) => r.code}
                    pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 只` }}
                    scroll={{ x: 800 }}
                    size="small"
                    locale={{ emptyText: <Empty description="暂无涨停数据" /> }}
                  />
                </Spin>
              ),
            },
            {
              key: 'limit_down',
              label: '跌停板',
              children: (
                <Spin spinning={loading}>
                  <Table<StockRankItem>
                    dataSource={limitDown}
                    columns={limitColumns}
                    rowKey={(r) => r.code}
                    pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 只` }}
                    scroll={{ x: 800 }}
                    size="small"
                    locale={{ emptyText: <Empty description="暂无跌停数据" /> }}
                  />
                </Spin>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
