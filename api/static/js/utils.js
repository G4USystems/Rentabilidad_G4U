/* ============================================
   G4U Finance Dashboard - Utilities
   ============================================ */

// Currency formatter
const formatCurrency = (value, options = {}) => {
    const { currency = 'EUR', compact = false } = options;

    if (compact && Math.abs(value) >= 1000) {
        const formatter = new Intl.NumberFormat('es-ES', {
            notation: 'compact',
            compactDisplay: 'short',
            maximumFractionDigits: 1
        });
        return formatter.format(value) + ' €';
    }

    return new Intl.NumberFormat('es-ES', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    }).format(value || 0);
};

// Short format for large numbers
const formatCompact = (value) => {
    if (Math.abs(value) >= 1000000) {
        return (value / 1000000).toFixed(1) + 'M';
    }
    if (Math.abs(value) >= 1000) {
        return (value / 1000).toFixed(1) + 'K';
    }
    return value.toFixed(0);
};

// Percentage formatter
const formatPercent = (value, decimals = 1) => {
    return (value || 0).toFixed(decimals) + '%';
};

// Date formatter
const formatDate = (dateStr, format = 'short') => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);

    if (format === 'short') {
        return date.toLocaleDateString('es-ES', {
            day: '2-digit',
            month: '2-digit',
            year: '2-digit'
        });
    }

    if (format === 'long') {
        return date.toLocaleDateString('es-ES', {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
    }

    if (format === 'relative') {
        const now = new Date();
        const diff = now - date;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));

        if (days === 0) return 'Hoy';
        if (days === 1) return 'Ayer';
        if (days < 7) return `Hace ${days} días`;
        if (days < 30) return `Hace ${Math.floor(days / 7)} sem`;
        return formatDate(dateStr, 'short');
    }

    return dateStr.split('T')[0];
};

// Date range helpers
const getDateRange = (period) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

    switch (period) {
        case 'today':
            return {
                start: today,
                end: new Date(today.getTime() + 24 * 60 * 60 * 1000 - 1)
            };
        case 'week':
            const weekStart = new Date(today);
            weekStart.setDate(today.getDate() - today.getDay() + 1);
            return { start: weekStart, end: now };
        case 'month':
            return {
                start: new Date(now.getFullYear(), now.getMonth(), 1),
                end: now
            };
        case 'quarter':
            const quarterMonth = Math.floor(now.getMonth() / 3) * 3;
            return {
                start: new Date(now.getFullYear(), quarterMonth, 1),
                end: now
            };
        case 'year':
            return {
                start: new Date(now.getFullYear(), 0, 1),
                end: now
            };
        case 'last-month':
            const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);
            return { start: lastMonth, end: lastMonthEnd };
        case 'last-quarter':
            const lastQuarterMonth = Math.floor(now.getMonth() / 3) * 3 - 3;
            const lastQuarterStart = new Date(now.getFullYear(), lastQuarterMonth, 1);
            const lastQuarterEnd = new Date(now.getFullYear(), lastQuarterMonth + 3, 0);
            return { start: lastQuarterStart, end: lastQuarterEnd };
        default:
            return { start: null, end: null };
    }
};

const formatDateISO = (date) => {
    if (!date) return '';
    return date.toISOString().split('T')[0];
};

// Debounce function
const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

// Throttle function
const throttle = (func, limit) => {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
};

// Deep clone
const deepClone = (obj) => JSON.parse(JSON.stringify(obj));

// Group by helper
const groupBy = (array, key) => {
    return array.reduce((result, item) => {
        const groupKey = typeof key === 'function' ? key(item) : item[key];
        (result[groupKey] = result[groupKey] || []).push(item);
        return result;
    }, {});
};

// Sum helper
const sumBy = (array, key) => {
    return array.reduce((sum, item) => {
        const value = typeof key === 'function' ? key(item) : item[key];
        return sum + (parseFloat(value) || 0);
    }, 0);
};

// Sort helper
const sortBy = (array, key, direction = 'asc') => {
    return [...array].sort((a, b) => {
        const aVal = typeof key === 'function' ? key(a) : a[key];
        const bVal = typeof key === 'function' ? key(b) : b[key];

        if (aVal < bVal) return direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return direction === 'asc' ? 1 : -1;
        return 0;
    });
};

// Calculate percentage change
const calcChange = (current, previous) => {
    if (!previous || previous === 0) return 0;
    return ((current - previous) / Math.abs(previous)) * 100;
};

// Generate unique ID
const generateId = () => {
    return 'id_' + Math.random().toString(36).substr(2, 9);
};

// Local storage helpers
const storage = {
    get: (key, defaultValue = null) => {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch {
            return defaultValue;
        }
    },
    set: (key, value) => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.warn('localStorage error:', e);
        }
    },
    remove: (key) => {
        localStorage.removeItem(key);
    }
};

// Color helpers
const getStatusColor = (value, thresholds = { good: 20, warning: 10 }) => {
    if (value >= thresholds.good) return 'success';
    if (value >= thresholds.warning) return 'warning';
    return 'danger';
};

const getAmountClass = (value) => {
    if (value > 0) return 'positive';
    if (value < 0) return 'negative';
    return '';
};

// SVG Icons (commonly used)
const icons = {
    arrowUp: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z"/></svg>',
    arrowDown: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z"/></svg>',
    check: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/></svg>',
    x: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"/></svg>',
    search: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"/></svg>',
    filter: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3 3a1 1 0 011-1h12a1 1 0 011 1v3a1 1 0 01-.293.707L12 11.414V15a1 1 0 01-.293.707l-2 2A1 1 0 018 17v-5.586L3.293 6.707A1 1 0 013 6V3z"/></svg>',
    download: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"/></svg>',
    refresh: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"/></svg>',
    bell: '<svg viewBox="0 0 20 20" fill="currentColor"><path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z"/></svg>',
    sparkles: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z"/></svg>'
};

// Export for use in other modules
window.Utils = {
    formatCurrency,
    formatCompact,
    formatPercent,
    formatDate,
    formatDateISO,
    getDateRange,
    debounce,
    throttle,
    deepClone,
    groupBy,
    sumBy,
    sortBy,
    calcChange,
    generateId,
    storage,
    getStatusColor,
    getAmountClass,
    icons
};
