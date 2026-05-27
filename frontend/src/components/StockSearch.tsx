import React, { useState, useRef, useCallback } from 'react';
import { AutoComplete, Input } from 'antd';
import type { DefaultOptionType } from 'antd/es/select';
import { SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { apiGet, apiPost } from '../utils/api';
import type { SearchResult } from '../types';

interface StockSearchProps {
  style?: React.CSSProperties;
  onSelect?: (value: string) => void;
}

interface SearchOption extends DefaultOptionType {
  name?: string;
}

export default function StockSearch({ style, onSelect: onSelectProp }: StockSearchProps) {
  const [options, setOptions] = useState<SearchOption[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const navigate = useNavigate();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearch = useCallback((value: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (!value || value.trim().length === 0) {
      setOptions([]);
      return;
    }
    timerRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await apiGet('/stock/search', { keyword: value.trim() });
        const items: SearchResult[] = Array.isArray(res) ? res : [];
        setOptions(
          items.map((item) => ({
            value: item.code,
            label: (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{item.code}</span>
                <span style={{ color: '#8b949e' }}>{item.name}</span>
              </div>
            ),
            name: item.name,
          }))
        );
      } catch {
        setOptions([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  }, []);

  const handleSelect = useCallback(
    (value: string) => {
      if (onSelectProp) {
        onSelectProp(value);
      } else {
        navigate(`/stock/${value}`);
      }
      setOptions([]);
    },
    [navigate, onSelectProp]
  );

  return (
    <AutoComplete
      options={options}
      onSearch={handleSearch}
      onSelect={handleSelect}
      style={style || { width: 280 }}
    >
      <Input
        placeholder="输入股票代码或名称搜索"
        prefix={<SearchOutlined />}
        allowClear
        
      />
    </AutoComplete>
  );
}
