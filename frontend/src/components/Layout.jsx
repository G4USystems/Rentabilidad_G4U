import { formatRelativeTime } from '../utils/format';

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: DashboardIcon },
  { id: 'profitability', label: 'Rentabilidad', icon: ProfitIcon },
  { id: 'transactions', label: 'Transacciones', icon: TransactionsIcon },
  { id: 'review', label: 'Revision', icon: ReviewIcon, badge: true },
  { id: 'simulator', label: 'Simulador IA', icon: AIIcon },
  { id: 'settings', label: 'Configuracion', icon: SettingsIcon, bottom: true },
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
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 fixed top-0 left-0 h-full flex flex-col z-50">
        {/* Logo */}
        <div className="h-20 flex items-center px-6 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-blue-600 rounded-xl flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-blue-500/30">
              G4U
            </div>
            <div>
              <p className="font-semibold text-white">Rentabilidad</p>
              <p className="text-xs text-slate-500">Financial Dashboard</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          <p className="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Menu</p>
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

        {/* Bottom Section */}
        <div className="p-4 border-t border-slate-800">
          {navItems.filter(i => i.bottom).map(item => (
            <NavLink
              key={item.id}
              item={item}
              active={currentView === item.id}
              onClick={() => onNavigate(item.id)}
            />
          ))}

          {/* Sync Status */}
          {lastSync && (
            <div className="mt-4 px-3 py-2 bg-slate-800/50 rounded-lg">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
                <span className="text-xs text-slate-400">
                  Sincronizado {formatRelativeTime(lastSync)}
                </span>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64 min-h-screen flex flex-col">
        {/* Top Bar */}
        <header className="h-20 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-40 shadow-sm">
          <div className="flex items-center gap-6">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">
                {getPageTitle(currentView)}
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">
                {getPageSubtitle(currentView)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Period Selector */}
            <div className="flex bg-slate-100 rounded-xl p-1">
              {['week', 'month', 'quarter', 'year'].map(p => (
                <button
                  key={p}
                  onClick={() => onPeriodChange(p)}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                    period === p
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {p === 'week' ? '7 dias' : p === 'month' ? '30 dias' : p === 'quarter' ? '90 dias' : '1 ano'}
                </button>
              ))}
            </div>

            {/* Sync Button */}
            <button
              onClick={onSync}
              className="flex items-center gap-2 px-4 py-2.5 bg-slate-900 text-white text-sm font-medium rounded-xl hover:bg-slate-800 transition-colors shadow-lg shadow-slate-900/20"
              title="Sincronizar"
            >
              <SyncIcon className="w-4 h-4" />
              <span>Sincronizar</span>
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 p-8 overflow-auto">
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
      className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-left text-sm font-medium transition-all duration-200 relative group ${
        active
          ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
          : 'text-slate-400 hover:bg-slate-800 hover:text-white'
      }`}
    >
      <Icon className="w-5 h-5" />
      <span>{item.label}</span>
      {badge > 0 && (
        <span className={`ml-auto text-xs font-bold px-2 py-0.5 rounded-full ${
          active ? 'bg-white/20 text-white' : 'bg-red-500 text-white'
        }`}>
          {badge}
        </span>
      )}
    </button>
  );
}

function getPageTitle(view) {
  const titles = {
    dashboard: 'Dashboard Ejecutivo',
    profitability: 'Analisis de Rentabilidad',
    transactions: 'Transacciones',
    review: 'Bandeja de Revision',
    simulator: 'Simulador IA',
    settings: 'Configuracion',
  };
  return titles[view] || view;
}

function getPageSubtitle(view) {
  const subtitles = {
    dashboard: 'Vista general de metricas financieras',
    profitability: 'Rentabilidad por cliente y proyecto',
    transactions: 'Historial de movimientos',
    review: 'Asignar transacciones a proyectos',
    simulator: 'Proyecciones y escenarios',
    settings: 'Gestionar tu cuenta',
  };
  return subtitles[view] || '';
}

// Icons
function DashboardIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="7" rx="2"/>
      <rect x="14" y="3" width="7" height="7" rx="2"/>
      <rect x="3" y="14" width="7" height="7" rx="2"/>
      <rect x="14" y="14" width="7" height="7" rx="2"/>
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
      <circle cx="12" cy="12" r="10"/>
      <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/>
      <path d="M12 17h.01"/>
    </svg>
  );
}

function SettingsIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
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
