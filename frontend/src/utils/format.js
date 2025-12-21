/**
 * Format currency with proper EUR formatting
 * Uses Spanish locale for proper thousands separator (.) and decimal (,)
 */
export function formatCurrency(value, compact = false) {
  const num = parseFloat(value) || 0;

  if (compact && Math.abs(num) >= 1000000) {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
      notation: 'compact',
      compactDisplay: 'short',
      maximumFractionDigits: 1,
    }).format(num);
  }

  if (compact && Math.abs(num) >= 1000) {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0,
    }).format(num);
  }

  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

/**
 * Format percentage with proper decimals
 */
export function formatPercent(value, decimals = 1) {
  const num = parseFloat(value) || 0;
  return new Intl.NumberFormat('es-ES', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num / 100);
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
  const amount = parseFloat(tx.amount) || 0;
  return tx.side === 'credit' || amount > 0;
}

/**
 * Get amount class based on value
 */
export function getAmountClass(value) {
  const num = parseFloat(value) || 0;
  return num >= 0 ? 'text-emerald-600' : 'text-red-500';
}
