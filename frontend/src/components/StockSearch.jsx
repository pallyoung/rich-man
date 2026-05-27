import React, { useState, useRef, useCallback } from 'react';
import { AutoComplete, Input } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';

export default function StockSearch({ style, onSelect: onSelectProp }) {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const timerRef = useRef(null);

  const handleSearch = useCallback((value) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (!value || value.trim().length === 0) {
      setOptions([]);
      return;
    }
    timerRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await api.get('/stock/search', { params: { keyword: value.trim() } });
        const items = Array.isArray(res) ? res : [];
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
    (value) => {
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
        loading={loading}
      />
    </AutoComplete>
  );
}
