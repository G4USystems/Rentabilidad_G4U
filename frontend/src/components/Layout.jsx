import { formatRelativeTime } from '../utils/format';

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: DashboardIcon },
  { id: 'profitability', label: 'Rentabilidad', icon: ProfitIcon },
  { id: 'transactions', label: 'Transacciones', icon: TransactionsIcon },
  { id: 'review', label: 'Revisión', icon: ReviewIcon, badge: true },
  { id: 'simulator', label: 'Simulador IA', icon: AIIcon },
  { id: 'settings', label: 'Configuración', icon: SettingsIcon, bottom: true },
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
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#f8fafc' }}>
      {/* Sidebar */}
      <aside style={{
        width: '260px',
        backgroundColor: '#0f172a',
        position: 'fixed',
        top: 0,
        left: 0,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 50
      }}>
        {/* Logo */}
        <div style={{
          height: '80px',
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          borderBottom: '1px solid #1e293b'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '42px',
              height: '42px',
              background: 'linear-gradient(135deg, #60a5fa, #3b82f6)',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: '700',
              fontSize: '14px',
              boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)'
            }}>
              G4U
            </div>
            <div>
              <p style={{ fontWeight: '600', color: 'white', fontSize: '15px', margin: 0 }}>Rentabilidad</p>
              <p style={{ fontSize: '12px', color: '#64748b', margin: 0 }}>Financial Dashboard</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: '16px' }}>
          <p style={{
            padding: '8px 12px',
            fontSize: '11px',
            fontWeight: '600',
            color: '#64748b',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            margin: 0
          }}>
            Menú
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '8px' }}>
            {navItems.filter(i => !i.bottom).map(item => (
              <NavLink
                key={item.id}
                item={item}
                active={currentView === item.id}
                badge={item.badge ? pendingCount : null}
                onClick={() => onNavigate(item.id)}
              />
            ))}
          </div>
        </nav>

        {/* Bottom Section */}
        <div style={{ padding: '16px', borderTop: '1px solid #1e293b' }}>
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
            <div style={{
              marginTop: '16px',
              padding: '10px 12px',
              backgroundColor: 'rgba(30, 41, 59, 0.5)',
              borderRadius: '10px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  width: '8px',
                  height: '8px',
                  backgroundColor: '#10b981',
                  borderRadius: '50%'
                }}></span>
                <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                  Sincronizado {formatRelativeTime(lastSync)}
                </span>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, marginLeft: '260px', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        {/* Top Bar */}
        <header style={{
          height: '80px',
          backgroundColor: 'white',
          borderBottom: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 32px',
          position: 'sticky',
          top: 0,
          zIndex: 40,
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
        }}>
          <div>
            <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#0f172a', margin: 0 }}>
              {getPageTitle(currentView)}
            </h1>
            <p style={{ fontSize: '14px', color: '#64748b', marginTop: '2px', margin: 0 }}>
              {getPageSubtitle(currentView)}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* Period Selector */}
            <div style={{
              display: 'flex',
              backgroundColor: '#f1f5f9',
              borderRadius: '12px',
              padding: '4px'
            }}>
              {['week', 'month', 'quarter', 'year'].map(p => (
                <button
                  key={p}
                  onClick={() => onPeriodChange(p)}
                  style={{
                    padding: '10px 16px',
                    fontSize: '14px',
                    fontWeight: '500',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    backgroundColor: period === p ? 'white' : 'transparent',
                    color: period === p ? '#0f172a' : '#64748b',
                    boxShadow: period === p ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                    transition: 'all 0.15s'
                  }}
                >
                  {p === 'week' ? '7 días' : p === 'month' ? '30 días' : p === 'quarter' ? '90 días' : '1 año'}
                </button>
              ))}
            </div>

            {/* Sync Button */}
            <button
              onClick={onSync}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 20px',
                backgroundColor: '#0f172a',
                color: 'white',
                fontSize: '14px',
                fontWeight: '600',
                border: 'none',
                borderRadius: '10px',
                cursor: 'pointer',
                boxShadow: '0 4px 12px rgba(15, 23, 42, 0.2)'
              }}
              title="Sincronizar"
            >
              <SyncIcon style={{ width: '16px', height: '16px' }} />
              <span>Sincronizar</span>
            </button>
          </div>
        </header>

        {/* Content */}
        <div style={{ flex: 1, padding: '32px', overflowY: 'auto' }}>
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
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '12px 14px',
        borderRadius: '10px',
        textAlign: 'left',
        fontSize: '14px',
        fontWeight: '500',
        border: 'none',
        cursor: 'pointer',
        backgroundColor: active ? '#3b82f6' : 'transparent',
        color: active ? 'white' : '#94a3b8',
        boxShadow: active ? '0 4px 12px rgba(59, 130, 246, 0.3)' : 'none',
        transition: 'all 0.15s'
      }}
    >
      <Icon style={{ width: '20px', height: '20px' }} />
      <span style={{ flex: 1 }}>{item.label}</span>
      {badge > 0 && (
        <span style={{
          fontSize: '12px',
          fontWeight: '700',
          padding: '2px 8px',
          borderRadius: '20px',
          backgroundColor: active ? 'rgba(255,255,255,0.2)' : '#ef4444',
          color: 'white'
        }}>
          {badge}
        </span>
      )}
    </button>
  );
}

function getPageTitle(view) {
  const titles = {
    dashboard: 'Dashboard Ejecutivo',
    profitability: 'Análisis de Rentabilidad',
    transactions: 'Transacciones',
    review: 'Bandeja de Revisión',
    simulator: 'Simulador IA',
    settings: 'Configuración',
  };
  return titles[view] || view;
}

function getPageSubtitle(view) {
  const subtitles = {
    dashboard: 'Vista general de métricas financieras',
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
