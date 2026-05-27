# RichMan - 中国股市量化分析平台

面向个人投资者的A股量化分析工具，集行情分析、技术指标、趋势识别、策略回测和财经资讯于一体。

## 功能模块

- **市场总览** — 四大指数实时行情、涨跌家数、热门板块、市场情绪
- **行情中心** — 涨跌排行、板块热力图、涨停/跌停板
- **个股分析** — 专业K线图、技术指标(MA/MACD/KDJ/RSI/BOLL)、基本面数据
- **趋势分析** — 买卖信号、多股对比、行业轮动
- **量化策略** — 策略回测(双均线/MACD/动量)、因子选股
- **资讯中心** — 财经新闻、个股公告、市场情绪指数

## 快速开始

```bash
# 一键启动
chmod +x start.sh && ./start.sh

# 或分别启动
# 后端
cd backend && pip install -r requirements.txt && python app.py

# 前端
cd frontend && npm install && npx vite --port 3000
```

访问 http://localhost:3000

## 技术栈

| 组件 | 技术 |
|------|------|
| 前端 | React 18 + Vite + Ant Design 5 + ECharts 5 |
| 后端 | Flask + AKShare + pandas |
| 存储 | SQLite (本地缓存) |
| 主题 | 深色/浅色可切换 |

## 目录结构

```
richman/
├── backend/
│   ├── app.py              # Flask 入口
│   ├── api/                # API 蓝图
│   │   ├── market.py       # 行情接口
│   │   ├── stock.py        # 个股接口
│   │   ├── trend.py        # 趋势接口
│   │   ├── quant.py        # 量化接口
│   │   └── news.py         # 资讯接口
│   ├── services/           # 业务服务
│   │   ├── indicators.py   # 技术指标计算
│   │   ├── backtest.py     # 回测引擎
│   │   └── cache.py        # 缓存服务
│   └── utils/              # 工具函数
├── frontend/
│   └── src/
│       ├── components/     # 通用组件
│       ├── pages/          # 页面组件
│       ├── hooks/          # 自定义 Hook
│       ├── utils/          # 工具函数
│       └── styles/         # 样式文件
├── start.sh                # 一键启动脚本
└── docs/                   # 设计文档
```
