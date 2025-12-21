/* ============================================
   G4U Finance Dashboard - API Module
   ============================================ */

const API = {
    baseUrl: '',

    // Generic fetch wrapper with error handling
    async request(endpoint, options = {}) {
        try {
            const response = await fetch(this.baseUrl + endpoint, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || data.message || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    },

    // GET request
    get(endpoint) {
        return this.request(endpoint);
    },

    // POST request
    post(endpoint, body) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    },

    // PUT request
    put(endpoint, body) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(body)
        });
    },

    // PATCH request
    patch(endpoint, body) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(body)
        });
    },

    // DELETE request
    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    },

    // ========== Dashboard ==========
    dashboard: {
        getData() {
            return API.get('/api/data');
        },

        getKPIs(startDate, endDate) {
            let url = '/api/v2/kpis/global';
            if (startDate || endDate) {
                const params = new URLSearchParams();
                if (startDate) params.append('start_date', startDate);
                if (endDate) params.append('end_date', endDate);
                url += '?' + params.toString();
            }
            return API.get(url);
        },

        getOverview() {
            return API.get('/api/v2/dashboard/overview');
        },

        getAlerts() {
            return API.get('/api/v2/alerts');
        }
    },

    // ========== Transactions ==========
    transactions: {
        getAll(filters = {}) {
            const params = new URLSearchParams();
            Object.entries(filters).forEach(([key, value]) => {
                if (value !== undefined && value !== '') {
                    params.append(key, value);
                }
            });
            const query = params.toString();
            return API.get('/api/v1/transactions' + (query ? '?' + query : ''));
        },

        get(id) {
            return API.get(`/api/v2/transactions/${id}`);
        },

        update(id, data) {
            return API.put(`/api/transaction/${id}`, data);
        },

        bulkUpdate(ids, data) {
            return API.post('/api/v1/transactions/bulk/assign-project', {
                transaction_ids: ids,
                ...data
            });
        },

        getAllocations(txId) {
            return API.get(`/api/v2/transactions/${txId}/allocations`);
        },

        setAllocations(txId, allocations) {
            return API.post(`/api/v2/transactions/${txId}/allocations`, { allocations });
        },

        // Get pending review transactions
        getPendingReview() {
            return API.get('/api/v1/transactions').then(data => {
                const transactions = data.transactions || [];
                // Filter unassigned or partially assigned
                return transactions.filter(tx => {
                    const hasProject = tx.project_id || tx.project;
                    const hasClient = tx.client_id || tx.client;
                    return !hasProject && !hasClient;
                });
            });
        }
    },

    // ========== Projects ==========
    projects: {
        getAll() {
            return API.get('/api/v1/projects');
        },

        getSummary() {
            return API.get('/api/v2/projects/summary');
        },

        get(id) {
            return API.get(`/api/v2/projects/${id}`);
        },

        create(data) {
            return API.post('/api/project', data);
        },

        update(id, data) {
            return API.put(`/api/project/${id}`, data);
        },

        delete(id) {
            return API.delete(`/api/project/${id}`);
        },

        getTransactions(projectId) {
            return API.get(`/api/v2/projects/${projectId}/transactions`);
        },

        getKPIs() {
            return API.get('/api/v2/kpis/projects');
        }
    },

    // ========== Clients ==========
    clients: {
        getAll() {
            return API.get('/api/clients');
        },

        getSummary() {
            return API.get('/api/v2/projects/clients/summary');
        },

        get(name) {
            return API.get(`/api/v2/clients/${encodeURIComponent(name)}/projects`);
        },

        create(data) {
            return API.post('/api/client', data);
        },

        update(id, data) {
            return API.put(`/api/client/${id}`, data);
        },

        delete(id) {
            return API.delete(`/api/client/${id}`);
        },

        getTransactions(name) {
            return API.get(`/api/v2/clients/${encodeURIComponent(name)}/transactions`);
        }
    },

    // ========== Categories ==========
    categories: {
        getAll() {
            return API.get('/api/v1/categories');
        },

        create(data) {
            return API.post('/api/category', data);
        },

        update(id, data) {
            return API.put(`/api/category/${id}`, data);
        },

        delete(id) {
            return API.delete(`/api/category/${id}`);
        }
    },

    // ========== Team Members ==========
    team: {
        getAll() {
            return API.get('/api/team-members');
        },

        create(data) {
            return API.post('/api/team-member', data);
        },

        update(id, data) {
            return API.put(`/api/team-member/${id}`, data);
        },

        delete(id) {
            return API.delete(`/api/team-member/${id}`);
        }
    },

    // ========== Salary Allocations ==========
    salaryAllocations: {
        getByMonth(month) {
            return API.get(`/api/salary-allocations?month=${month}`);
        },

        create(data) {
            return API.post('/api/salary-allocation', data);
        },

        delete(id) {
            return API.delete(`/api/salary-allocation/${id}`);
        }
    },

    // ========== Transaction Allocations ==========
    transactionAllocations: {
        getAll() {
            return API.get('/api/transaction-allocations');
        },

        create(data) {
            return API.post('/api/transaction-allocation', data);
        },

        delete(id) {
            return API.delete(`/api/transaction-allocation/${id}`);
        }
    },

    // ========== Reports ==========
    reports: {
        getPL(period = 'all') {
            return API.get(`/api/v1/reports/pl?period=${period}`);
        },

        getPLMonthly(year, month) {
            return API.get(`/api/v1/reports/pl/monthly?year=${year}&month=${month}`);
        },

        exportPDF() {
            // Trigger PDF download
            window.open('/api/v2/reports/pl/export/pdf', '_blank');
        },

        exportCSV() {
            window.open('/api/v2/reports/pl/export/csv', '_blank');
        }
    },

    // ========== Sync ==========
    sync: {
        all() {
            return API.post('/api/v1/sync/all');
        },

        transactions() {
            return API.post('/api/v1/sync/transactions');
        },

        checkStatus() {
            return API.get('/api/status');
        },

        importQontoMembers() {
            return API.post('/api/qonto/sync-members');
        },

        getQontoOrganization() {
            return API.get('/api/qonto/organization');
        }
    },

    // ========== AI Suggestions ==========
    suggestions: {
        getForTransaction(txId) {
            return API.get(`/api/v2/transactions/${txId}/suggestions`);
        },

        applyRule(ruleId, txId) {
            return API.post(`/api/v2/assignment-rules/${ruleId}/apply`, { transaction_id: txId });
        }
    }
};

// Export
window.API = API;
