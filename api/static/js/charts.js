/* ============================================
   G4U Finance Dashboard - Charts & Sparklines
   ============================================ */

const Charts = {
    // Generate SVG Sparkline
    sparkline(data, options = {}) {
        const {
            width = 100,
            height = 40,
            stroke = 'var(--primary)',
            fill = 'var(--primary)',
            showArea = true,
            className = ''
        } = options;

        if (!data || data.length < 2) {
            return `<svg class="sparkline-svg ${className}" width="${width}" height="${height}"></svg>`;
        }

        const values = data.map(d => typeof d === 'object' ? d.value : d);
        const min = Math.min(...values);
        const max = Math.max(...values);
        const range = max - min || 1;

        const padding = 2;
        const chartWidth = width - padding * 2;
        const chartHeight = height - padding * 2;

        const points = values.map((val, i) => {
            const x = padding + (i / (values.length - 1)) * chartWidth;
            const y = padding + chartHeight - ((val - min) / range) * chartHeight;
            return `${x},${y}`;
        });

        const linePath = `M ${points.join(' L ')}`;

        // Area path (for gradient fill)
        const areaPath = `M ${padding},${height - padding} L ${points.join(' L ')} L ${width - padding},${height - padding} Z`;

        // Determine color based on trend
        const trend = values[values.length - 1] >= values[0] ? 'positive' : 'negative';
        const strokeColor = trend === 'positive' ? 'var(--success)' : 'var(--danger)';
        const fillColor = trend === 'positive' ? 'var(--success)' : 'var(--danger)';

        return `
            <svg class="sparkline-svg ${className}" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
                ${showArea ? `<path class="sparkline-area ${trend}" d="${areaPath}"/>` : ''}
                <path class="sparkline-line ${trend}" d="${linePath}"/>
            </svg>
        `;
    },

    // Bar sparkline (for monthly data)
    barSparkline(data, options = {}) {
        const {
            width = 100,
            height = 40,
            gap = 2,
            className = ''
        } = options;

        if (!data || data.length === 0) {
            return `<div class="sparkline ${className}" style="width:${width}px;height:${height}px;"></div>`;
        }

        const values = data.map(d => typeof d === 'object' ? d.value : d);
        const max = Math.max(...values.map(Math.abs));

        const barWidth = (width - (values.length - 1) * gap) / values.length;

        const bars = values.map((val, i) => {
            const barHeight = (Math.abs(val) / max) * height;
            const isNegative = val < 0;
            return `<div class="sparkline-bar ${isNegative ? 'negative' : ''}"
                        style="width:${barWidth}px;height:${barHeight}px;"></div>`;
        }).join('');

        return `<div class="sparkline ${className}" style="width:${width}px;height:${height}px;">${bars}</div>`;
    },

    // Simple line chart using Canvas
    lineChart(canvas, data, options = {}) {
        if (!canvas || !data) return;

        const ctx = canvas.getContext('2d');
        const {
            labels = [],
            datasets = [],
            showGrid = true,
            showLegend = true,
            animated = true
        } = options;

        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();

        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height;
        const padding = { top: 20, right: 20, bottom: 40, left: 60 };

        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Find min/max
        let allValues = [];
        datasets.forEach(ds => {
            allValues = allValues.concat(ds.data);
        });
        const minVal = Math.min(0, ...allValues);
        const maxVal = Math.max(...allValues);
        const range = maxVal - minVal || 1;

        // Draw grid
        if (showGrid) {
            ctx.strokeStyle = '#e2e8f0';
            ctx.lineWidth = 1;

            // Horizontal lines
            const numLines = 5;
            for (let i = 0; i <= numLines; i++) {
                const y = padding.top + (i / numLines) * chartHeight;
                ctx.beginPath();
                ctx.moveTo(padding.left, y);
                ctx.lineTo(width - padding.right, y);
                ctx.stroke();

                // Y-axis labels
                const value = maxVal - (i / numLines) * range;
                ctx.fillStyle = '#64748b';
                ctx.font = '11px -apple-system, sans-serif';
                ctx.textAlign = 'right';
                ctx.fillText(Utils.formatCompact(value), padding.left - 8, y + 4);
            }

            // X-axis labels
            const labelStep = Math.ceil(labels.length / 12);
            labels.forEach((label, i) => {
                if (i % labelStep === 0) {
                    const x = padding.left + (i / (labels.length - 1)) * chartWidth;
                    ctx.fillStyle = '#64748b';
                    ctx.font = '11px -apple-system, sans-serif';
                    ctx.textAlign = 'center';
                    ctx.fillText(label, x, height - padding.bottom + 20);
                }
            });
        }

        // Draw datasets
        datasets.forEach((ds, dsIndex) => {
            const { data: values, color = '#3b82f6', fillColor, lineWidth = 2 } = ds;

            if (!values || values.length === 0) return;

            const points = values.map((val, i) => ({
                x: padding.left + (i / (values.length - 1)) * chartWidth,
                y: padding.top + chartHeight - ((val - minVal) / range) * chartHeight
            }));

            // Draw fill
            if (fillColor) {
                ctx.beginPath();
                ctx.moveTo(points[0].x, padding.top + chartHeight);
                points.forEach(p => ctx.lineTo(p.x, p.y));
                ctx.lineTo(points[points.length - 1].x, padding.top + chartHeight);
                ctx.closePath();
                ctx.fillStyle = fillColor;
                ctx.fill();
            }

            // Draw line
            ctx.beginPath();
            ctx.strokeStyle = color;
            ctx.lineWidth = lineWidth;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            points.forEach((p, i) => {
                if (i === 0) ctx.moveTo(p.x, p.y);
                else ctx.lineTo(p.x, p.y);
            });
            ctx.stroke();

            // Draw points
            points.forEach((p, i) => {
                if (i === points.length - 1 || values.length <= 12) {
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
                    ctx.fillStyle = '#fff';
                    ctx.fill();
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 2;
                    ctx.stroke();
                }
            });
        });
    },

    // Bar chart
    barChart(canvas, data, options = {}) {
        if (!canvas || !data) return;

        const ctx = canvas.getContext('2d');
        const {
            labels = [],
            values = [],
            colors = [],
            showValues = true
        } = options;

        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();

        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height;
        const padding = { top: 20, right: 20, bottom: 60, left: 60 };

        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;

        ctx.clearRect(0, 0, width, height);

        const max = Math.max(...values.map(Math.abs));
        const barWidth = chartWidth / values.length * 0.7;
        const barGap = chartWidth / values.length * 0.3;

        values.forEach((val, i) => {
            const barHeight = (Math.abs(val) / max) * chartHeight;
            const x = padding.left + i * (barWidth + barGap) + barGap / 2;
            const y = val >= 0
                ? padding.top + chartHeight - barHeight
                : padding.top + chartHeight;

            // Draw bar
            ctx.fillStyle = colors[i] || (val >= 0 ? '#059669' : '#dc2626');
            ctx.beginPath();
            ctx.roundRect(x, y, barWidth, barHeight, 4);
            ctx.fill();

            // Draw label
            ctx.fillStyle = '#64748b';
            ctx.font = '11px -apple-system, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(labels[i] || '', x + barWidth / 2, height - padding.bottom + 20);

            // Draw value
            if (showValues) {
                ctx.fillStyle = '#1e293b';
                ctx.font = '12px -apple-system, sans-serif';
                ctx.fillText(
                    Utils.formatCompact(val),
                    x + barWidth / 2,
                    y - 8
                );
            }
        });
    },

    // Donut chart for proportions
    donutChart(canvas, data, options = {}) {
        if (!canvas || !data) return;

        const ctx = canvas.getContext('2d');
        const {
            colors = ['#3b82f6', '#059669', '#f59e0b', '#ef4444', '#8b5cf6'],
            centerLabel = '',
            centerValue = ''
        } = options;

        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();

        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height;

        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) / 2 - 10;
        const innerRadius = radius * 0.65;

        ctx.clearRect(0, 0, width, height);

        const total = data.reduce((sum, d) => sum + d.value, 0);
        let currentAngle = -Math.PI / 2;

        data.forEach((d, i) => {
            const sliceAngle = (d.value / total) * Math.PI * 2;

            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
            ctx.closePath();
            ctx.fillStyle = colors[i % colors.length];
            ctx.fill();

            currentAngle += sliceAngle;
        });

        // Draw inner circle (donut hole)
        ctx.beginPath();
        ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2);
        ctx.fillStyle = '#fff';
        ctx.fill();

        // Draw center text
        if (centerLabel || centerValue) {
            ctx.textAlign = 'center';
            if (centerValue) {
                ctx.font = 'bold 24px -apple-system, sans-serif';
                ctx.fillStyle = '#1e293b';
                ctx.fillText(centerValue, centerX, centerY + 8);
            }
            if (centerLabel) {
                ctx.font = '12px -apple-system, sans-serif';
                ctx.fillStyle = '#64748b';
                ctx.fillText(centerLabel, centerX, centerY + 28);
            }
        }
    },

    // Generate monthly trend data from transactions
    getMonthlyTrend(transactions, months = 6) {
        const now = new Date();
        const result = [];

        for (let i = months - 1; i >= 0; i--) {
            const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
            const monthEnd = new Date(now.getFullYear(), now.getMonth() - i + 1, 0);

            const monthTxs = transactions.filter(tx => {
                const txDate = new Date(tx.settled_at || tx.emitted_at);
                return txDate >= date && txDate <= monthEnd;
            });

            const income = monthTxs
                .filter(tx => tx.side === 'credit' || parseFloat(tx.amount) > 0)
                .reduce((sum, tx) => sum + Math.abs(parseFloat(tx.amount) || 0), 0);

            const expenses = monthTxs
                .filter(tx => tx.side === 'debit' || parseFloat(tx.amount) < 0)
                .reduce((sum, tx) => sum + Math.abs(parseFloat(tx.amount) || 0), 0);

            result.push({
                month: date.toLocaleString('es-ES', { month: 'short' }),
                year: date.getFullYear(),
                income,
                expenses,
                net: income - expenses
            });
        }

        return result;
    }
};

// Export
window.Charts = Charts;
