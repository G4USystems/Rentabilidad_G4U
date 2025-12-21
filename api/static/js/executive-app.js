/* ============================================
   G4U Profitability - Executive Dashboard App
   Modern, Clean, Data-Focused Application
   ============================================ */

const App = {
    // State
    state: {
        transactions: [],
        projects: [],
        clients: [],
        categories: [],
        teamMembers: [],
        allocations: [],

        currentView: 'dashboard',
        currentPeriod: 'month',
        selectedTransaction: null,
        pendingAllocations: [],

        filters: {
            type: '',
            category: '',
            project: '',
            client: '',
            search: ''
        },

        loading: false,
        updateInterval: null
    },

    // Initialize
    async init() {
        console.log('G4U Profitability v2.0 - Executive Dashboard');

        this.setupNavigation();
        this.setupPeriodTabs();
        this.setupFilters();
        this.setupModals();
        this.setupScenarioOptions();
        this.setupSettingsMenu();

        await this.loadAllData();
        this.startAutoUpdate();
    },

    // ============================================
    // Data Loading
    // ============================================
    async loadAllData() {
        this.state.loading = true;
        this.setSyncStatus('syncing');

        try {
            const [dashboardData, clientsData, teamData, allocationsData] = await Promise.all([
                this.api('/api/dashboard_data'),
                this.api('/api/clients'),
                this.api('/api/team_members'),
                this.api('/api/v2/allocations').catch(() => ({ allocations: [] }))
            ]);

            this.state.transactions = dashboardData.transactions || [];
            this.state.projects = dashboardData.projects || [];
            this.state.categories = dashboardData.categories || [];
            this.state.clients = clientsData.clients || [];
            this.state.teamMembers = teamData.team_members || [];
            this.state.allocations = allocationsData.allocations || [];

            this.render();
            this.setSyncStatus('connected');

        } catch (error) {
            console.error('Error loading data:', error);
            this.toast('Error al cargar datos', 'error');
            this.setSyncStatus('error');
        }

        this.state.loading = false;
    },

    async api(url, options = {}) {
        const response = await fetch(url, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    },

    startAutoUpdate() {
        this.state.updateInterval = setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.loadAllData();
            }
        }, 30000);
    },

    setSyncStatus(status) {
        const dot = document.querySelector('.sync-dot');
        const text = document.querySelector('.sync-text');
        if (!dot || !text) return;

        dot.className = 'sync-dot';
        if (status === 'syncing') {
            dot.classList.add('syncing');
            text.textContent = 'Sincronizando...';
        } else if (status === 'connected') {
            text.textContent = 'Actualizado';
        } else {
            dot.style.background = 'var(--danger)';
            text.textContent = 'Error';
        }
    },

    // ============================================
    // Navigation
    // ============================================
    setupNavigation() {
        document.querySelectorAll('.nav-link[data-view]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const view = link.dataset.view;
                this.navigateTo(view);
            });
        });

        // Handle browser back/forward
        window.addEventListener('popstate', (e) => {
            if (e.state?.view) {
                this.navigateTo(e.state.view, false);
            }
        });
    },

    navigateTo(view, pushState = true) {
        // Update nav
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        document.querySelector(`.nav-link[data-view="${view}"]`)?.classList.add('active');

        // Update views
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${view}`)?.classList.add('active');

        // Update title
        const titles = {
            dashboard: 'Dashboard Ejecutivo',
            profitability: 'Rentabilidad',
            transactions: 'Transacciones',
            review: 'Revision',
            simulator: 'Simulador IA',
            settings: 'Configuracion'
        };
        document.getElementById('page-title').textContent = titles[view] || view;

        this.state.currentView = view;

        if (pushState) {
            history.pushState({ view }, '', `#${view}`);
        }

        this.render();
    },

    // ============================================
    // Rendering
    // ============================================
    render() {
        const view = this.state.currentView;

        switch (view) {
            case 'dashboard':
                this.renderDashboard();
                break;
            case 'profitability':
                this.renderProfitability();
                break;
            case 'transactions':
                this.renderTransactions();
                break;
            case 'review':
                this.renderReview();
                break;
            case 'simulator':
                this.renderSimulator();
                break;
            case 'settings':
                this.renderSettings();
                break;
        }

        this.updatePendingBadge();
    },

    // ============================================
    // Dashboard
    // ============================================
    renderDashboard() {
        const txs = this.getFilteredByPeriod();
        const prevTxs = this.getPreviousPeriod();

        // Calculate metrics
        const income = this.sumIncome(txs);
        const expenses = this.sumExpenses(txs);
        const net = income - expenses;
        const margin = income > 0 ? (net / income) * 100 : 0;

        const prevIncome = this.sumIncome(prevTxs);
        const prevExpenses = this.sumExpenses(prevTxs);
        const prevNet = prevIncome - prevExpenses;
        const prevMargin = prevIncome > 0 ? (prevNet / prevIncome) * 100 : 0;

        // Update hero metrics
        document.getElementById('hero-margin').textContent = this.formatPercent(margin);
        this.updateTrend('hero-margin-trend', margin - prevMargin, true);

        document.getElementById('hero-income').textContent = this.formatCurrency(income);
        document.getElementById('hero-income-count').textContent = `${txs.filter(t => this.isIncome(t)).length} transacciones`;

        document.getElementById('hero-expenses').textContent = this.formatCurrency(expenses);
        document.getElementById('hero-expenses-count').textContent = `${txs.filter(t => !this.isIncome(t)).length} transacciones`;

        const netEl = document.getElementById('hero-net');
        netEl.textContent = this.formatCurrency(net);
        netEl.className = `hero-metric-value ${net >= 0 ? 'positive' : 'negative'}`;

        const netChange = prevNet !== 0 ? ((net - prevNet) / Math.abs(prevNet)) * 100 : 0;
        document.getElementById('hero-net-trend').textContent = `${netChange >= 0 ? '+' : ''}${netChange.toFixed(1)}% vs anterior`;

        // Render charts
        this.renderCashFlowChart(txs);
        this.renderCategoryBars(txs);
        this.renderTopClients(txs);
        this.renderTopProjects(txs);

        // Pending alert
        const pending = this.getPendingCount();
        const alertEl = document.getElementById('pending-alert');
        if (pending > 0) {
            alertEl.style.display = 'flex';
            document.getElementById('pending-count').textContent = pending;
        } else {
            alertEl.style.display = 'none';
        }
    },

    renderCashFlowChart(txs) {
        const container = document.getElementById('chart-cashflow');
        if (!container) return;

        // Group by month
        const monthly = this.groupByMonth(txs, 6);
        const maxValue = Math.max(...monthly.map(m => Math.max(m.income, m.expenses)));

        const barWidth = 100 / (monthly.length * 3);

        container.innerHTML = `
            <svg viewBox="0 0 100 60" preserveAspectRatio="none" style="width:100%;height:100%;">
                ${monthly.map((m, i) => {
                    const x = i * (100 / monthly.length) + barWidth / 2;
                    const incomeH = maxValue > 0 ? (m.income / maxValue) * 50 : 0;
                    const expenseH = maxValue > 0 ? (m.expenses / maxValue) * 50 : 0;
                    return `
                        <rect x="${x}" y="${55 - incomeH}" width="${barWidth}" height="${incomeH}" fill="var(--success)" rx="1"/>
                        <rect x="${x + barWidth + 2}" y="${55 - expenseH}" width="${barWidth}" height="${expenseH}" fill="var(--danger)" rx="1"/>
                        <text x="${x + barWidth}" y="59" text-anchor="middle" font-size="3" fill="var(--text-muted)">${m.label}</text>
                    `;
                }).join('')}
            </svg>
        `;
    },

    renderCategoryBars(txs) {
        const container = document.getElementById('category-bars');
        if (!container) return;

        // Group expenses by category
        const categories = {};
        txs.filter(t => !this.isIncome(t)).forEach(t => {
            const cat = t.category || t.qonto_category || 'Sin categoria';
            categories[cat] = (categories[cat] || 0) + Math.abs(parseFloat(t.amount) || 0);
        });

        const sorted = Object.entries(categories)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 6);

        const maxVal = sorted[0]?.[1] || 1;

        container.innerHTML = sorted.length === 0
            ? '<div class="loading-placeholder">Sin datos de gastos</div>'
            : sorted.map(([name, value]) => `
                <div class="category-bar-item">
                    <div class="category-bar-label">${name}</div>
                    <div class="category-bar-track">
                        <div class="category-bar-fill" style="width: ${(value / maxVal) * 100}%"></div>
                    </div>
                    <div class="category-bar-value">${this.formatCurrency(value, true)}</div>
                </div>
            `).join('');
    },

    renderTopClients(txs) {
        const container = document.getElementById('top-clients');
        if (!container) return;

        const clientData = {};
        txs.forEach(t => {
            const client = t.client || t.client_id;
            if (!client) return;
            if (!clientData[client]) clientData[client] = { income: 0, expenses: 0 };
            if (this.isIncome(t)) {
                clientData[client].income += Math.abs(parseFloat(t.amount) || 0);
            } else {
                clientData[client].expenses += Math.abs(parseFloat(t.amount) || 0);
            }
        });

        const clients = Object.entries(clientData)
            .map(([name, data]) => ({
                name,
                income: data.income,
                net: data.income - data.expenses,
                margin: data.income > 0 ? ((data.income - data.expenses) / data.income) * 100 : 0
            }))
            .sort((a, b) => b.income - a.income)
            .slice(0, 5);

        container.innerHTML = clients.length === 0
            ? '<div class="loading-placeholder">Sin datos de clientes</div>'
            : clients.map((c, i) => `
                <div class="ranking-item" onclick="App.navigateTo('profitability')">
                    <span class="ranking-position">${i + 1}</span>
                    <div class="ranking-info">
                        <div class="ranking-name">${c.name}</div>
                    </div>
                    <div class="ranking-value">
                        <div class="ranking-amount">${this.formatCurrency(c.income, true)}</div>
                        <div class="ranking-margin ${c.margin >= 0 ? 'positive' : 'negative'}">${this.formatPercent(c.margin)}</div>
                    </div>
                </div>
            `).join('');
    },

    renderTopProjects(txs) {
        const container = document.getElementById('top-projects');
        if (!container) return;

        const projectData = {};
        txs.forEach(t => {
            const proj = t.project || t.project_id;
            if (!proj) return;
            if (!projectData[proj]) {
                const pInfo = this.state.projects.find(p => p.id === proj || p.name === proj);
                projectData[proj] = { name: pInfo?.name || proj, client: pInfo?.client || '', income: 0, expenses: 0 };
            }
            if (this.isIncome(t)) {
                projectData[proj].income += Math.abs(parseFloat(t.amount) || 0);
            } else {
                projectData[proj].expenses += Math.abs(parseFloat(t.amount) || 0);
            }
        });

        const projects = Object.values(projectData)
            .map(p => ({
                ...p,
                net: p.income - p.expenses,
                margin: p.income > 0 ? ((p.income - p.expenses) / p.income) * 100 : 0
            }))
            .sort((a, b) => b.income - a.income)
            .slice(0, 5);

        container.innerHTML = projects.length === 0
            ? '<div class="loading-placeholder">Sin datos de proyectos</div>'
            : projects.map((p, i) => `
                <div class="ranking-item" onclick="App.navigateTo('profitability')">
                    <span class="ranking-position">${i + 1}</span>
                    <div class="ranking-info">
                        <div class="ranking-name">${p.name}</div>
                        <div class="ranking-sub">${p.client || 'Sin cliente'}</div>
                    </div>
                    <div class="ranking-value">
                        <div class="ranking-amount">${this.formatCurrency(p.income, true)}</div>
                        <div class="ranking-margin ${p.margin >= 0 ? 'positive' : 'negative'}">${this.formatPercent(p.margin)}</div>
                    </div>
                </div>
            `).join('');
    },

    // ============================================
    // Profitability View
    // ============================================
    renderProfitability() {
        this.renderClientsProfitability();
        this.renderProjectsProfitability();
        this.setupProfitabilityTabs();
    },

    setupProfitabilityTabs() {
        document.querySelectorAll('.view-tab[data-subtab]').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                const subtab = tab.dataset.subtab;
                document.querySelectorAll('.subtab-content').forEach(c => c.classList.remove('active'));
                document.getElementById(`subtab-${subtab}`)?.classList.add('active');
            });
        });
    },

    renderClientsProfitability() {
        const container = document.getElementById('clients-profitability');
        if (!container) return;

        const txs = this.getFilteredByPeriod();
        const clientData = {};

        txs.forEach(t => {
            const client = t.client || t.client_id;
            if (!client) return;
            if (!clientData[client]) {
                const cInfo = this.state.clients.find(c => c.id === client || c.name === client);
                clientData[client] = { name: cInfo?.name || client, income: 0, expenses: 0 };
            }
            if (this.isIncome(t)) {
                clientData[client].income += Math.abs(parseFloat(t.amount) || 0);
            } else {
                clientData[client].expenses += Math.abs(parseFloat(t.amount) || 0);
            }
        });

        const clients = Object.values(clientData)
            .map(c => ({
                ...c,
                net: c.income - c.expenses,
                margin: c.income > 0 ? ((c.income - c.expenses) / c.income) * 100 : 0
            }))
            .sort((a, b) => b.income - a.income);

        container.innerHTML = clients.length === 0
            ? '<div class="loading-placeholder">No hay datos de clientes para el periodo seleccionado</div>'
            : clients.map(c => this.renderProfitabilityCard(c)).join('');
    },

    renderProjectsProfitability() {
        const container = document.getElementById('projects-profitability');
        if (!container) return;

        const txs = this.getFilteredByPeriod();
        const projectData = {};

        txs.forEach(t => {
            const proj = t.project || t.project_id;
            if (!proj) return;
            if (!projectData[proj]) {
                const pInfo = this.state.projects.find(p => p.id === proj || p.name === proj);
                projectData[proj] = { name: pInfo?.name || proj, client: pInfo?.client || '', status: pInfo?.status || 'Active', income: 0, expenses: 0 };
            }
            if (this.isIncome(t)) {
                projectData[proj].income += Math.abs(parseFloat(t.amount) || 0);
            } else {
                projectData[proj].expenses += Math.abs(parseFloat(t.amount) || 0);
            }
        });

        // Add projects without transactions
        this.state.projects.forEach(p => {
            const key = p.id || p.name;
            if (!projectData[key]) {
                projectData[key] = { name: p.name, client: p.client || '', status: p.status || 'Active', income: 0, expenses: 0 };
            }
        });

        const projects = Object.values(projectData)
            .map(p => ({
                ...p,
                net: p.income - p.expenses,
                margin: p.income > 0 ? ((p.income - p.expenses) / p.income) * 100 : 0
            }))
            .sort((a, b) => b.income - a.income);

        container.innerHTML = projects.length === 0
            ? '<div class="loading-placeholder">No hay proyectos</div>'
            : projects.map(p => this.renderProfitabilityCard(p, true)).join('');
    },

    renderProfitabilityCard(item, isProject = false) {
        const marginClass = item.margin >= 0 ? 'positive' : 'negative';
        const barWidth = Math.min(Math.abs(item.margin), 100);

        return `
            <div class="profitability-card">
                <div class="profitability-card-header">
                    <div>
                        <div class="profitability-card-name">${item.name}</div>
                        <div class="profitability-card-sub">${isProject ? (item.client || 'Sin cliente') : ''}</div>
                    </div>
                    <div class="profitability-card-margin ${marginClass}">${this.formatPercent(item.margin)}</div>
                </div>
                <div class="profitability-stats">
                    <div class="profitability-stat">
                        <div class="profitability-stat-label">Ingresos</div>
                        <div class="profitability-stat-value positive">${this.formatCurrency(item.income, true)}</div>
                    </div>
                    <div class="profitability-stat">
                        <div class="profitability-stat-label">Gastos</div>
                        <div class="profitability-stat-value negative">${this.formatCurrency(item.expenses, true)}</div>
                    </div>
                    <div class="profitability-stat">
                        <div class="profitability-stat-label">Resultado</div>
                        <div class="profitability-stat-value ${marginClass}">${this.formatCurrency(item.net, true)}</div>
                    </div>
                </div>
                <div class="profitability-bar">
                    <div class="profitability-bar-fill ${marginClass}" style="width: ${barWidth}%"></div>
                </div>
            </div>
        `;
    },

    // ============================================
    // Transactions View
    // ============================================
    renderTransactions() {
        this.populateFilters();
        this.renderTransactionsTable();
        this.updateTransactionStats();
    },

    populateFilters() {
        // Categories
        const catSelect = document.getElementById('filter-category');
        if (catSelect && catSelect.options.length <= 1) {
            const cats = [...new Set(this.state.transactions.map(t => t.category || t.qonto_category).filter(Boolean))];
            cats.sort().forEach(c => catSelect.appendChild(new Option(c, c)));
        }

        // Projects
        const projSelect = document.getElementById('filter-project');
        if (projSelect && projSelect.options.length <= 1) {
            this.state.projects.forEach(p => projSelect.appendChild(new Option(p.name, p.id || p.name)));
        }

        // Clients
        const clientSelect = document.getElementById('filter-client');
        if (clientSelect && clientSelect.options.length <= 1) {
            this.state.clients.forEach(c => clientSelect.appendChild(new Option(c.name, c.id || c.name)));
        }
    },

    setupFilters() {
        ['filter-type', 'filter-category', 'filter-project', 'filter-client'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', () => this.applyFilters());
        });

        document.getElementById('filter-search')?.addEventListener('input',
            this.debounce(() => this.applyFilters(), 300)
        );
    },

    applyFilters() {
        this.state.filters.type = document.getElementById('filter-type')?.value || '';
        this.state.filters.category = document.getElementById('filter-category')?.value || '';
        this.state.filters.project = document.getElementById('filter-project')?.value || '';
        this.state.filters.client = document.getElementById('filter-client')?.value || '';
        this.state.filters.search = document.getElementById('filter-search')?.value || '';

        this.renderTransactionsTable();
        this.updateTransactionStats();
    },

    clearFilters() {
        document.getElementById('filter-type').value = '';
        document.getElementById('filter-category').value = '';
        document.getElementById('filter-project').value = '';
        document.getElementById('filter-client').value = '';
        document.getElementById('filter-search').value = '';

        this.state.filters = { type: '', category: '', project: '', client: '', search: '' };
        this.renderTransactionsTable();
        this.updateTransactionStats();
    },

    getFilteredTransactions() {
        let txs = this.getFilteredByPeriod();
        const { type, category, project, client, search } = this.state.filters;

        if (type) {
            txs = txs.filter(t => type === 'income' ? this.isIncome(t) : !this.isIncome(t));
        }
        if (category) {
            txs = txs.filter(t => (t.category || t.qonto_category) === category);
        }
        if (project) {
            txs = txs.filter(t => (t.project || t.project_id) === project);
        }
        if (client) {
            txs = txs.filter(t => (t.client || t.client_id) === client);
        }
        if (search) {
            const q = search.toLowerCase();
            txs = txs.filter(t =>
                (t.counterparty_name || '').toLowerCase().includes(q) ||
                (t.label || '').toLowerCase().includes(q) ||
                (t.note || '').toLowerCase().includes(q)
            );
        }

        return txs.sort((a, b) => new Date(b.settled_at || b.emitted_at) - new Date(a.settled_at || a.emitted_at));
    },

    renderTransactionsTable() {
        const tbody = document.getElementById('transactions-table');
        if (!tbody) return;

        const txs = this.getFilteredTransactions().slice(0, 100);

        tbody.innerHTML = txs.length === 0
            ? '<tr><td colspan="7" class="empty-cell">No hay transacciones</td></tr>'
            : txs.map(t => {
                const amount = parseFloat(t.amount) || 0;
                const isIncome = this.isIncome(t);
                const proj = t.project || t.project_id;
                const client = t.client || t.client_id;

                return `
                    <tr>
                        <td>${this.formatDate(t.settled_at || t.emitted_at)}</td>
                        <td>
                            <div class="tx-desc">${t.counterparty_name || t.label || '-'}</div>
                            ${t.note ? `<div class="tx-note">${t.note}</div>` : ''}
                        </td>
                        <td><span class="tx-tag">${t.category || t.qonto_category || '-'}</span></td>
                        <td>${proj ? `<span class="tx-tag">${proj}</span>` : '<span class="tx-unassigned">-</span>'}</td>
                        <td>${client || '<span class="tx-unassigned">-</span>'}</td>
                        <td class="tx-amount ${isIncome ? 'positive' : 'negative'}">${isIncome ? '+' : ''}${this.formatCurrency(amount)}</td>
                        <td>
                            <button class="btn btn-ghost btn-sm" onclick="App.openAssignment('${t.id}')" title="Asignar">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                                    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                                </svg>
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
    },

    updateTransactionStats() {
        const txs = this.getFilteredTransactions();
        const income = this.sumIncome(txs);
        const expenses = this.sumExpenses(txs);
        const unassigned = txs.filter(t => !t.project && !t.project_id && !t.client && !t.client_id).length;

        document.getElementById('tx-total').textContent = txs.length;
        document.getElementById('tx-income').textContent = this.formatCurrency(income);
        document.getElementById('tx-expenses').textContent = this.formatCurrency(expenses);
        document.getElementById('tx-unassigned').textContent = unassigned;
    },

    // ============================================
    // Review View (with % Allocation)
    // ============================================
    renderReview() {
        const pending = this.state.transactions.filter(t =>
            !t.project && !t.project_id && !t.client && !t.client_id && !t.excluded
        );

        document.getElementById('review-total').textContent = pending.length;
        this.renderReviewList(pending);
        this.setupReviewSort();
    },

    setupReviewSort() {
        document.getElementById('review-sort')?.addEventListener('change', () => {
            this.renderReview();
        });
    },

    renderReviewList(pending) {
        const container = document.getElementById('review-list');
        if (!container) return;

        const sortValue = document.getElementById('review-sort')?.value || 'date-desc';
        pending = [...pending].sort((a, b) => {
            if (sortValue === 'date-asc') return new Date(a.settled_at) - new Date(b.settled_at);
            if (sortValue === 'amount-desc') return Math.abs(parseFloat(b.amount)) - Math.abs(parseFloat(a.amount));
            if (sortValue === 'amount-asc') return Math.abs(parseFloat(a.amount)) - Math.abs(parseFloat(b.amount));
            return new Date(b.settled_at) - new Date(a.settled_at);
        });

        if (pending.length === 0) {
            container.innerHTML = `
                <div class="assignment-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <p>Todas las transacciones estan asignadas</p>
                </div>
            `;
            return;
        }

        container.innerHTML = pending.map(t => {
            const amount = parseFloat(t.amount) || 0;
            const isIncome = this.isIncome(t);
            const isSelected = this.state.selectedTransaction === t.id;

            return `
                <div class="review-item ${isSelected ? 'selected' : ''}" data-id="${t.id}" onclick="App.selectReviewItem('${t.id}')">
                    <div class="review-item-content">
                        <div class="review-item-title">${t.counterparty_name || t.label || 'Sin descripcion'}</div>
                        <div class="review-item-meta">
                            <span>${this.formatDate(t.settled_at || t.emitted_at)}</span>
                            <span>${t.qonto_category || '-'}</span>
                        </div>
                    </div>
                    <div class="review-item-amount ${isIncome ? 'positive' : 'negative'}">
                        ${isIncome ? '+' : ''}${this.formatCurrency(amount)}
                    </div>
                </div>
            `;
        }).join('');
    },

    selectReviewItem(txId) {
        this.state.selectedTransaction = txId;
        this.state.pendingAllocations = [];

        // Update selection UI
        document.querySelectorAll('.review-item').forEach(el => {
            el.classList.toggle('selected', el.dataset.id === txId);
        });

        // Render assignment panel
        const tx = this.state.transactions.find(t => t.id === txId);
        if (!tx) return;

        const panel = document.getElementById('assignment-panel');
        const amount = parseFloat(tx.amount) || 0;
        const isIncome = this.isIncome(tx);

        panel.innerHTML = `
            <div class="assignment-header">
                <div class="assignment-tx-info">
                    <div class="assignment-tx-title">${tx.counterparty_name || tx.label || 'Transaccion'}</div>
                    <div class="assignment-tx-amount ${isIncome ? 'positive' : 'negative'}">
                        ${isIncome ? '+' : ''}${this.formatCurrency(amount)}
                    </div>
                    <div class="assignment-tx-meta">
                        ${this.formatDate(tx.settled_at || tx.emitted_at)} - ${tx.qonto_category || 'Sin categoria'}
                    </div>
                </div>
            </div>
            <div class="assignment-body">
                <div class="ai-suggestion" id="review-ai-suggestion" style="display:none;">
                    <div class="ai-suggestion-header">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 2a4 4 0 014 4c0 1.1-.9 2-2 2h-4a2 2 0 01-2-2 4 4 0 014-4z"/>
                            <path d="M12 8v8M8 12h8"/>
                            <circle cx="12" cy="19" r="2"/>
                        </svg>
                        <span>Sugerencia IA</span>
                    </div>
                    <div class="ai-suggestion-content" id="review-ai-content"></div>
                    <button class="btn btn-secondary btn-sm" onclick="App.applyReviewSuggestion()">Aplicar</button>
                </div>

                <div class="allocations-section">
                    <div class="allocations-header">
                        <h4>Asignaciones</h4>
                        <button class="btn btn-ghost btn-sm" onclick="App.addReviewAllocation()">+ Agregar</button>
                    </div>
                    <div class="allocations-list" id="review-allocations">
                        ${this.renderAllocationRow(0)}
                    </div>
                    <div class="allocations-total" id="review-allocations-total">
                        <span>Total asignado:</span>
                        <span class="total-pct">0%</span>
                    </div>
                </div>
            </div>
            <div class="assignment-footer">
                <button class="btn btn-danger" onclick="App.excludeReviewTransaction()">Excluir</button>
                <div style="flex:1;"></div>
                <button class="btn btn-ghost" onclick="App.cancelReview()">Cancelar</button>
                <button class="btn btn-primary" onclick="App.saveReviewAssignment()">Guardar</button>
            </div>
        `;

        // Initialize with one allocation row
        this.state.pendingAllocations = [{ project: '', client: '', percentage: 100 }];
    },

    renderAllocationRow(index) {
        const projects = this.state.projects.map(p => `<option value="${p.id || p.name}">${p.name}</option>`).join('');
        const clients = this.state.clients.map(c => `<option value="${c.id || c.name}">${c.name}</option>`).join('');

        return `
            <div class="allocation-row" data-index="${index}">
                <select class="alloc-project" onchange="App.updateAllocation(${index}, 'project', this.value)">
                    <option value="">Proyecto...</option>
                    ${projects}
                </select>
                <select class="alloc-client" onchange="App.updateAllocation(${index}, 'client', this.value)">
                    <option value="">Cliente...</option>
                    ${clients}
                </select>
                <input type="number" class="pct-input" value="100" min="0" max="100"
                       onchange="App.updateAllocation(${index}, 'percentage', this.value)">
                <button class="remove-btn" onclick="App.removeAllocation(${index})" ${index === 0 ? 'disabled' : ''}>
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>
        `;
    },

    addReviewAllocation() {
        const index = this.state.pendingAllocations.length;
        this.state.pendingAllocations.push({ project: '', client: '', percentage: 0 });

        const container = document.getElementById('review-allocations');
        container.insertAdjacentHTML('beforeend', this.renderAllocationRow(index));
        this.updateAllocationTotal();
    },

    updateAllocation(index, field, value) {
        if (this.state.pendingAllocations[index]) {
            this.state.pendingAllocations[index][field] = field === 'percentage' ? parseInt(value) || 0 : value;
        }
        this.updateAllocationTotal();
    },

    removeAllocation(index) {
        if (index === 0) return;
        this.state.pendingAllocations.splice(index, 1);
        this.rerenderAllocations();
    },

    rerenderAllocations() {
        const container = document.getElementById('review-allocations');
        container.innerHTML = this.state.pendingAllocations.map((_, i) => this.renderAllocationRow(i)).join('');

        // Restore values
        this.state.pendingAllocations.forEach((alloc, i) => {
            const row = container.querySelector(`[data-index="${i}"]`);
            if (row) {
                row.querySelector('.alloc-project').value = alloc.project || '';
                row.querySelector('.alloc-client').value = alloc.client || '';
                row.querySelector('.pct-input').value = alloc.percentage;
            }
        });

        this.updateAllocationTotal();
    },

    updateAllocationTotal() {
        const total = this.state.pendingAllocations.reduce((sum, a) => sum + (a.percentage || 0), 0);
        const totalEl = document.getElementById('review-allocations-total');
        if (totalEl) {
            totalEl.className = `allocations-total ${total === 100 ? 'valid' : 'invalid'}`;
            totalEl.querySelector('.total-pct').textContent = `${total}%`;
        }
    },

    async saveReviewAssignment() {
        const txId = this.state.selectedTransaction;
        if (!txId) return;

        const total = this.state.pendingAllocations.reduce((sum, a) => sum + (a.percentage || 0), 0);
        if (total !== 100) {
            this.toast('El total debe ser 100%', 'warning');
            return;
        }

        const validAllocations = this.state.pendingAllocations.filter(a => a.project || a.client);
        if (validAllocations.length === 0) {
            this.toast('Selecciona al menos un proyecto o cliente', 'warning');
            return;
        }

        try {
            // If single 100% allocation, update transaction directly
            if (validAllocations.length === 1 && validAllocations[0].percentage === 100) {
                const alloc = validAllocations[0];
                await this.api(`/api/transactions/${txId}`, {
                    method: 'PUT',
                    body: JSON.stringify({
                        project_id: alloc.project || null,
                        client_id: alloc.client || null
                    })
                });
            } else {
                // Multiple allocations - save to allocations endpoint
                await this.api('/api/v2/allocations', {
                    method: 'POST',
                    body: JSON.stringify({
                        transaction_id: txId,
                        allocations: validAllocations.map(a => ({
                            project_id: a.project || null,
                            client_id: a.client || null,
                            percentage: a.percentage
                        }))
                    })
                });
            }

            // Update local state
            const tx = this.state.transactions.find(t => t.id === txId);
            if (tx && validAllocations.length === 1) {
                tx.project_id = validAllocations[0].project;
                tx.client_id = validAllocations[0].client;
            }

            this.toast('Transaccion asignada correctamente', 'success');
            this.state.selectedTransaction = null;
            this.state.pendingAllocations = [];
            this.renderReview();

        } catch (error) {
            console.error('Error saving assignment:', error);
            this.toast('Error al guardar asignacion', 'error');
        }
    },

    async excludeReviewTransaction() {
        const txId = this.state.selectedTransaction;
        if (!txId) return;

        try {
            await this.api(`/api/transactions/${txId}`, {
                method: 'PUT',
                body: JSON.stringify({ excluded: true })
            });

            const tx = this.state.transactions.find(t => t.id === txId);
            if (tx) tx.excluded = true;

            this.toast('Transaccion excluida', 'success');
            this.state.selectedTransaction = null;
            this.renderReview();

        } catch (error) {
            this.toast('Error al excluir transaccion', 'error');
        }
    },

    cancelReview() {
        this.state.selectedTransaction = null;
        this.state.pendingAllocations = [];

        document.querySelectorAll('.review-item').forEach(el => el.classList.remove('selected'));

        document.getElementById('assignment-panel').innerHTML = `
            <div class="assignment-empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
                    <rect x="9" y="3" width="6" height="4" rx="1"/>
                    <path d="M9 14l2 2 4-4"/>
                </svg>
                <p>Selecciona una transaccion para asignar</p>
            </div>
        `;
    },

    // ============================================
    // AI Simulator
    // ============================================
    renderSimulator() {
        // Populate project select
        const projSelect = document.getElementById('sim-project');
        if (projSelect && projSelect.options.length <= 1) {
            this.state.projects.forEach(p => projSelect.appendChild(new Option(p.name, p.id || p.name)));
        }
    },

    setupScenarioOptions() {
        document.querySelectorAll('input[name="scenario-type"]').forEach(radio => {
            radio.addEventListener('change', () => {
                const value = radio.value;
                document.getElementById('sim-project-group').style.display = value === 'new_project' ? 'block' : 'none';
                document.getElementById('sim-custom-group').style.display = value === 'custom' ? 'block' : 'none';
            });
        });
    },

    async runSimulation() {
        const btn = document.getElementById('btn-simulate');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Procesando...';

        const scenarioType = document.querySelector('input[name="scenario-type"]:checked')?.value || 'growth';
        const period = parseInt(document.getElementById('sim-period')?.value) || 6;
        const variation = parseFloat(document.getElementById('sim-variation')?.value) || 10;

        try {
            const result = await this.api('/api/v2/scenarios/simulate', {
                method: 'POST',
                body: JSON.stringify({
                    scenario_type: scenarioType,
                    months: period,
                    variation_percent: variation,
                    project_id: document.getElementById('sim-project')?.value || null,
                    custom_prompt: document.getElementById('sim-custom')?.value || null
                })
            });

            this.renderSimulationResults(result);

        } catch (error) {
            console.error('Simulation error:', error);
            this.toast('Error al ejecutar simulacion', 'error');
        }

        btn.disabled = false;
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Ejecutar Simulacion
        `;
    },

    renderSimulationResults(result) {
        const container = document.getElementById('simulator-results');
        const output = document.getElementById('simulation-output');

        container.style.display = 'block';

        const current = result.current || {};
        const projected = result.projected || {};
        const diff = {
            income: (projected.income || 0) - (current.income || 0),
            expenses: (projected.expenses || 0) - (current.expenses || 0),
            net: (projected.net || 0) - (current.net || 0),
            margin: (projected.margin || 0) - (current.margin || 0)
        };

        output.innerHTML = `
            <div class="simulation-metric">
                <span class="simulation-metric-label">Ingresos Proyectados</span>
                <span class="simulation-metric-value positive">${this.formatCurrency(projected.income || 0)}</span>
            </div>
            <div class="simulation-metric">
                <span class="simulation-metric-label">Gastos Proyectados</span>
                <span class="simulation-metric-value negative">${this.formatCurrency(projected.expenses || 0)}</span>
            </div>
            <div class="simulation-metric">
                <span class="simulation-metric-label">Resultado Neto</span>
                <span class="simulation-metric-value ${projected.net >= 0 ? 'positive' : 'negative'}">${this.formatCurrency(projected.net || 0)}</span>
            </div>
            <div class="simulation-metric">
                <span class="simulation-metric-label">Margen Proyectado</span>
                <span class="simulation-metric-value ${projected.margin >= 0 ? 'positive' : 'negative'}">${this.formatPercent(projected.margin || 0)}</span>
            </div>

            ${result.insight ? `
                <div class="simulation-insight">
                    <div class="simulation-insight-title">Analisis IA</div>
                    <div class="simulation-insight-text">${result.insight}</div>
                </div>
            ` : ''}

            ${result.recommendations?.length > 0 ? `
                <div class="simulation-insight" style="margin-top: var(--space-md);">
                    <div class="simulation-insight-title">Recomendaciones</div>
                    <ul style="margin:0;padding-left:20px;">
                        ${result.recommendations.map(r => `<li>${r}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        `;
    },

    // ============================================
    // Settings
    // ============================================
    renderSettings() {
        this.renderClientsSettings();
        this.renderProjectsSettings();
        this.renderTeamSettings();
        this.renderCategoriesSettings();
    },

    setupSettingsMenu() {
        document.querySelectorAll('.settings-menu-item').forEach(item => {
            item.addEventListener('click', () => {
                document.querySelectorAll('.settings-menu-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');

                const panel = item.dataset.settings;
                document.querySelectorAll('.settings-panel').forEach(p => p.classList.remove('active'));
                document.getElementById(`settings-${panel}`)?.classList.add('active');
            });
        });
    },

    renderClientsSettings() {
        const container = document.getElementById('clients-table-container');
        if (!container) return;

        container.innerHTML = this.state.clients.length === 0
            ? '<div class="loading-placeholder">No hay clientes</div>'
            : `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Nombre</th>
                            <th>Contacto</th>
                            <th>Email</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.state.clients.map(c => `
                            <tr>
                                <td><strong>${c.name}</strong></td>
                                <td>${c.contact || '-'}</td>
                                <td>${c.email || '-'}</td>
                                <td>
                                    <button class="btn btn-ghost btn-sm" onclick="App.deleteClient('${c.id}')">Eliminar</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
    },

    renderProjectsSettings() {
        const container = document.getElementById('projects-table-container');
        if (!container) return;

        container.innerHTML = this.state.projects.length === 0
            ? '<div class="loading-placeholder">No hay proyectos</div>'
            : `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Nombre</th>
                            <th>Cliente</th>
                            <th>Estado</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.state.projects.map(p => `
                            <tr>
                                <td><strong>${p.name}</strong></td>
                                <td>${p.client || '-'}</td>
                                <td><span class="tx-tag">${p.status || 'Active'}</span></td>
                                <td>
                                    <button class="btn btn-ghost btn-sm" onclick="App.deleteProject('${p.id}')">Eliminar</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
    },

    renderTeamSettings() {
        const container = document.getElementById('team-table-container');
        if (!container) return;

        container.innerHTML = this.state.teamMembers.length === 0
            ? '<div class="loading-placeholder">No hay miembros</div>'
            : `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Nombre</th>
                            <th>Rol</th>
                            <th>Salario</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.state.teamMembers.map(m => `
                            <tr>
                                <td><strong>${m.name}</strong></td>
                                <td>${m.role || '-'}</td>
                                <td>${this.formatCurrency(m.salary || 0)}</td>
                                <td>
                                    <button class="btn btn-ghost btn-sm" onclick="App.deleteMember('${m.id}')">Eliminar</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
    },

    renderCategoriesSettings() {
        const container = document.getElementById('categories-table-container');
        if (!container) return;

        container.innerHTML = this.state.categories.length === 0
            ? '<div class="loading-placeholder">No hay categorias</div>'
            : `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Nombre</th>
                            <th>Tipo</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.state.categories.map(c => `
                            <tr>
                                <td><strong>${c.name}</strong></td>
                                <td><span class="tx-tag">${c.type === 'Income' ? 'Ingreso' : 'Gasto'}</span></td>
                                <td>
                                    <button class="btn btn-ghost btn-sm" onclick="App.deleteCategory('${c.id}')">Eliminar</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
    },

    // ============================================
    // CRUD Operations
    // ============================================
    async saveClient() {
        const data = {
            name: document.getElementById('new-client-name')?.value,
            contact: document.getElementById('new-client-contact')?.value,
            email: document.getElementById('new-client-email')?.value,
            phone: document.getElementById('new-client-phone')?.value
        };

        if (!data.name) {
            this.toast('El nombre es requerido', 'warning');
            return;
        }

        try {
            await this.api('/api/clients', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            this.closeModal('add-client');
            await this.loadAllData();
            this.toast('Cliente creado', 'success');
        } catch (error) {
            this.toast('Error al crear cliente', 'error');
        }
    },

    async saveProject() {
        const data = {
            name: document.getElementById('new-project-name')?.value,
            client: document.getElementById('new-project-client')?.value,
            status: document.getElementById('new-project-status')?.value
        };

        if (!data.name) {
            this.toast('El nombre es requerido', 'warning');
            return;
        }

        try {
            await this.api('/api/projects', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            this.closeModal('add-project');
            await this.loadAllData();
            this.toast('Proyecto creado', 'success');
        } catch (error) {
            this.toast('Error al crear proyecto', 'error');
        }
    },

    async saveTeamMember() {
        const data = {
            name: document.getElementById('new-member-name')?.value,
            role: document.getElementById('new-member-role')?.value,
            salary: parseFloat(document.getElementById('new-member-salary')?.value) || 0
        };

        if (!data.name) {
            this.toast('El nombre es requerido', 'warning');
            return;
        }

        try {
            await this.api('/api/team_members', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            this.closeModal('add-member');
            await this.loadAllData();
            this.toast('Miembro agregado', 'success');
        } catch (error) {
            this.toast('Error al agregar miembro', 'error');
        }
    },

    async saveCategory() {
        const data = {
            name: document.getElementById('new-category-name')?.value,
            type: document.getElementById('new-category-type')?.value
        };

        if (!data.name) {
            this.toast('El nombre es requerido', 'warning');
            return;
        }

        try {
            await this.api('/api/categories', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            this.closeModal('add-category');
            await this.loadAllData();
            this.toast('Categoria creada', 'success');
        } catch (error) {
            this.toast('Error al crear categoria', 'error');
        }
    },

    async syncQonto() {
        this.toast('Sincronizando con Qonto...', 'info');
        try {
            await this.api('/api/sync_all', { method: 'POST' });
            await this.loadAllData();
            this.toast('Sincronizacion completada', 'success');
        } catch (error) {
            this.toast('Error al sincronizar', 'error');
        }
    },

    async testAirtable() {
        try {
            await this.api('/api/test_airtable');
            this.toast('Conexion exitosa', 'success');
        } catch (error) {
            this.toast('Error de conexion', 'error');
        }
    },

    // ============================================
    // Modals
    // ============================================
    setupModals() {
        document.getElementById('modal-overlay')?.addEventListener('click', () => {
            this.closeAllModals();
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeAllModals();
        });
    },

    openModal(name) {
        document.getElementById('modal-overlay')?.classList.add('active');
        document.getElementById(`modal-${name}`)?.classList.add('active');

        // Populate client select for project modal
        if (name === 'add-project') {
            const select = document.getElementById('new-project-client');
            if (select && select.options.length <= 1) {
                this.state.clients.forEach(c => select.appendChild(new Option(c.name, c.name)));
            }
        }
    },

    closeModal(name) {
        document.getElementById('modal-overlay')?.classList.remove('active');
        document.getElementById(`modal-${name}`)?.classList.remove('active');
    },

    closeAllModals() {
        document.getElementById('modal-overlay')?.classList.remove('active');
        document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
    },

    openAssignment(txId) {
        this.state.selectedTransaction = txId;
        this.state.pendingAllocations = [{ project: '', client: '', percentage: 100 }];

        const tx = this.state.transactions.find(t => t.id === txId);
        if (!tx) return;

        const amount = parseFloat(tx.amount) || 0;
        const isIncome = this.isIncome(tx);

        document.getElementById('modal-tx-detail').innerHTML = `
            <div class="tx-detail-title">${tx.counterparty_name || tx.label || 'Transaccion'}</div>
            <div class="tx-detail-amount ${isIncome ? 'positive' : 'negative'}">
                ${isIncome ? '+' : ''}${this.formatCurrency(amount)}
            </div>
            <div class="tx-detail-meta">
                <span>${this.formatDate(tx.settled_at || tx.emitted_at)}</span>
                <span>${tx.qonto_category || '-'}</span>
            </div>
        `;

        const allocsList = document.getElementById('allocations-list');
        allocsList.innerHTML = this.renderAllocationRow(0);

        this.updateModalAllocationTotal();
        this.openModal('assignment');
    },

    updateModalAllocationTotal() {
        const total = this.state.pendingAllocations.reduce((sum, a) => sum + (a.percentage || 0), 0);
        const totalEl = document.getElementById('allocations-total');
        if (totalEl) {
            totalEl.className = `allocations-total ${total === 100 ? 'valid' : 'invalid'}`;
            totalEl.querySelector('.total-pct').textContent = `${total}%`;
        }
    },

    addAllocationRow() {
        const index = this.state.pendingAllocations.length;
        this.state.pendingAllocations.push({ project: '', client: '', percentage: 0 });

        const container = document.getElementById('allocations-list');
        container.insertAdjacentHTML('beforeend', this.renderAllocationRow(index));
        this.updateModalAllocationTotal();
    },

    async saveAssignment() {
        // Reuse the review save logic
        const txId = this.state.selectedTransaction;
        if (!txId) return;

        const total = this.state.pendingAllocations.reduce((sum, a) => sum + (a.percentage || 0), 0);
        if (total !== 100) {
            this.toast('El total debe ser 100%', 'warning');
            return;
        }

        const validAllocations = this.state.pendingAllocations.filter(a => a.project || a.client);
        if (validAllocations.length === 0) {
            this.toast('Selecciona al menos un proyecto o cliente', 'warning');
            return;
        }

        try {
            if (validAllocations.length === 1 && validAllocations[0].percentage === 100) {
                const alloc = validAllocations[0];
                await this.api(`/api/transactions/${txId}`, {
                    method: 'PUT',
                    body: JSON.stringify({
                        project_id: alloc.project || null,
                        client_id: alloc.client || null
                    })
                });

                const tx = this.state.transactions.find(t => t.id === txId);
                if (tx) {
                    tx.project_id = alloc.project;
                    tx.client_id = alloc.client;
                }
            }

            this.toast('Transaccion asignada', 'success');
            this.closeModal('assignment');
            this.render();

        } catch (error) {
            this.toast('Error al guardar', 'error');
        }
    },

    async excludeTransaction() {
        const txId = this.state.selectedTransaction;
        if (!txId) return;

        try {
            await this.api(`/api/transactions/${txId}`, {
                method: 'PUT',
                body: JSON.stringify({ excluded: true })
            });

            const tx = this.state.transactions.find(t => t.id === txId);
            if (tx) tx.excluded = true;

            this.toast('Transaccion excluida', 'success');
            this.closeModal('assignment');
            this.render();

        } catch (error) {
            this.toast('Error al excluir', 'error');
        }
    },

    // ============================================
    // Period Filter
    // ============================================
    setupPeriodTabs() {
        document.querySelectorAll('.period-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.period-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.state.currentPeriod = tab.dataset.period;
                this.render();
            });
        });

        document.getElementById('btn-sync')?.addEventListener('click', () => {
            this.syncQonto();
        });
    },

    getFilteredByPeriod() {
        const period = this.state.currentPeriod;
        const now = new Date();
        let start;

        switch (period) {
            case 'week':
                start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                break;
            case 'month':
                start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                break;
            case 'quarter':
                start = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
                break;
            case 'year':
                start = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
                break;
            default:
                return this.state.transactions;
        }

        return this.state.transactions.filter(t => {
            const txDate = new Date(t.settled_at || t.emitted_at);
            return txDate >= start;
        });
    },

    getPreviousPeriod() {
        const period = this.state.currentPeriod;
        const now = new Date();
        let start, end;

        const days = { week: 7, month: 30, quarter: 90, year: 365 }[period] || 30;

        end = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
        start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);

        return this.state.transactions.filter(t => {
            const txDate = new Date(t.settled_at || t.emitted_at);
            return txDate >= start && txDate < end;
        });
    },

    // ============================================
    // Utilities
    // ============================================
    isIncome(tx) {
        const amount = parseFloat(tx.amount) || 0;
        return tx.side === 'credit' || amount > 0;
    },

    sumIncome(txs) {
        return txs.filter(t => this.isIncome(t)).reduce((sum, t) => sum + Math.abs(parseFloat(t.amount) || 0), 0);
    },

    sumExpenses(txs) {
        return txs.filter(t => !this.isIncome(t)).reduce((sum, t) => sum + Math.abs(parseFloat(t.amount) || 0), 0);
    },

    getPendingCount() {
        return this.state.transactions.filter(t =>
            !t.project && !t.project_id && !t.client && !t.client_id && !t.excluded
        ).length;
    },

    updatePendingBadge() {
        const count = this.getPendingCount();
        const badge = document.getElementById('review-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    },

    groupByMonth(txs, months = 6) {
        const result = [];
        const now = new Date();

        for (let i = months - 1; i >= 0; i--) {
            const month = new Date(now.getFullYear(), now.getMonth() - i, 1);
            const monthEnd = new Date(now.getFullYear(), now.getMonth() - i + 1, 0);

            const monthTxs = txs.filter(t => {
                const date = new Date(t.settled_at || t.emitted_at);
                return date >= month && date <= monthEnd;
            });

            result.push({
                label: month.toLocaleString('es', { month: 'short' }),
                income: this.sumIncome(monthTxs),
                expenses: this.sumExpenses(monthTxs)
            });
        }

        return result;
    },

    formatCurrency(value, compact = false) {
        const num = parseFloat(value) || 0;
        if (compact && Math.abs(num) >= 1000) {
            return (num / 1000).toFixed(1) + 'k€';
        }
        return new Intl.NumberFormat('es-ES', {
            style: 'currency',
            currency: 'EUR',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(num);
    },

    formatPercent(value) {
        return (parseFloat(value) || 0).toFixed(1) + '%';
    },

    formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
    },

    updateTrend(elementId, change, isPercent = false) {
        const el = document.getElementById(elementId);
        if (!el) return;

        const isUp = change > 0;
        el.className = `hero-metric-trend ${isUp ? 'up' : 'down'}`;
        el.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="${isUp ? 'M7 17l5-5 5 5M7 7l5 5 5-5' : 'M7 7l5 5 5-5M7 17l5-5 5 5'}"/>
            </svg>
            <span>${isUp ? '+' : ''}${Math.abs(change).toFixed(1)}${isPercent ? ' pts' : '%'} vs anterior</span>
        `;
    },

    debounce(fn, delay) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn.apply(this, args), delay);
        };
    },

    toast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
        `;

        container.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }
};

// Initialize
document.addEventListener('DOMContentLoaded', () => App.init());
