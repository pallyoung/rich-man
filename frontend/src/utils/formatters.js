import dayjs from 'dayjs';

export function formatPrice(num) {
  if (num === null || num === undefined || isNaN(num)) return '--';
  return Number(num).toFixed(2);
}

export function formatPercent(num) {
  if (num === null || num === undefined || isNaN(num)) return '--';
  const val = Number(num);
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(2)}%`;
}

export function getPercentColor(num) {
  if (num === null || num === undefined || isNaN(num)) return '';
  const val = Number(num);
  if (val > 0) return 'stock-up';
  if (val < 0) return 'stock-down';
  return 'stock-flat';
}

export function formatVolume(num) {
  if (num === null || num === undefined || isNaN(num)) return '--';
  const val = Number(num);
  if (Math.abs(val) >= 1e8) {
    return `${(val / 1e8).toFixed(2)}亿手`;
  }
  if (Math.abs(val) >= 1e4) {
    return `${(val / 1e4).toFixed(2)}万手`;
  }
  return `${val.toFixed(0)}手`;
}

export function formatAmount(num) {
  if (num === null || num === undefined || isNaN(num)) return '--';
  const val = Number(num);
  if (Math.abs(val) >= 1e8) {
    return `${(val / 1e8).toFixed(2)}亿`;
  }
  if (Math.abs(val) >= 1e4) {
    return `${(val / 1e4).toFixed(2)}万`;
  }
  return val.toFixed(2);
}

export function formatDate(dateStr) {
  if (!dateStr) return '--';
  return dayjs(dateStr).format('YYYY-MM-DD');
}

export function formatDateTime(dateStr) {
  if (!dateStr) return '--';
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss');
}
