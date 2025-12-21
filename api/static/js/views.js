/* ============================================
   G4U Finance Dashboard - Views Module
   Render functions for each view
   ============================================ */

// Extend App with view-specific methods
Object.assign(App, {

    // ========== CLIENTS VIEW ==========
    renderClients(params = {}) {
        const transactions = this.getFilteredTransactions();

        // Group transactions by client
        const clientData = {};
        transactions.forEach(tx => {
            const client = tx.client || tx.client_id;
            if (!client) return;

            if (!clientData[client]) {
                const clientInfo = this.state.clients.find(c => c.id === client || c.name === client);
                clientData[client] = {
                    name: clientInfo?.name || client,
                    id: clientInfo?.id || client,
                    income: 0,
                    expenses: 0,
                    projects: new Set(),
                    transactions: []
                };
            }

            const amount = parseFloat(tx.amount) || 0;
            if (amount > 0 || tx.side === 'credit') {
                clientData[client].income += Math.abs(amount);
            } else {
                clientData[client].expenses += Math.abs(amount);
            }

            if (tx.project_id || tx.project) {
                clientData[client].projects.add(tx.project_id || tx.project);
            }
            clientData[client].transactions.push(tx);
        });

        // Convert to array
        const clients = Object.values(clientData).map(c => ({
            ...c,
            projectCount: c.projects.size,
            net: c.income - c.expenses,
            margin: c.income > 0 ? ((c.income - c.expenses) / c.income) * 100 : 0
        })).sort((a, b) => b.income - a.income);

        // Update KPIs
        const totalClients = this.state.clients.length;
        const totalIncome = clients.reduce((sum, c) => sum + c.income, 0);
        const avgMargin = clients.length > 0
            ? clients.reduce((sum, c) => sum + c.margin, 0) / clients.length
            : 0;

        document.getElementById('clients-count').textContent = totalClients;
        document.getElementById('clients-income').textContent = Utils.formatCurrency(totalIncome, { compact: true });
        document.getElementById('clients-margin').textContent = Utils.formatPercent(avgMargin);

        // Render table
        const tbody = document.getElementById('clients-table-body');
        if (!tbody) return;

        if (clients.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-muted" style="text-align:center;padding:40px;">No hay datos de clientes</td></tr>';
            return;
        }

        tbody.innerHTML = clients.map(client => {
            const monthlyData = Charts.getMonthlyTrend(client.transactions, 6);
            const sparkline = Charts.sparkline(monthlyData.map(d => d.income), { width: 80, height: 24 });

            return `
                <tr onclick="App.showClientDetail('${client.id}')" style="cursor:pointer;">
                    <td>
                        <div style="font-weight:500;">${client.name}</div>
                    </td>
                    <td>${client.projectCount}</td>
                    <td style="text-align:right;">
                        <span class="amount positive">${Utils.formatCurrency(client.income, { compact: true })}</span>
                    </td>
                    <td style="text-align:right;">
                        <span class="amount negative">${Utils.formatCurrency(client.expenses, { compact: true })}</span>
                    </td>
                    <td style="text-align:right;">
                        <span class="${client.margin >= 20 ? 'amount positive' : client.margin >= 0 ? '' : 'amount negative'}">
                            ${Utils.formatPercent(client.margin)}
                        </span>
                    </td>
                    <td>${sparkline}</td>
                    <td>
                        <button class="btn btn-ghost btn-sm btn-icon" onclick="event.stopPropagation(); App.editClient('${client.id}')">
                            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    },

    showClientDetail(clientId) {
        // Navigate to client detail with breadcrumbs
        const client = this.state.clients.find(c => c.id === clientId || c.name === clientId);
        if (!client) return;

        // Update breadcrumbs
        document.getElementById('clients-breadcrumbs').innerHTML = `
            <a href="#" onclick="App.renderClients(); return false;">Clientes</a>
            <span class="separator">/</span>
            <span class="current">${client.name}</span>
        `;

        document.getElementById('clients-title').textContent = client.name;

        // Get client projects
        const projects = this.state.projects.filter(p => p.client === client.name);

        // Get client transactions
        const transactions = this.state.transactions.filter(tx =>
            tx.client === client.name || tx.client_id === clientId
        );

        // Render detail view...
        // (Implementation would show projects, transactions, KPIs for this client)
    },

    filterClients() {
        const search = document.getElementById('client-search')?.value.toLowerCase() || '';
        // Apply filters and re-render
        this.renderClients();
    },

    // ========== PROJECTS VIEW ==========
    renderProjects(params = {}) {
        const transactions = this.getFilteredTransactions();

        // Populate client filter
        const clientSelect = document.getElementById('project-filter-client');
        if (clientSelect && clientSelect.options.length <= 1) {
            this.state.clients.forEach(c => {
                clientSelect.appendChild(new Option(c.name, c.name));
            });
        }

        // Group transactions by project
        const projectData = {};
        transactions.forEach(tx => {
            const projectId = tx.project_id || tx.project;
            if (!projectId) return;

            if (!projectData[projectId]) {
                const project = this.state.projects.find(p => p.id === projectId || p.name === projectId);
                projectData[projectId] = {
                    id: project?.id || projectId,
                    name: project?.name || projectId,
                    client: project?.client || '',
                    status: project?.status || 'Active',
                    income: 0,
                    expenses: 0,
                    transactions: []
                };
            }

            const amount = parseFloat(tx.amount) || 0;
            if (amount > 0 || tx.side === 'credit') {
                projectData[projectId].income += Math.abs(amount);
            } else {
                projectData[projectId].expenses += Math.abs(amount);
            }
            projectData[projectId].transactions.push(tx);
        });

        // Add projects without transactions
        this.state.projects.forEach(p => {
            if (!projectData[p.id] && !projectData[p.name]) {
                projectData[p.id || p.name] = {
                    id: p.id,
                    name: p.name,
                    client: p.client || '',
                    status: p.status || 'Active',
                    income: 0,
                    expenses: 0,
                    transactions: []
                };
            }
        });

        // Apply filters
        let projects = Object.values(projectData);
        const clientFilter = document.getElementById('project-filter-client')?.value;
        const statusFilter = document.getElementById('project-filter-status')?.value;
        const searchFilter = document.getElementById('project-search')?.value.toLowerCase();

        if (clientFilter) {
            projects = projects.filter(p => p.client === clientFilter);
        }
        if (statusFilter) {
            projects = projects.filter(p => p.status === statusFilter);
        }
        if (searchFilter) {
            projects = projects.filter(p => p.name.toLowerCase().includes(searchFilter));
        }

        // Calculate margin and sort
        projects = projects.map(p => ({
            ...p,
            net: p.income - p.expenses,
            margin: p.income > 0 ? ((p.income - p.expenses) / p.income) * 100 : 0
        })).sort((a, b) => b.income - a.income);

        // Update KPIs
        const activeCount = projects.filter(p => p.status === 'Active').length;
        const totalIncome = projects.reduce((sum, p) => sum + p.income, 0);
        const totalExpenses = projects.reduce((sum, p) => sum + p.expenses, 0);
        const avgMargin = projects.length > 0
            ? projects.reduce((sum, p) => sum + p.margin, 0) / projects.length
            : 0;

        document.getElementById('projects-active').textContent = activeCount;
        document.getElementById('projects-income').textContent = Utils.formatCurrency(totalIncome, { compact: true });
        document.getElementById('projects-expenses').textContent = Utils.formatCurrency(totalExpenses, { compact: true });
        document.getElementById('projects-margin').textContent = Utils.formatPercent(avgMargin);

        // Render project grid
        const container = document.getElementById('projects-grid');
        if (!container) return;

        if (projects.length === 0) {
            container.innerHTML = '<div class="text-muted" style="padding:40px;text-align:center;">No hay proyectos</div>';
            return;
        }

        container.innerHTML = projects.map(project => {
            const statusClass = project.status === 'Active' ? 'success' :
                               project.status === 'Completed' ? 'info' : 'warning';
            const statusLabel = project.status === 'Active' ? 'Activo' :
                               project.status === 'Completed' ? 'Completado' : 'En Pausa';

            const marginClass = project.margin >= 20 ? 'positive' :
                               project.margin >= 0 ? '' : 'negative';

            const barWidth = Math.min(Math.abs(project.margin), 100);
            const barClass = project.margin >= 0 ? 'positive' : 'negative';

            return `
                <div class="project-card" onclick="App.showProjectDetail('${project.id}')">
                    <div class="project-card-header">
                        <div>
                            <div class="project-name">${project.name}</div>
                            <div class="project-client">${project.client || 'Sin cliente'}</div>
                        </div>
                        <span class="status ${statusClass}">${statusLabel}</span>
                    </div>
                    <div class="project-stats">
                        <div class="project-stat">
                            <div class="project-stat-label">Ingresos</div>
                            <div class="project-stat-value positive">${Utils.formatCurrency(project.income, { compact: true })}</div>
                        </div>
                        <div class="project-stat">
                            <div class="project-stat-label">Gastos</div>
                            <div class="project-stat-value negative">${Utils.formatCurrency(project.expenses, { compact: true })}</div>
                        </div>
                        <div class="project-stat">
                            <div class="project-stat-label">Resultado</div>
                            <div class="project-stat-value ${marginClass}">${Utils.formatCurrency(project.net, { compact: true })}</div>
                        </div>
                        <div class="project-stat">
                            <div class="project-stat-label">Margen</div>
                            <div class="project-stat-value ${marginClass}">${Utils.formatPercent(project.margin)}</div>
                        </div>
                    </div>
                    <div class="project-bar">
                        <div class="project-bar-fill ${barClass}" style="width: ${barWidth}%"></div>
                    </div>
                </div>
            `;
        }).join('');
    },

    showProjectDetail(projectId) {
        // Navigate to project detail
        console.log('Show project detail:', projectId);
        // Implementation similar to showClientDetail
    },

    filterProjects() {
        this.renderProjects();
    },

    // ========== TRANSACTIONS VIEW ==========
    renderTransactions() {
        const transactions = this.getFilteredTransactions();

        // Populate filter dropdowns if empty
        this.populateTransactionFilters();

        const tbody = document.getElementById('transactions-table-body');
        if (!tbody) return;

        if (transactions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-muted" style="text-align:center;padding:40px;">No hay transacciones</td></tr>';
            return;
        }

        tbody.innerHTML = transactions.slice(0, 100).map(tx => {
            const amount = parseFloat(tx.amount) || 0;
            const isIncome = amount > 0 || tx.side === 'credit';
            const isSelected = this.state.selectedTransactions.includes(tx.id);

            const project = tx.project_id || tx.project;
            const client = tx.client_id || tx.client;
            const assignmentText = project || client || '-';
            const assignmentClass = (project || client) ? '' : 'text-muted';

            return `
                <tr class="${isSelected ? 'selected' : ''}">
                    <td>
                        <input type="checkbox" class="table-checkbox"
                               ${isSelected ? 'checked' : ''}
                               onchange="App.toggleTransactionSelection('${tx.id}')">
                    </td>
                    <td>${Utils.formatDate(tx.settled_at || tx.emitted_at)}</td>
                    <td>
                        <div style="font-weight:500;">${tx.counterparty_name || tx.label || '-'}</div>
                        <div class="text-muted text-xs">${tx.note || ''}</div>
                    </td>
                    <td>${tx.category || tx.qonto_category || '-'}</td>
                    <td class="${assignmentClass}">${assignmentText}</td>
                    <td style="text-align:right;">
                        <span class="amount ${isIncome ? 'positive' : 'negative'}">
                            ${isIncome ? '+' : ''}${Utils.formatCurrency(amount)}
                        </span>
                    </td>
                    <td>
                        <div class="table-actions">
                            <button class="btn btn-ghost btn-sm btn-icon" onclick="App.openTxAssignment('${tx.id}')" data-tooltip="Asignar">
                                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/></svg>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        // Update sort indicators
        document.querySelectorAll('th .sort-icon').forEach(el => {
            const field = el.id.replace('sort-', '');
            if (field === this.state.sortField) {
                el.textContent = this.state.sortDirection === 'desc' ? '↓' : '↑';
                el.parentElement.classList.add('sorted');
            } else {
                el.textContent = '';
                el.parentElement.classList.remove('sorted');
            }
        });
    },

    populateTransactionFilters() {
        // Categories
        const catSelect = document.getElementById('tx-filter-category');
        if (catSelect && catSelect.options.length <= 1) {
            const categories = [...new Set(this.state.transactions.map(tx => tx.category || tx.qonto_category).filter(Boolean))];
            categories.sort().forEach(c => {
                catSelect.appendChild(new Option(c, c));
            });
        }

        // Projects
        const projSelect = document.getElementById('tx-filter-project');
        if (projSelect && projSelect.options.length <= 1) {
            this.state.projects.forEach(p => {
                projSelect.appendChild(new Option(p.name, p.id || p.name));
            });
        }

        // Clients
        const clientSelect = document.getElementById('tx-filter-client');
        if (clientSelect && clientSelect.options.length <= 1) {
            this.state.clients.forEach(c => {
                clientSelect.appendChild(new Option(c.name, c.id || c.name));
            });
        }
    },

    applyTransactionFilters() {
        this.state.filters.type = document.getElementById('tx-filter-type')?.value || '';
        this.state.filters.category = document.getElementById('tx-filter-category')?.value || '';
        this.state.filters.project = document.getElementById('tx-filter-project')?.value || '';
        this.state.filters.client = document.getElementById('tx-filter-client')?.value || '';
        this.state.filters.dateFrom = document.getElementById('tx-filter-from')?.value || '';
        this.state.filters.dateTo = document.getElementById('tx-filter-to')?.value || '';
        this.state.filters.search = document.getElementById('tx-search')?.value || '';

        this.renderTransactions();
    },

    clearTransactionFilters() {
        document.getElementById('tx-filter-type').value = '';
        document.getElementById('tx-filter-category').value = '';
        document.getElementById('tx-filter-project').value = '';
        document.getElementById('tx-filter-client').value = '';
        document.getElementById('tx-filter-from').value = '';
        document.getElementById('tx-filter-to').value = '';
        document.getElementById('tx-search').value = '';

        document.querySelectorAll('.quick-filter').forEach(btn => btn.classList.remove('active'));

        this.state.filters = {
            type: '', category: '', project: '', client: '',
            assigned: '', search: '', dateFrom: '', dateTo: ''
        };

        this.renderTransactions();
    },

    toggleQuickFilter(filter) {
        const btn = document.querySelector(`.quick-filter[data-filter="${filter}"]`);
        const isActive = btn?.classList.contains('active');

        document.querySelectorAll('.quick-filter').forEach(b => b.classList.remove('active'));

        if (!isActive) {
            btn?.classList.add('active');
            this.state.filters.assigned = filter === 'assigned' ? 'assigned' :
                                          filter === 'unassigned' ? 'unassigned' : '';
        } else {
            this.state.filters.assigned = '';
        }

        this.renderTransactions();
    },

    sortTransactions(field) {
        if (this.state.sortField === field) {
            this.state.sortDirection = this.state.sortDirection === 'desc' ? 'asc' : 'desc';
        } else {
            this.state.sortField = field;
            this.state.sortDirection = 'desc';
        }
        this.renderTransactions();
    },

    toggleTransactionSelection(txId) {
        const idx = this.state.selectedTransactions.indexOf(txId);
        if (idx >= 0) {
            this.state.selectedTransactions.splice(idx, 1);
        } else {
            this.state.selectedTransactions.push(txId);
        }
        this.updateBulkActionsBar();
        this.renderTransactions();
    },

    toggleAllTransactions() {
        const checkbox = document.getElementById('select-all-tx');
        const transactions = this.getFilteredTransactions().slice(0, 100);

        if (checkbox.checked) {
            this.state.selectedTransactions = transactions.map(tx => tx.id);
        } else {
            this.state.selectedTransactions = [];
        }

        this.updateBulkActionsBar();
        this.renderTransactions();
    },

    updateBulkActionsBar() {
        const bar = document.getElementById('bulk-actions-bar');
        const count = this.state.selectedTransactions.length;

        if (count > 0) {
            bar?.classList.remove('hidden');
            document.getElementById('selected-count').textContent = count;
        } else {
            bar?.classList.add('hidden');
        }
    },

    clearSelection() {
        this.state.selectedTransactions = [];
        document.getElementById('select-all-tx').checked = false;
        this.updateBulkActionsBar();
        this.renderTransactions();
    },

    // ========== REVIEW VIEW ==========
    renderReview() {
        // Get pending review transactions
        const pending = this.state.transactions.filter(tx => {
            const hasProject = tx.project_id || tx.project;
            const hasClient = tx.client_id || tx.client;
            return !hasProject && !hasClient;
        });

        // Update count
        document.getElementById('review-count').textContent = `${pending.length} pendientes`;

        // Render list
        const list = document.getElementById('review-list');
        if (!list) return;

        if (pending.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <h4>Todo revisado</h4>
                    <p>No hay transacciones pendientes de asignar</p>
                </div>
            `;
            return;
        }

        list.innerHTML = pending.map(tx => {
            const amount = parseFloat(tx.amount) || 0;
            const isIncome = amount > 0 || tx.side === 'credit';

            return `
                <div class="review-item" data-tx-id="${tx.id}" onclick="App.selectReviewItem('${tx.id}')">
                    <input type="checkbox" class="review-item-checkbox" onclick="event.stopPropagation()">
                    <div class="review-item-content">
                        <div class="review-item-title">${tx.counterparty_name || tx.label || 'Sin descripcion'}</div>
                        <div class="review-item-meta">
                            <span>${Utils.formatDate(tx.settled_at || tx.emitted_at)}</span>
                            <span>${tx.qonto_category || '-'}</span>
                        </div>
                    </div>
                    <div class="review-item-amount ${isIncome ? 'positive' : 'negative'}">
                        ${isIncome ? '+' : ''}${Utils.formatCurrency(amount)}
                    </div>
                </div>
            `;
        }).join('');
    },

    selectReviewItem(txId) {
        // Update selection UI
        document.querySelectorAll('.review-item').forEach(item => {
            item.classList.toggle('selected', item.dataset.txId === txId);
        });

        // Get transaction details
        const tx = this.state.transactions.find(t => t.id === txId);
        if (!tx) return;

        // Update panel
        document.getElementById('review-panel-title').textContent = tx.counterparty_name || tx.label || 'Transaccion';
        document.getElementById('review-panel-subtitle').textContent = Utils.formatCurrency(parseFloat(tx.amount) || 0);

        // Render assignment form
        const body = document.getElementById('review-panel-body');
        body.innerHTML = `
            <div class="form-group">
                <label>Categoria</label>
                <select id="review-category">
                    <option value="">Sin categoria</option>
                    ${this.state.categories.map(c => `<option value="${c.name}">${c.name}</option>`).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>Proyecto</label>
                <select id="review-project">
                    <option value="">Sin proyecto</option>
                    ${this.state.projects.map(p => `<option value="${p.id || p.name}">${p.name}</option>`).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>Cliente</label>
                <select id="review-client">
                    <option value="">Sin cliente</option>
                    ${this.state.clients.map(c => `<option value="${c.id || c.name}">${c.name}</option>`).join('')}
                </select>
            </div>
        `;

        // Show footer
        document.getElementById('review-panel-footer').style.display = 'flex';

        // Store current tx id
        this._currentReviewTx = txId;
    },

    async confirmAssignment() {
        const txId = this._currentReviewTx;
        if (!txId) return;

        const category = document.getElementById('review-category')?.value;
        const project = document.getElementById('review-project')?.value;
        const client = document.getElementById('review-client')?.value;

        if (!project && !client) {
            this.showNotification('Selecciona al menos un proyecto o cliente', 'warning');
            return;
        }

        try {
            await API.transactions.update(txId, {
                category: category || undefined,
                project_id: project || undefined,
                client_id: client || undefined
            });

            // Update local state
            const tx = this.state.transactions.find(t => t.id === txId);
            if (tx) {
                if (category) tx.category = category;
                if (project) tx.project_id = project;
                if (client) tx.client_id = client;
            }

            this.showNotification('Transaccion asignada correctamente', 'success');
            this.renderReview();
            this.updatePendingCount();

        } catch (error) {
            this.showNotification('Error al asignar: ' + error.message, 'error');
        }
    },

    async excludeTransaction() {
        const txId = this._currentReviewTx;
        if (!txId) return;

        try {
            await API.transactions.update(txId, { excluded: true });
            this.showNotification('Transaccion excluida', 'success');
            this.renderReview();
        } catch (error) {
            this.showNotification('Error: ' + error.message, 'error');
        }
    },

    // ========== SETTINGS VIEW ==========
    renderSettings() {
        this.renderTeamMembers();
        this.renderClientsSettings();
        this.renderProjectsSettings();
        this.renderCategoriesSettings();
        this.initAllocationMonths();
    },

    showSettingsTab(tab, element) {
        // Update tab active state
        document.querySelectorAll('#view-settings .tab').forEach(t => t.classList.remove('active'));
        element?.classList.add('active');

        // Show/hide sections
        document.querySelectorAll('.settings-section').forEach(s => s.classList.add('hidden'));
        document.getElementById(`settings-${tab}`)?.classList.remove('hidden');
    },

    renderTeamMembers() {
        const tbody = document.getElementById('team-members-table');
        if (!tbody) return;

        if (this.state.teamMembers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-muted" style="text-align:center;padding:20px;">No hay miembros</td></tr>';
            return;
        }

        tbody.innerHTML = this.state.teamMembers.map(m => `
            <tr>
                <td>${m.name || '-'}</td>
                <td>${m.role || '-'}</td>
                <td style="text-align:right;" class="amount">${Utils.formatCurrency(m.salary || 0)}</td>
                <td>
                    <button class="btn btn-sm btn-ghost" onclick="App.editMember('${m.id}')">Editar</button>
                    <button class="btn btn-sm btn-ghost" onclick="App.deleteMember('${m.id}')" style="color:var(--danger);">X</button>
                </td>
            </tr>
        `).join('');
    },

    renderClientsSettings() {
        const tbody = document.getElementById('settings-clients-table');
        if (!tbody) return;

        if (this.state.clients.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-muted" style="text-align:center;padding:20px;">No hay clientes</td></tr>';
            return;
        }

        tbody.innerHTML = this.state.clients.map(c => `
            <tr>
                <td>${c.name || '-'}</td>
                <td>${c.contact || '-'}</td>
                <td>${c.email || '-'}</td>
                <td>${c.phone || '-'}</td>
                <td>
                    <button class="btn btn-sm btn-ghost" onclick="App.editClient('${c.id}')">Editar</button>
                    <button class="btn btn-sm btn-ghost" onclick="App.deleteClient('${c.id}')" style="color:var(--danger);">X</button>
                </td>
            </tr>
        `).join('');
    },

    renderProjectsSettings() {
        const tbody = document.getElementById('settings-projects-table');
        if (!tbody) return;

        if (this.state.projects.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-muted" style="text-align:center;padding:20px;">No hay proyectos</td></tr>';
            return;
        }

        const statusLabels = {
            'Active': 'Activo',
            'Completed': 'Completado',
            'On Hold': 'En Pausa'
        };

        tbody.innerHTML = this.state.projects.map(p => `
            <tr>
                <td>${p.name || '-'}</td>
                <td>${p.client || '-'}</td>
                <td><span class="status ${p.status === 'Active' ? 'success' : p.status === 'Completed' ? 'info' : 'warning'}">${statusLabels[p.status] || p.status}</span></td>
                <td>
                    <button class="btn btn-sm btn-ghost" onclick="App.editProject('${p.id}')">Editar</button>
                    <button class="btn btn-sm btn-ghost" onclick="App.deleteProject('${p.id}')" style="color:var(--danger);">X</button>
                </td>
            </tr>
        `).join('');
    },

    renderCategoriesSettings() {
        const tbody = document.getElementById('categories-table');
        if (!tbody) return;

        if (this.state.categories.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-muted" style="text-align:center;padding:20px;">No hay categorias</td></tr>';
            return;
        }

        tbody.innerHTML = this.state.categories.map(c => `
            <tr>
                <td>${c.name || '-'}</td>
                <td>${c.type === 'Income' ? 'Ingreso' : 'Gasto'}</td>
                <td>
                    <button class="btn btn-sm btn-ghost" onclick="App.editCategory('${c.id}')">Editar</button>
                    <button class="btn btn-sm btn-ghost" onclick="App.deleteCategory('${c.id}')" style="color:var(--danger);">X</button>
                </td>
            </tr>
        `).join('');
    },

    initAllocationMonths() {
        const select = document.getElementById('allocation-month');
        if (!select) return;

        const now = new Date();
        let html = '';

        for (let i = -6; i <= 6; i++) {
            const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
            const value = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
            const label = d.toLocaleString('es-ES', { month: 'long', year: 'numeric' });
            const selected = i === 0 ? ' selected' : '';
            html += `<option value="${value}"${selected}>${label.charAt(0).toUpperCase() + label.slice(1)}</option>`;
        }

        select.innerHTML = html;
    },

    // ========== CRUD Operations ==========
    async saveClient() {
        const data = {
            name: document.getElementById('new-client-name')?.value,
            contact: document.getElementById('new-client-contact')?.value,
            email: document.getElementById('new-client-email')?.value,
            phone: document.getElementById('new-client-phone')?.value,
            notes: document.getElementById('new-client-notes')?.value
        };

        if (!data.name) {
            this.showNotification('Ingresa un nombre', 'warning');
            return;
        }

        try {
            await API.clients.create(data);
            this.closeModal('add-client');
            await this.loadAllData();
            this.showNotification('Cliente creado', 'success');
        } catch (error) {
            this.showNotification('Error: ' + error.message, 'error');
        }
    },

    async saveProject() {
        const data = {
            name: document.getElementById('new-project-name')?.value,
            client: document.getElementById('new-project-client')?.value,
            status: document.getElementById('new-project-status')?.value
        };

        if (!data.name) {
            this.showNotification('Ingresa un nombre', 'warning');
            return;
        }

        try {
            await API.projects.create(data);
            this.closeModal('add-project');
            await this.loadAllData();
            this.showNotification('Proyecto creado', 'success');
        } catch (error) {
            this.showNotification('Error: ' + error.message, 'error');
        }
    },

    async saveTeamMember() {
        const data = {
            name: document.getElementById('new-member-name')?.value,
            role: document.getElementById('new-member-role')?.value,
            salary: parseFloat(document.getElementById('new-member-salary')?.value) || 0
        };

        if (!data.name) {
            this.showNotification('Ingresa un nombre', 'warning');
            return;
        }

        try {
            await API.team.create(data);
            this.closeModal('add-member');
            await this.loadAllData();
            this.showNotification('Miembro agregado', 'success');
        } catch (error) {
            this.showNotification('Error: ' + error.message, 'error');
        }
    },

    async saveCategory() {
        const data = {
            name: document.getElementById('new-category-name')?.value,
            type: document.getElementById('new-category-type')?.value
        };

        if (!data.name) {
            this.showNotification('Ingresa un nombre', 'warning');
            return;
        }

        try {
            await API.categories.create(data);
            this.closeModal('add-category');
            await this.loadAllData();
            this.showNotification('Categoria creada', 'success');
        } catch (error) {
            this.showNotification('Error: ' + error.message, 'error');
        }
    },

    // Transaction assignment modal
    openTxAssignment(txId) {
        const tx = this.state.transactions.find(t => t.id === txId);
        if (!tx) return;

        document.getElementById('tx-assignment-desc').textContent = tx.counterparty_name || tx.label || '-';
        document.getElementById('tx-assignment-amount').textContent = Utils.formatCurrency(parseFloat(tx.amount) || 0);

        // Populate selects
        const catSelect = document.getElementById('tx-alloc-category');
        catSelect.innerHTML = '<option value="">Sin categoria</option>' +
            this.state.categories.map(c => `<option value="${c.name}">${c.name}</option>`).join('');

        const projSelect = document.getElementById('tx-alloc-project');
        projSelect.innerHTML = '<option value="">Sin proyecto</option>' +
            this.state.projects.map(p => `<option value="${p.id || p.name}">${p.name}</option>`).join('');

        const clientSelect = document.getElementById('tx-alloc-client');
        clientSelect.innerHTML = '<option value="">Sin cliente</option>' +
            this.state.clients.map(c => `<option value="${c.id || c.name}">${c.name}</option>`).join('');

        this._currentAssignmentTx = txId;
        this.openModal('tx-assignment');
    },

    // ========== Sync functions ==========
    async syncQontoMembers() {
        try {
            const result = await API.sync.importQontoMembers();
            this.showNotification(`Miembros importados: ${result.created}`, 'success');
            await this.loadAllData();
        } catch (error) {
            this.showNotification('Error: ' + error.message, 'error');
        }
    },

    async loadQontoOrganization() {
        try {
            const data = await API.sync.getQontoOrganization();
            document.getElementById('qonto-org-name').textContent = data.legal_name || data.slug || '-';

            let balance = 0;
            if (data.bank_accounts?.length > 0) {
                balance = data.bank_accounts[0].balance || 0;
            }
            document.getElementById('qonto-balance').textContent = Utils.formatCurrency(balance);
            document.getElementById('qonto-org-info').classList.remove('hidden');
        } catch (error) {
            this.showNotification('Error: ' + error.message, 'error');
        }
    }
});

// Notification styles
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    .notification {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-lg);
        animation: slideIn 0.2s ease;
        max-width: 400px;
    }

    .notification-success { border-left: 4px solid var(--success); }
    .notification-error { border-left: 4px solid var(--danger); }
    .notification-warning { border-left: 4px solid var(--warning); }
    .notification-info { border-left: 4px solid var(--primary); }

    .notification button {
        background: none;
        border: none;
        font-size: 18px;
        color: var(--text-muted);
        cursor: pointer;
        padding: 0;
        margin-left: auto;
    }

    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(100%);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    .text-success { color: var(--success) !important; }
    .text-warning { color: var(--warning) !important; }
    .text-danger { color: var(--danger) !important; }
`;
document.head.appendChild(notificationStyles);
