/**
 * Format currency with modern, clean display
 * Uses compact notation for large numbers
 */
export function formatCurrency(value, compact = false) {
  const num = parseFloat(value) || 0;
  const absNum = Math.abs(num);

  // For compact mode, use abbreviated format
  if (compact) {
    if (absNum >= 1000000) {
      const formatted = (num / 1000000).toFixed(1);
      return `${formatted.replace('.', ',')}M €`;
    }
    if (absNum >= 1000) {
      const formatted = (num / 1000).toFixed(absNum >= 10000 ? 0 : 1);
      return `${formatted.replace('.', ',')}K €`;
    }
    return `${num.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')} €`;
  }

  // Full format with decimals
  const parts = num.toFixed(2).split('.');
  const intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const decPart = parts[1];

  return `${intPart},${decPart} €`;
}

/**
 * Format large numbers in a clean, readable way
 * Example: 1234567 → "1,23M"
 */
export function formatNumber(value, decimals = 0) {
  const num = parseFloat(value) || 0;
  const absNum = Math.abs(num);

  if (absNum >= 1000000) {
    return `${(num / 1000000).toFixed(2).replace('.', ',')}M`;
  }
  if (absNum >= 1000) {
    return `${(num / 1000).toFixed(1).replace('.', ',')}K`;
  }

  return num.toFixed(decimals).replace('.', ',');
}

/**
 * Format percentage - clean display
 */
export function formatPercent(value, decimals = 1) {
  const num = parseFloat(value) || 0;
  const sign = num >= 0 ? '+' : '';
  return `${sign}${num.toFixed(decimals).replace('.', ',')}%`;
}

/**
 * Format date in Spanish locale
 */
export function formatDate(dateStr, options = {}) {
  if (!dateStr) return '-';
  const date = new Date(dateStr);

  const defaultOptions = {
    day: '2-digit',
    month: 'short',
    ...options
  };

  return date.toLocaleDateString('es-ES', defaultOptions);
}

/**
 * Format date with time
 */
export function formatDateTime(dateStr) {
  if (!dateStr) return '-';
  const date = new Date(dateStr);

  return date.toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format relative time (hace X minutos)
 */
export function formatRelativeTime(dateStr) {
  if (!dateStr) return '-';

  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Ahora';
  if (diffMins < 60) return `Hace ${diffMins} min`;
  if (diffHours < 24) return `Hace ${diffHours}h`;
  if (diffDays < 7) return `Hace ${diffDays}d`;

  return formatDate(dateStr);
}

/**
 * Check if transaction is income
 */
export function isIncome(tx) {
  const side = (tx.side || '').toLowerCase();
  return side === 'credit' || side === 'income';
}

/**
 * Get amount class based on value
 */
export function getAmountClass(value) {
  const num = parseFloat(value) || 0;
  return num >= 0 ? 'text-emerald-600' : 'text-red-500';
}
