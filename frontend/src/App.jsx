import React, { useState, useMemo, Suspense, lazy } from 'react';
import { Layout, Menu, Switch, Space, Typography, Spin } from 'antd';
import {
  DashboardOutlined,
  BarChartOutlined,
  StockOutlined,
  LineChartOutlined,
  RobotOutlined,
  ReadOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';

// Lazy load pages for code-splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const MarketCenter = lazy(() => import('./pages/MarketCenter'));
const StockAnalysis = lazy(() => import('./pages/StockAnalysis'));
const TrendAnalysis = lazy(() => import('./pages/TrendAnalysis'));
const QuantStrategy = lazy(() => import('./pages/QuantStrategy'));
const NewsCenter = lazy(() => import('./pages/NewsCenter'));

const { Sider, Header, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '市场总览' },
  { key: '/market', icon: <BarChartOutlined />, label: '行情中心' },
  { key: '/stock', icon: <StockOutlined />, label: '个股分析' },
  { key: '/trend', icon: <LineChartOutlined />, label: '趋势分析' },
  { key: '/quant', icon: <RobotOutlined />, label: '量化策略' },
  { key: '/news', icon: <ReadOutlined />, label: '资讯中心' },
];

export default function App({ isDark, toggleTheme }) {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey = useMemo(() => {
    const path = location.pathname;
    if (path === '/') return '/';
    const match = menuItems.find((m) => m.key !== '/' && path.startsWith(m.key));
    return match ? match.key : '/';
  }, [location.pathname]);

  const handleMenuClick = ({ key }) => {
    if (key === '/stock') {
      navigate('/stock');
    } else {
      navigate(key);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={220}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 10,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid var(--color-border)',
          }}
        >
          <Text
            strong
            style={{
              fontSize: collapsed ? 18 : 22,
              color: 'var(--color-primary)',
              letterSpacing: 2,
              transition: 'font-size 0.2s',
            }}
          >
            {collapsed ? 'RM' : 'RichMan'}
          </Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ borderRight: 0, marginTop: 8 }}
        />
      </Sider>

      <Layout style={{ marginLeft: collapsed ? 80 : 220, transition: 'margin-left 0.2s' }}>
        <Header
          style={{
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid var(--color-border)',
            position: 'sticky',
            top: 0,
            zIndex: 9,
          }}
        >
          <div />
          <Space size="middle">
            <BulbOutlined style={{ color: 'var(--color-text-secondary)' }} />
            <Switch
              checked={isDark}
              onChange={toggleTheme}
              checkedChildren="深色"
              unCheckedChildren="浅色"
            />
          </Space>
        </Header>

        <Content
          style={{
            margin: 20,
            minHeight: 280,
          }}
        >
          <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}><Spin size="large" /></div>}>
            <Routes>
              <Route path="/" element={<Dashboard isDark={isDark} />} />
              <Route path="/market" element={<MarketCenter isDark={isDark} />} />
              <Route path="/stock" element={<StockAnalysis isDark={isDark} />} />
              <Route path="/stock/:code" element={<StockAnalysis isDark={isDark} />} />
              <Route path="/trend" element={<TrendAnalysis isDark={isDark} />} />
              <Route path="/quant" element={<QuantStrategy isDark={isDark} />} />
              <Route path="/news" element={<NewsCenter isDark={isDark} />} />
            </Routes>
          </Suspense>
        </Content>
      </Layout>
    </Layout>
  );
}
