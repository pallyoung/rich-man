import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, theme as antdTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';
import './styles/theme.css';

function Root() {
  const [isDark, setIsDark] = React.useState(() => {
    return (localStorage.getItem('richman-theme') || 'dark') === 'dark';
  });

  const toggleTheme = React.useCallback(() => {
    setIsDark((prev) => {
      const next = !prev;
      document.documentElement.setAttribute('data-theme', next ? 'dark' : 'light');
      localStorage.setItem('richman-theme', next ? 'dark' : 'light');
      return next;
    });
  }, []);

  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
        token: {
          colorPrimary: isDark ? '#58a6ff' : '#1677ff',
          borderRadius: 6,
        },
      }}
    >
      <BrowserRouter>
        <App isDark={isDark} toggleTheme={toggleTheme} />
      </BrowserRouter>
    </ConfigProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
