import { useState, useMemo, useCallback } from 'react';
import { useData } from './hooks/useApi';
import { isIncome } from './utils/format';

import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import Profitability from './components/Profitability';
import Transactions from './components/Transactions';
import Review from './components/Review';
import Simulator from './components/Simulator';
import Settings from './components/Settings';
import Toast from './components/Toast';

import './index.css';

export default function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [period, setPeriod] = useState('month');
  const [toasts, setToasts] = useState([]);
  const [modal, setModal] = useState(null);

  // Fetch data with auto-refresh
  const { data, loading, error, lastSync, refresh } = useData(30000);

  // Filter transactions by period
  const filteredTransactions = useMemo(() => {
    const days = { week: 7, month: 30, quarter: 90, year: 365 }[period] || 30;
    const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000);

    return data.transactions.filter(t => {
      const txDate = new Date(t.settled_at || t.emitted_at);
      return txDate >= cutoff;
    });
  }, [data.transactions, period]);

  // Pending count
  const pendingCount = useMemo(() => {
    return data.transactions.filter(t =>
      !t.project && !t.project_id && !t.client && !t.client_id && !t.excluded
    ).length;
  }, [data.transactions]);

  // Toast helper
  const showToast = useCallback((message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  // Navigation
  const handleNavigate = useCallback((view) => {
    setCurrentView(view);
  }, []);

  // Sync
  const handleSync = useCallback(async () => {
    showToast('Sincronizando...', 'info');
    await refresh();
    showToast('Datos actualizados', 'success');
  }, [refresh, showToast]);

  // Modal handlers
  const openModal = useCallback((name) => setModal(name), []);
  const closeModal = useCallback(() => setModal(null), []);

  // Assignment handler
  const handleAssign = useCallback((tx) => {
    // For now, navigate to review
    setCurrentView('review');
  }, []);

  // Loading state
  if (loading && data.transactions.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-600">Cargando datos...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && data.transactions.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Error al cargar datos</h2>
          <p className="text-slate-600 mb-4">{error}</p>
          <button
            onClick={refresh}
            className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <Layout
        currentView={currentView}
        onNavigate={handleNavigate}
        pendingCount={pendingCount}
        lastSync={lastSync}
        onSync={handleSync}
        period={period}
        onPeriodChange={setPeriod}
      >
        {currentView === 'dashboard' && (
          <Dashboard
            transactions={filteredTransactions}
            projects={data.projects}
            clients={data.clients}
            onNavigate={handleNavigate}
          />
        )}

        {currentView === 'profitability' && (
          <Profitability
            transactions={filteredTransactions}
            projects={data.projects}
            clients={data.clients}
          />
        )}

        {currentView === 'transactions' && (
          <Transactions
            transactions={filteredTransactions}
            projects={data.projects}
            clients={data.clients}
            categories={data.categories}
            onAssign={handleAssign}
          />
        )}

        {currentView === 'review' && (
          <Review
            transactions={data.transactions}
            projects={data.projects}
            clients={data.clients}
            onRefresh={refresh}
            showToast={showToast}
          />
        )}

        {currentView === 'simulator' && (
          <Simulator
            projects={data.projects}
            showToast={showToast}
          />
        )}

        {currentView === 'settings' && (
          <Settings
            clients={data.clients}
            projects={data.projects}
            teamMembers={data.teamMembers}
            categories={data.categories}
            onRefresh={refresh}
            showToast={showToast}
            onOpenModal={openModal}
          />
        )}
      </Layout>

      {/* Toasts */}
      <Toast toasts={toasts} onRemove={removeToast} />

      {/* Modals would go here */}
    </>
  );
}
