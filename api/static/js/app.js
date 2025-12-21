/* ============================================
   G4U Finance Dashboard - Main Application
   ============================================ */

const App = {
    // Application State
    state: {
        // Data
        transactions: [],
        projects: [],
        clients: [],
        categories: [],
        teamMembers: [],
        transactionAllocations: [],
        alerts: [],

        // UI State
        currentView: 'dashboard',
        currentPeriod: 'month',
        customDateRange: { start: null, end: null },
        selectedTransactions: [],
        sortField: 'settled_at',
        sortDirection: 'desc',

        // Filters
        filters: {
            type: '',
            category: '',
            project: '',
            client: '',
            assigned: '',
            search: '',
            dateFrom: '',
            dateTo: ''
        },

        // Loading states
        loading: {
            data: true,
            sync: false
        },

        // Real-time update interval
        updateInterval: null,
        lastUpdate: null
    },

    // Initialize application
    async init() {
        console.log('G4U Finance Dashboard v7.0 - Executive Edition');

        // Setup event listeners
        this.setupNavigation();
        this.setupKeyboardShortcuts();
        this.setupSearch();
        this.setupModals();

        // Load initial data
        await this.loadAllData();

        // Start real-time updates (every 30 seconds)
        this.startRealTimeUpdates();

        // Check system status
        this.checkStatus();
    },

    // ========== Data Loading ==========
    async loadAllData() {
        this.state.loading.data = true;
        this.showLoading();

        try {
            // Load all data in parallel
            const [
                dataResult,
                clientsResult,
                teamResult,
                allocationsResult
            ] = await Promise.all([
                API.dashboard.getData(),
                API.clients.getAll(),
                API.team.getAll(),
                API.transactionAllocations.getAll()
            ]);

            // Update state
            this.state.transactions = dataResult.transactions || [];
            this.state.projects = dataResult.projects || [];
            this.state.categories = dataResult.categories || [];
            this.state.clients = clientsResult.clients || [];
            this.state.teamMembers = teamResult.team_members || [];
            this.state.transactionAllocations = allocationsResult.allocations || [];

            // Calculate pending review count
            this.updatePendingCount();

            // Render current view
            this.renderCurrentView();

            this.state.lastUpdate = new Date();

        } catch (error) {
            console.error('Error loading data:', error);
            this.showNotification('Error al cargar datos', 'error');
        } finally {
            this.state.loading.data = false;
            this.hideLoading();
        }
    },

    // ========== Real-time Updates ==========
    startRealTimeUpdates() {
        // Update every 30 seconds
        this.state.updateInterval = setInterval(() => {
            this.refreshData();
        }, 30000);
    },

    stopRealTimeUpdates() {
        if (this.state.updateInterval) {
            clearInterval(this.state.updateInterval);
            this.state.updateInterval = null;
        }
    },

    async refreshData() {
        try {
            const data = await API.dashboard.getData();
            this.state.transactions = data.transactions || [];
            this.state.projects = data.projects || [];

            // Only re-render if on dashboard or relevant view
            if (['dashboard', 'transactions', 'review'].includes(this.state.currentView)) {
                this.renderCurrentView();
            }

            this.updatePendingCount();
            this.state.lastUpdate = new Date();
            this.updateSyncStatus();
        } catch (error) {
            console.error('Error refreshing data:', error);
        }
    },

    // ========== Navigation ==========
    setupNavigation() {
        document.querySelectorAll('.nav-item[data-view]').forEach(item => {
            item.addEventListener('click', () => {
                const view = item.dataset.view;
                this.navigateTo(view);
            });
        });
    },

    navigateTo(view, params = {}) {
        // Update active nav
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        const navItem = document.querySelector(`.nav-item[data-view="${view}"]`);
        if (navItem) navItem.classList.add('active');

        // Hide all views
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));

        // Show target view
        const viewEl = document.getElementById(`view-${view}`);
        if (viewEl) {
            viewEl.classList.add('active');
            this.state.currentView = view;
            this.renderCurrentView(params);
        }

        // Update URL without reload
        history.pushState({ view, params }, '', `#${view}`);
    },

    renderCurrentView(params = {}) {
        switch (this.state.currentView) {
            case 'dashboard':
                this.renderDashboard();
                break;
            case 'clients':
                this.renderClients(params);
                break;
            case 'projects':
                this.renderProjects(params);
                break;
            case 'transactions':
                this.renderTransactions();
                break;
            case 'review':
                this.renderReview();
                break;
            case 'settings':
                this.renderSettings();
                break;
        }
    },

    // ========== Dashboard ==========
    renderDashboard() {
        const filtered = this.getFilteredTransactions();
        const previousPeriod = this.getPreviousPeriodTransactions();

        // Calculate KPIs
        const kpis = this.calculateKPIs(filtered, previousPeriod);

        // Render KPI cards
        this.renderKPICards(kpis);

        // Render charts
        this.renderDashboardCharts(filtered);

        // Render top clients
        this.renderTopClients(filtered);

        // Render top projects
        this.renderTopProjects(filtered);

        // Render recent transactions
        this.renderRecentTransactions(filtered.slice(0, 10));

        // Render alerts if any
        this.renderAlerts();
    },

    calculateKPIs(transactions, previousTransactions = []) {
        const income = transactions
            .filter(tx => tx.side === 'credit' || parseFloat(tx.amount) > 0)
            .reduce((sum, tx) => sum + Math.abs(parseFloat(tx.amount) || 0), 0);

        const expenses = transactions
            .filter(tx => tx.side === 'debit' || parseFloat(tx.amount) < 0)
            .reduce((sum, tx) => sum + Math.abs(parseFloat(tx.amount) || 0), 0);

        const net = income - expenses;
        const margin = income > 0 ? (net / income) * 100 : 0;

        // Previous period for comparison
        const prevIncome = previousTransactions
            .filter(tx => tx.side === 'credit' || parseFloat(tx.amount) > 0)
            .reduce((sum, tx) => sum + Math.abs(parseFloat(tx.amount) || 0), 0);

        const prevExpenses = previousTransactions
            .filter(tx => tx.side === 'debit' || parseFloat(tx.amount) < 0)
            .reduce((sum, tx) => sum + Math.abs(parseFloat(tx.amount) || 0), 0);

        const prevNet = prevIncome - prevExpenses;
        const prevMargin = prevIncome > 0 ? (prevNet / prevIncome) * 100 : 0;

        // Estimate EBITDA (simplified - would need more data for real EBITDA)
        const ebitda = net; // Simplified

        return {
            income: { value: income, change: Utils.calcChange(income, prevIncome) },
            expenses: { value: expenses, change: Utils.calcChange(expenses, prevExpenses) },
            net: { value: net, change: Utils.calcChange(net, prevNet) },
            margin: { value: margin, change: margin - prevMargin },
            ebitda: { value: ebitda, change: Utils.calcChange(ebitda, prevNet) }
        };
    },

    renderKPICards(kpis) {
        const monthlyData = Charts.getMonthlyTrend(this.state.transactions, 6);

        // Margin
        const marginEl = document.getElementById('kpi-margin');
        if (marginEl) {
            const marginCard = marginEl.closest('.kpi-card');
            marginEl.textContent = Utils.formatPercent(kpis.margin.value);
            marginEl.className = `kpi-value ${kpis.margin.value >= 0 ? 'positive' : 'negative'}`;
            this.updateKPIChange(marginCard, kpis.margin.change, true);
            this.renderKPISparkline(marginCard, monthlyData.map(d => d.net > 0 && d.income > 0 ? (d.net / d.income) * 100 : 0));
        }

        // EBITDA / Net Result
        const ebitdaEl = document.getElementById('kpi-ebitda');
        if (ebitdaEl) {
            const ebitdaCard = ebitdaEl.closest('.kpi-card');
            ebitdaEl.textContent = Utils.formatCurrency(kpis.net.value, { compact: true });
            ebitdaEl.className = `kpi-value ${kpis.net.value >= 0 ? 'positive' : 'negative'}`;
            this.updateKPIChange(ebitdaCard, kpis.net.change);
            this.renderKPISparkline(ebitdaCard, monthlyData.map(d => d.net));
        }

        // Income
        const incomeEl = document.getElementById('kpi-income');
        if (incomeEl) {
            const incomeCard = incomeEl.closest('.kpi-card');
            incomeEl.textContent = Utils.formatCurrency(kpis.income.value, { compact: true });
            this.updateKPIChange(incomeCard, kpis.income.change);
            this.renderKPISparkline(incomeCard, monthlyData.map(d => d.income));
        }

        // Expenses
        const expensesEl = document.getElementById('kpi-expenses');
        if (expensesEl) {
            const expensesCard = expensesEl.closest('.kpi-card');
            expensesEl.textContent = Utils.formatCurrency(kpis.expenses.value, { compact: true });
            this.updateKPIChange(expensesCard, kpis.expenses.change, false, true);
            this.renderKPISparkline(expensesCard, monthlyData.map(d => d.expenses));
        }

        // Gross Margin (using income as proxy for now)
        const grossMarginEl = document.getElementById('kpi-gross-margin');
        if (grossMarginEl) {
            const grossCard = grossMarginEl.closest('.kpi-card');
            const grossMargin = kpis.income.value > 0 ? ((kpis.income.value - kpis.expenses.value * 0.7) / kpis.income.value) * 100 : 0;
            grossMarginEl.textContent = Utils.formatPercent(grossMargin);
            grossMarginEl.className = `kpi-value ${grossMargin >= 0 ? 'positive' : 'negative'}`;
        }
    },

    updateKPIChange(card, change, isPercent = false, invertColors = false) {
        const changeEl = card?.querySelector('.kpi-change');
        if (!changeEl) return;

        const isUp = change > 0;
        const displayUp = invertColors ? !isUp : isUp;
        const arrow = isUp ? '↑' : (change < 0 ? '↓' : '');
        const value = isPercent ? Math.abs(change).toFixed(1) + ' pts' : Math.abs(change).toFixed(1) + '%';

        changeEl.className = `kpi-change ${displayUp ? 'up' : (change < 0 ? 'down' : 'neutral')}`;
        changeEl.innerHTML = `${arrow} ${value}`;
    },

    renderKPISparkline(card, data) {
        const container = card?.querySelector('.kpi-sparkline');
        if (!container || !data || data.length === 0) return;

        container.innerHTML = Charts.sparkline(data, { width: 120, height: 40 });
    },

    renderDashboardCharts(transactions) {
        const canvas = document.getElementById('chart-evolution');
        if (!canvas) return;

        const monthlyData = Charts.getMonthlyTrend(transactions, 12);

        Charts.lineChart(canvas, monthlyData, {
            labels: monthlyData.map(d => d.month),
            datasets: [
                {
                    data: monthlyData.map(d => d.income),
                    color: '#059669',
                    fillColor: 'rgba(5, 150, 105, 0.1)',
                    label: 'Ingresos'
                },
                {
                    data: monthlyData.map(d => d.expenses),
                    color: '#dc2626',
                    fillColor: 'rgba(220, 38, 38, 0.1)',
                    label: 'Gastos'
                }
            ]
        });
    },

    renderTopClients(transactions) {
        const container = document.getElementById('top-clients-list');
        if (!container) return;

        // Group by client
        const clientData = {};
        transactions.forEach(tx => {
            const client = tx.client || tx.client_id || 'Sin asignar';
            if (!clientData[client]) {
                clientData[client] = { income: 0, expenses: 0 };
            }
            const amount = parseFloat(tx.amount) || 0;
            if (amount > 0 || tx.side === 'credit') {
                clientData[client].income += Math.abs(amount);
            } else {
                clientData[client].expenses += Math.abs(amount);
            }
        });

        // Convert to array and sort
        const clients = Object.entries(clientData)
            .map(([name, data]) => ({
                name,
                net: data.income - data.expenses,
                income: data.income
            }))
            .filter(c => c.name !== 'Sin asignar')
            .sort((a, b) => b.income - a.income)
            .slice(0, 5);

        const maxIncome = Math.max(...clients.map(c => c.income));

        container.innerHTML = clients.length === 0
            ? '<div class="empty-state"><p>No hay datos de clientes</p></div>'
            : `<ul class="top-list">
                ${clients.map((client, i) => `
                    <li class="top-list-item" onclick="App.navigateTo('clients', { client: '${client.name}' })">
                        <span class="top-list-rank">${i + 1}</span>
                        <div class="top-list-info">
                            <div class="top-list-name">${client.name}</div>
                        </div>
                        <div class="top-list-value">
                            <div class="top-list-amount">${Utils.formatCurrency(client.income, { compact: true })}</div>
                        </div>
                        <div class="top-list-bar">
                            <div class="progress-bar">
                                <div class="progress-bar-fill positive" style="width: ${(client.income / maxIncome) * 100}%"></div>
                            </div>
                        </div>
                    </li>
                `).join('')}
            </ul>`;
    },

    renderTopProjects(transactions) {
        const container = document.getElementById('top-projects-list');
        if (!container) return;

        // Group by project
        const projectData = {};
        transactions.forEach(tx => {
            const projectId = tx.project_id || tx.project;
            if (!projectId) return;

            if (!projectData[projectId]) {
                const project = this.state.projects.find(p => p.id === projectId || p.name === projectId);
                projectData[projectId] = {
                    name: project?.name || projectId,
                    client: project?.client || '',
                    income: 0,
                    expenses: 0
                };
            }
            const amount = parseFloat(tx.amount) || 0;
            if (amount > 0 || tx.side === 'credit') {
                projectData[projectId].income += Math.abs(amount);
            } else {
                projectData[projectId].expenses += Math.abs(amount);
            }
        });

        const projects = Object.values(projectData)
            .map(p => ({ ...p, margin: p.income > 0 ? ((p.income - p.expenses) / p.income) * 100 : 0 }))
            .sort((a, b) => b.income - a.income)
            .slice(0, 5);

        container.innerHTML = projects.length === 0
            ? '<div class="empty-state"><p>No hay datos de proyectos</p></div>'
            : `<ul class="top-list">
                ${projects.map((project, i) => `
                    <li class="top-list-item" onclick="App.navigateTo('projects', { project: '${project.name}' })">
                        <span class="top-list-rank">${i + 1}</span>
                        <div class="top-list-info">
                            <div class="top-list-name">${project.name}</div>
                            <div class="top-list-subtitle">${project.client || 'Sin cliente'}</div>
                        </div>
                        <div class="top-list-value">
                            <div class="top-list-amount">${Utils.formatCurrency(project.income, { compact: true })}</div>
                            <div class="top-list-change ${project.margin >= 20 ? 'text-success' : project.margin >= 0 ? 'text-warning' : 'text-danger'}">
                                ${Utils.formatPercent(project.margin)} margen
                            </div>
                        </div>
                    </li>
                `).join('')}
            </ul>`;
    },

    renderRecentTransactions(transactions) {
        const tbody = document.getElementById('recent-transactions');
        if (!tbody) return;

        if (transactions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-muted" style="text-align:center;padding:40px;">No hay transacciones</td></tr>';
            return;
        }

        tbody.innerHTML = transactions.map(tx => {
            const amount = parseFloat(tx.amount) || 0;
            const isIncome = amount > 0 || tx.side === 'credit';

            return `
                <tr onclick="App.showTransactionDetail('${tx.id}')">
                    <td>${Utils.formatDate(tx.settled_at || tx.emitted_at)}</td>
                    <td>
                        <div style="font-weight:500;">${tx.counterparty_name || tx.label || '-'}</div>
                        <div class="text-muted text-xs">${tx.note || ''}</div>
                    </td>
                    <td>${tx.category || tx.qonto_category || '-'}</td>
                    <td>${tx.project || '-'}</td>
                    <td style="text-align:right;">
                        <span class="amount ${isIncome ? 'positive' : 'negative'}">
                            ${isIncome ? '+' : ''}${Utils.formatCurrency(amount)}
                        </span>
                    </td>
                </tr>
            `;
        }).join('');
    },

    renderAlerts() {
        const container = document.getElementById('alerts-panel');
        if (!container) return;

        // Generate alerts based on data analysis
        const alerts = [];

        // Check for pending review transactions
        const pendingCount = this.getPendingReviewCount();
        if (pendingCount > 0) {
            alerts.push({
                type: 'warning',
                title: `${pendingCount} transacciones pendientes`,
                message: 'Hay transacciones sin asignar a proyecto/cliente',
                action: () => this.navigateTo('review')
            });
        }

        // Check for negative margin projects
        const negativeMarginProjects = this.state.projects.filter(p => {
            const txs = this.state.transactions.filter(tx => tx.project_id === p.id || tx.project === p.name);
            const income = txs.filter(tx => parseFloat(tx.amount) > 0).reduce((s, tx) => s + parseFloat(tx.amount), 0);
            const expenses = txs.filter(tx => parseFloat(tx.amount) < 0).reduce((s, tx) => s + Math.abs(parseFloat(tx.amount)), 0);
            return income > 0 && (income - expenses) / income < 0;
        });

        if (negativeMarginProjects.length > 0) {
            alerts.push({
                type: 'danger',
                title: 'Proyectos con margen negativo',
                message: `${negativeMarginProjects.map(p => p.name).join(', ')}`,
                action: () => this.navigateTo('projects')
            });
        }

        container.innerHTML = alerts.length === 0
            ? '<div class="text-muted text-sm">Sin alertas activas</div>'
            : `<div class="alerts-list">
                ${alerts.map(alert => `
                    <div class="alert-item ${alert.type}" onclick="${alert.action ? 'App.' + alert.action.name + '()' : ''}">
                        <svg class="alert-icon" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"/>
                        </svg>
                        <div class="alert-content">
                            <div class="alert-title">${alert.title}</div>
                            <div class="alert-message">${alert.message}</div>
                        </div>
                    </div>
                `).join('')}
            </div>`;
    },

    // ========== Filtering ==========
    getFilteredTransactions() {
        let transactions = [...this.state.transactions];
        const { filters, currentPeriod, customDateRange } = this.state;

        // Date filter
        const dateRange = currentPeriod === 'custom'
            ? customDateRange
            : Utils.getDateRange(currentPeriod);

        if (dateRange.start) {
            transactions = transactions.filter(tx => {
                const txDate = new Date(tx.settled_at || tx.emitted_at);
                return txDate >= dateRange.start && (!dateRange.end || txDate <= dateRange.end);
            });
        }

        // Type filter
        if (filters.type) {
            transactions = transactions.filter(tx => {
                if (filters.type === 'credit') return tx.side === 'credit' || parseFloat(tx.amount) > 0;
                if (filters.type === 'debit') return tx.side === 'debit' || parseFloat(tx.amount) < 0;
                return true;
            });
        }

        // Category filter
        if (filters.category) {
            transactions = transactions.filter(tx =>
                tx.category === filters.category || tx.qonto_category === filters.category
            );
        }

        // Project filter
        if (filters.project) {
            transactions = transactions.filter(tx =>
                tx.project_id === filters.project || tx.project === filters.project
            );
        }

        // Client filter
        if (filters.client) {
            transactions = transactions.filter(tx =>
                tx.client_id === filters.client || tx.client === filters.client
            );
        }

        // Assignment filter
        if (filters.assigned) {
            transactions = transactions.filter(tx => {
                const hasAssignment = tx.project_id || tx.project || tx.client_id || tx.client;
                if (filters.assigned === 'assigned') return hasAssignment;
                if (filters.assigned === 'unassigned') return !hasAssignment;
                return true;
            });
        }

        // Search filter
        if (filters.search) {
            const search = filters.search.toLowerCase();
            transactions = transactions.filter(tx =>
                (tx.counterparty_name || '').toLowerCase().includes(search) ||
                (tx.label || '').toLowerCase().includes(search) ||
                (tx.note || '').toLowerCase().includes(search)
            );
        }

        // Sort
        transactions.sort((a, b) => {
            const aVal = a[this.state.sortField];
            const bVal = b[this.state.sortField];

            if (this.state.sortField === 'amount' || this.state.sortField === 'vat_amount') {
                return this.state.sortDirection === 'desc'
                    ? parseFloat(bVal || 0) - parseFloat(aVal || 0)
                    : parseFloat(aVal || 0) - parseFloat(bVal || 0);
            }

            if (aVal < bVal) return this.state.sortDirection === 'desc' ? 1 : -1;
            if (aVal > bVal) return this.state.sortDirection === 'desc' ? -1 : 1;
            return 0;
        });

        return transactions;
    },

    getPreviousPeriodTransactions() {
        const { currentPeriod } = this.state;

        if (currentPeriod === 'all' || currentPeriod === 'custom') {
            return [];
        }

        const prevRange = Utils.getDateRange('last-' + currentPeriod);
        if (!prevRange.start) return [];

        return this.state.transactions.filter(tx => {
            const txDate = new Date(tx.settled_at || tx.emitted_at);
            return txDate >= prevRange.start && txDate <= prevRange.end;
        });
    },

    // ========== Pending Review ==========
    getPendingReviewCount() {
        return this.state.transactions.filter(tx => {
            const hasProject = tx.project_id || tx.project;
            const hasClient = tx.client_id || tx.client;
            return !hasProject && !hasClient;
        }).length;
    },

    updatePendingCount() {
        const count = this.getPendingReviewCount();
        const badge = document.getElementById('review-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    },

    // ========== Keyboard Shortcuts ==========
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ignore if typing in input
            if (e.target.matches('input, textarea, select')) return;

            // Cmd/Ctrl + K: Open search
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                document.getElementById('global-search')?.focus();
                return;
            }

            // G + key navigation
            if (e.key === 'g') {
                this._waitingForNav = true;
                setTimeout(() => { this._waitingForNav = false; }, 500);
                return;
            }

            if (this._waitingForNav) {
                this._waitingForNav = false;
                switch (e.key) {
                    case 'd': this.navigateTo('dashboard'); break;
                    case 'c': this.navigateTo('clients'); break;
                    case 'p': this.navigateTo('projects'); break;
                    case 't': this.navigateTo('transactions'); break;
                    case 'r': this.navigateTo('review'); break;
                    case 's': this.navigateTo('settings'); break;
                }
            }

            // Escape: Close modals
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });
    },

    // ========== Search ==========
    setupSearch() {
        const searchInput = document.getElementById('global-search');
        if (!searchInput) return;

        searchInput.addEventListener('input', Utils.debounce((e) => {
            const query = e.target.value.trim().toLowerCase();
            if (query.length < 2) {
                this.hideSearchResults();
                return;
            }
            this.performSearch(query);
        }, 300));

        searchInput.addEventListener('focus', () => {
            const query = searchInput.value.trim();
            if (query.length >= 2) {
                this.showSearchResults();
            }
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box')) {
                this.hideSearchResults();
            }
        });
    },

    performSearch(query) {
        const results = {
            transactions: this.state.transactions
                .filter(tx =>
                    (tx.counterparty_name || '').toLowerCase().includes(query) ||
                    (tx.label || '').toLowerCase().includes(query)
                )
                .slice(0, 5),
            projects: this.state.projects
                .filter(p => p.name.toLowerCase().includes(query))
                .slice(0, 3),
            clients: this.state.clients
                .filter(c => c.name.toLowerCase().includes(query))
                .slice(0, 3)
        };

        this.showSearchResults(results);
    },

    showSearchResults(results) {
        // Implementation for search results dropdown
        const container = document.getElementById('search-results');
        if (!container) return;

        container.classList.add('active');
        // Render results...
    },

    hideSearchResults() {
        const container = document.getElementById('search-results');
        if (container) container.classList.remove('active');
    },

    // ========== Modals ==========
    setupModals() {
        // Close modal on overlay click
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    overlay.classList.remove('active');
                }
            });
        });
    },

    openModal(name) {
        const modal = document.getElementById(`modal-${name}`);
        if (modal) modal.classList.add('active');
    },

    closeModal(name) {
        const modal = document.getElementById(`modal-${name}`);
        if (modal) modal.classList.remove('active');
    },

    closeAllModals() {
        document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
    },

    // ========== Notifications ==========
    showNotification(message, type = 'info') {
        // Simple notification implementation
        const container = document.getElementById('notifications') || document.body;
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()">&times;</button>
        `;

        container.appendChild(notification);

        setTimeout(() => notification.remove(), 5000);
    },

    // ========== Loading States ==========
    showLoading() {
        document.body.classList.add('loading');
    },

    hideLoading() {
        document.body.classList.remove('loading');
    },

    // ========== Sync Status ==========
    async checkStatus() {
        try {
            const status = await API.sync.checkStatus();
            this.updateStatusIndicator(status);
        } catch (error) {
            this.updateStatusIndicator({ connected: false });
        }
    },

    updateStatusIndicator(status) {
        const indicator = document.getElementById('sync-status');
        if (!indicator) return;

        const dot = indicator.querySelector('.dot');
        const text = indicator.querySelector('span:last-child');

        if (status.connected !== false) {
            dot?.classList.remove('error');
            dot?.classList.add('success');
            if (text) text.textContent = 'Conectado';
        } else {
            dot?.classList.remove('success');
            dot?.classList.add('error');
            if (text) text.textContent = 'Desconectado';
        }
    },

    updateSyncStatus() {
        const el = document.getElementById('last-update-time');
        if (el && this.state.lastUpdate) {
            el.textContent = Utils.formatDate(this.state.lastUpdate.toISOString(), 'relative');
        }
    },

    // ========== Sync Actions ==========
    async syncQonto() {
        if (this.state.loading.sync) return;

        this.state.loading.sync = true;
        const btn = document.querySelector('[onclick*="syncQonto"]');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Sincronizando...';
        }

        try {
            await API.sync.all();
            await this.loadAllData();
            this.showNotification('Sincronización completada', 'success');
        } catch (error) {
            this.showNotification('Error al sincronizar: ' + error.message, 'error');
        } finally {
            this.state.loading.sync = false;
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = 'Sync Qonto';
            }
        }
    },

    // ========== Period Filter ==========
    setPeriod(period) {
        this.state.currentPeriod = period;

        // Update UI
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.period === period);
        });

        // Toggle custom date inputs
        const customInputs = document.getElementById('custom-dates');
        if (customInputs) {
            customInputs.classList.toggle('hidden', period !== 'custom');
        }

        this.renderCurrentView();
    }
};

// Make App globally available
window.App = App;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => App.init());
