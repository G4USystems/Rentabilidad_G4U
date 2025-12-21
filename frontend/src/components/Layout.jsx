import { useState } from 'react';
import { formatRelativeTime } from '../utils/format';

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: DashboardIcon },
  { id: 'profitability', label: 'Rentabilidad', icon: ProfitIcon },
  { id: 'transactions', label: 'Transacciones', icon: TransactionsIcon },
  { id: 'review', label: 'Revision', icon: ReviewIcon, badge: true },
  { id: 'simulator', label: 'Simulador IA', icon: AIIcon },
  { id: 'settings', label: 'Config', icon: SettingsIcon, bottom: true },
];

export default function Layout({
  children,
  currentView,
  onNavigate,
  pendingCount = 0,
  lastSync,
  onSync,
  period,
  onPeriodChange
}) {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-slate-200 fixed top-0 left-0 h-full flex flex-col z-50">
        <div className="h-16 flex items-center justify-center border-b border-slate-200">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
            G4U
          </div>
        </div>

        <nav className="flex-1 p-3 flex flex-col gap-1">
          {navItems.filter(i => !i.bottom).map(item => (
            <NavLink
              key={item.id}
              item={item}
              active={currentView === item.id}
              badge={item.badge ? pendingCount : null}
              onClick={() => onNavigate(item.id)}
            />
          ))}
        </nav>

        <div className="p-3 border-t border-slate-200">
          {navItems.filter(i => i.bottom).map(item => (
            <NavLink
              key={item.id}
              item={item}
              active={currentView === item.id}
              onClick={() => onNavigate(item.id)}
            />
          ))}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-56 min-h-screen flex flex-col">
        {/* Top Bar */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 sticky top-0 z-40">
          <div className="flex items-center gap-6">
            <h1 className="text-lg font-semibold text-slate-900">
              {getPageTitle(currentView)}
            </h1>
            {lastSync && (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                <span>Actualizado {formatRelativeTime(lastSync)}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4">
            {/* Period Selector */}
            <div className="flex bg-slate-100 rounded-lg p-1">
              {['week', 'month', 'quarter', 'year'].map(p => (
                <button
                  key={p}
                  onClick={() => onPeriodChange(p)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                    period === p
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {p === 'week' ? '7D' : p === 'month' ? '30D' : p === 'quarter' ? '90D' : '1A'}
                </button>
              ))}
            </div>

            {/* Sync Button */}
            <button
              onClick={onSync}
              className="w-9 h-9 flex items-center justify-center border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors"
              title="Sincronizar"
            >
              <SyncIcon className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 p-6 overflow-auto">
          {children}
        </div>
      </main>
    </div>
  );
}

function NavLink({ item, active, badge, onClick }) {
  const Icon = item.icon;

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-sm font-medium transition-all relative ${
        active
          ? 'bg-blue-50 text-blue-600'
          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
      }`}
    >
      {active && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-blue-600 rounded-r" />
      )}
      <Icon className="w-5 h-5" />
      <span>{item.label}</span>
      {badge > 0 && (
        <span className="ml-auto bg-red-500 text-white text-xs font-semibold px-2 py-0.5 rounded-full">
          {badge}
        </span>
      )}
    </button>
  );
}

function getPageTitle(view) {
  const titles = {
    dashboard: 'Dashboard Ejecutivo',
    profitability: 'Rentabilidad',
    transactions: 'Transacciones',
    review: 'Revision',
    simulator: 'Simulador IA',
    settings: 'Configuracion',
  };
  return titles[view] || view;
}

// Icons
function DashboardIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
  );
}

function ProfitIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
    </svg>
  );
}

function TransactionsIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 3v18h18"/>
      <path d="M7 16l4-4 4 4 5-6"/>
    </svg>
  );
}

function ReviewIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 11l3 3L22 4"/>
      <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
    </svg>
  );
}

function AIIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2a4 4 0 014 4c0 1.1-.9 2-2 2h-4a2 2 0 01-2-2 4 4 0 014-4z"/>
      <path d="M12 8v8M8 12h8"/>
      <circle cx="12" cy="19" r="2"/>
    </svg>
  );
}

function SettingsIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3"/>
      <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
    </svg>
  );
}

function SyncIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M23 4v6h-6M1 20v-6h6"/>
      <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
    </svg>
  );
}
