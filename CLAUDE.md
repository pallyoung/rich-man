# RichMan Project

## Overview
Chinese stock market quantitative analysis platform for individual investors.

## Tech Stack
- Frontend: React 18 + Vite + Ant Design 5 + ECharts 5
- Backend: Flask + AKShare + pandas
- Storage: SQLite (local cache)

## Commands
- Start all: `./start.sh`
- Backend only: `cd backend && python3 app.py`
- Frontend only: `cd frontend && npx vite --port 3000`
- Install backend deps: `cd backend && pip install -r requirements.txt`
- Install frontend deps: `cd frontend && npm install`

## Conventions
- Chinese convention: RED = price UP, GREEN = price DOWN
- All UI text in Chinese
- API format: {"code": 0, "data": ..., "message": "success"}
- Dark theme default, switchable via header toggle
- Numbers use Chinese units (万, 亿)
