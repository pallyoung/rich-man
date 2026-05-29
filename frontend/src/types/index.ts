/** API response wrapper from backend */
export interface ApiResponse<T = unknown> {
  code: number;
  data: T;
  message: string;
}

/** Market index item */
export interface MarketIndex {
  code: string;
  name: string;
  price?: number;
  current_price?: number;
  change?: number;
  change_pct?: number;
  pct_change?: number;
  volume?: number;
  amount?: number;
  data_date?: string;
}

/** Sector data */
export interface SectorData {
  name: string;
  value?: number;
  market_cap?: number;
  change?: number;
  change_pct?: number;
  leading_stock?: string;
}

/** Signal data */
export interface SignalData {
  stock_code: string;
  stock_name: string;
  signal_type: string;
  signal_date: string;
  strength?: number | null;
  description?: string;
}

/** Stock ranking item */
export interface StockRankItem {
  code: string;
  name: string;
  price: number;
  change_pct: number;
  change: number;
  volume: number;
  amount: number;
  turnover_rate?: number;
  amplitude?: number;
}

/** Stock realtime info */
export interface StockRealtime {
  code: string;
  name: string;
  price?: number;
  current_price?: number;
  change?: number;
  change_pct?: number;
  pct_change?: number;
  industry?: string;
  sector?: string;
  [key: string]: unknown;
}

/** K-line data as array: [date, open, high, low, close, volume] */
export type KLineItem = [string, number, number, number, number, number];

/** K-line data as object */
export interface KLineObject {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/** Indicator config for K-line chart */
export interface IndicatorConfig {
  ma_periods?: number[];
  macd?: boolean;
  kdj?: boolean;
  rsi?: boolean;
  boll?: boolean;
  volume?: boolean;
}

/** Intraday data point */
export interface IntradayPoint {
  time: string;
  price: number;
  volume: number;
}

/** Fundamental data row */
export interface FundamentalRow {
  field?: string;
  value?: string;
  [key: string]: unknown;
}

/** Backtest params */
export interface BacktestParams {
  strategy: string;
  stock_code: string;
  start_date?: string;
  end_date?: string;
  initial_capital?: number;
  commission?: number;
  short_period?: number;
  long_period?: number;
}

/** Backtest metrics */
export interface BacktestMetrics {
  total_return?: number;
  annual_return?: number;
  max_drawdown?: number;
  sharpe_ratio?: number;
  win_rate?: number;
  [key: string]: unknown;
}

/** Trade record */
export interface TradeRecord {
  date: string;
  action: string;
  price: number | null;
  shares: number | null;
  pnl?: number | null;
}

/** Equity curve data point */
export interface EquityPoint {
  date: string;
  equity: number;
  benchmark?: number | null;
}

/** Backtest result */
export interface BacktestResult {
  metrics: BacktestMetrics;
  equity_curve: EquityPoint[];
  trades: TradeRecord[];
  [key: string]: unknown;
}

/** Factor select result item */
export interface FactorResult {
  code: string;
  name?: string;
  score?: number;
  [key: string]: unknown;
}

/** Compare stock data */
export interface CompareStock {
  code?: string;
  name?: string;
  prices?: number[];
  dates?: string[];
  data?: { price: number; date: string }[];
}

/** Rotation data */
export interface RotationItem {
  name: string;
  score?: number;
  value?: number;
}

/** News item */
export interface NewsItem {
  title: string;
  url?: string;
  source?: string;
  time?: string;
  publish_time?: string;
  summary?: string;
  content?: string;
}

/** Announcement item */
export interface AnnouncementItem {
  title: string;
  url?: string;
  date?: string;
  publish_time?: string;
  type?: string;
}

/** Sentiment data */
export interface SentimentData {
  score: number;
  keywords: (string | { text?: string; name?: string; weight?: number; count?: number })[];
}

/** Search result item */
export interface SearchResult {
  code: string;
  name: string;
}

/** Overview data with updown stats */
export interface FearGreedFactor {
  score: number;
  weight: number;
  label: string;
}

export interface OverviewData {
  indices: MarketIndex[];
  up_count?: number;
  down_count?: number;
  flat_count?: number;
  up?: number;
  down?: number;
  flat?: number;
  sentiment?: number;
  sentiment_label?: string;
  factors?: Record<string, FearGreedFactor>;
  source?: string;
  [key: string]: unknown;
}
