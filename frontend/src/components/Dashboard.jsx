import { useMemo } from 'react';
import { formatCurrency, formatPercent, isIncome } from '../utils/format';

export default function Dashboard({ transactions, projects, clients, onNavigate }) {
  // Calculate main metrics
  const metrics = useMemo(() => {
    let income = 0, expenses = 0;

    transactions.forEach(t => {
      const amount = Math.abs(parseFloat(t.amount) || 0);
      if (isIncome(t)) {
        income += amount;
      } else {
        expenses += amount;
      }
    });

    const net = income - expenses;
    const margin = income > 0 ? (net / income) * 100 : 0;

    return { income, expenses, net, margin };
  }, [transactions]);

  // Pending transactions count
  const pendingCount = useMemo(() => {
    return transactions.filter(t =>
      !t.project && !t.project_id && !t.client && !t.client_id && !t.excluded
    ).length;
  }, [transactions]);

  // Top 5 clients by income
  const topClients = useMemo(() => {
    const map = new Map();

    transactions.forEach(t => {
      const id = t.client_id || t.client;
      if (!id) return;

      const info = clients.find(c => c.id === id || c.name === id);
      const name = info?.name || (id.startsWith('rec') ? 'Cliente' : id);

      if (!map.has(id)) {
        map.set(id, { name, income: 0, expenses: 0 });
      }

      const entry = map.get(id);
      if (isIncome(t)) {
        entry.income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        entry.expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });

    return Array.from(map.values())
      .map(c => ({ ...c, net: c.income - c.expenses }))
      .sort((a, b) => b.income - a.income)
      .slice(0, 5);
  }, [transactions, clients]);

  // Top 5 projects by income
  const topProjects = useMemo(() => {
    const map = new Map();

    transactions.forEach(t => {
      const id = t.project_id || t.project;
      if (!id) return;

      const info = projects.find(p => p.id === id || p.name === id);
      const name = info?.name || (id.startsWith('rec') ? 'Proyecto' : id);
      const client = info?.client || '';

      if (!map.has(id)) {
        map.set(id, { name, client, income: 0, expenses: 0 });
      }

      const entry = map.get(id);
      if (isIncome(t)) {
        entry.income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        entry.expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });

    return Array.from(map.values())
      .map(p => ({ ...p, net: p.income - p.expenses }))
      .sort((a, b) => b.income - a.income)
      .slice(0, 5);
  }, [transactions, projects]);

  // Expenses by category
  const expensesByCategory = useMemo(() => {
    const map = new Map();
    let total = 0;

    transactions.filter(t => !isIncome(t)).forEach(t => {
      const cat = t.category || t.qonto_category || 'Otros';
      const amount = Math.abs(parseFloat(t.amount) || 0);
      map.set(cat, (map.get(cat) || 0) + amount);
      total += amount;
    });

    const colors = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#6366f1'];

    return Array.from(map.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, value], i) => ({
        name,
        value,
        percent: total > 0 ? (value / total) * 100 : 0,
        color: colors[i]
      }));
  }, [transactions]);

  const totalExpenses = expensesByCategory.reduce((sum, c) => sum + c.value, 0);
  const marginStatus = metrics.margin >= 20 ? 'excellent' : metrics.margin >= 0 ? 'moderate' : 'negative';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
        <KPICard
          label="Ingresos"
          value={formatCurrency(metrics.income, true)}
          trend="+12.5%"
          trendUp={true}
          color="#10b981"
          bgColor="#ecfdf5"
        />
        <KPICard
          label="Gastos"
          value={formatCurrency(metrics.expenses, true)}
          trend="-3.2%"
          trendUp={false}
          color="#ef4444"
          bgColor="#fef2f2"
        />
        <KPICard
          label="Resultado Neto"
          value={formatCurrency(metrics.net, true)}
          color={metrics.net >= 0 ? '#3b82f6' : '#ef4444'}
          bgColor={metrics.net >= 0 ? '#eff6ff' : '#fef2f2'}
        />
        <KPICard
          label="Margen"
          value={`${metrics.margin.toFixed(1)}%`}
          badge={marginStatus === 'excellent' ? 'Excelente' : marginStatus === 'moderate' ? 'Moderado' : 'Negativo'}
          badgeColor={marginStatus === 'excellent' ? '#10b981' : marginStatus === 'moderate' ? '#f59e0b' : '#ef4444'}
          color={marginStatus === 'excellent' ? '#10b981' : marginStatus === 'moderate' ? '#f59e0b' : '#ef4444'}
          bgColor={marginStatus === 'excellent' ? '#ecfdf5' : marginStatus === 'moderate' ? '#fffbeb' : '#fef2f2'}
        />
      </div>

      {/* Alert for pending */}
      {pendingCount > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          backgroundColor: '#fffbeb',
          border: '1px solid #fcd34d',
          borderRadius: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              backgroundColor: '#fbbf24',
              borderRadius: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px'
            }}>⚡</div>
            <div>
              <div style={{ fontWeight: '600', color: '#92400e' }}>{pendingCount} transacciones pendientes</div>
              <div style={{ fontSize: '14px', color: '#a16207' }}>Requieren asignación a proyecto o cliente</div>
            </div>
          </div>
          <button
            onClick={() => onNavigate('review')}
            style={{
              padding: '10px 20px',
              backgroundColor: '#f59e0b',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontWeight: '600',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Revisar ahora →
          </button>
        </div>
      )}

      {/* Two Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Expenses by Category */}
        <Card title="Gastos por Categoría" action="Ver todo →" onAction={() => onNavigate('transactions')}>
          {expensesByCategory.length === 0 ? (
            <EmptyState message="Sin datos de gastos" />
          ) : (
            <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
              {/* Donut Chart */}
              <div style={{ position: 'relative', width: '140px', height: '140px', flexShrink: 0 }}>
                <svg viewBox="0 0 100 100" style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
                  {expensesByCategory.reduce((acc, cat, i) => {
                    const r = 35;
                    const circumference = 2 * Math.PI * r;
                    const dash = (cat.percent / 100) * circumference;
                    const offset = acc.offset;
                    acc.elements.push(
                      <circle
                        key={i}
                        cx="50"
                        cy="50"
                        r={r}
                        fill="none"
                        strokeWidth="12"
                        stroke={cat.color}
                        strokeDasharray={`${dash} ${circumference}`}
                        strokeDashoffset={-offset}
                      />
                    );
                    acc.offset += dash;
                    return acc;
                  }, { offset: 0, elements: [] }).elements}
                </svg>
                <div style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <div style={{ fontSize: '16px', fontWeight: '700', color: '#1e293b' }}>
                    {formatCurrency(totalExpenses, true)}
                  </div>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>Total</div>
                </div>
              </div>

              {/* Legend */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {expensesByCategory.map((cat, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: cat.color }} />
                    <span style={{ flex: 1, fontSize: '13px', color: '#475569', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{cat.name}</span>
                    <span style={{ fontSize: '13px', fontWeight: '600', color: '#1e293b', fontFamily: 'monospace' }}>{formatCurrency(cat.value, true)}</span>
                    <span style={{ fontSize: '12px', color: '#94a3b8', width: '40px', textAlign: 'right' }}>{cat.percent.toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        {/* Quick Stats */}
        <Card title="Resumen General">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <StatRow label="Clientes activos" value={clients.length} />
            <StatRow label="Proyectos" value={projects.length} />
            <StatRow label="Transacciones" value={transactions.length} />
            <StatRow label="Sin asignar" value={pendingCount} highlight={pendingCount > 0} />
          </div>
        </Card>
      </div>

      {/* Rankings */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        <Card title="Top Clientes" subtitle="Por ingresos" action="Ver análisis →" onAction={() => onNavigate('profitability')}>
          {topClients.length === 0 ? (
            <EmptyState message="Sin clientes asignados" />
          ) : (
            <RankingList items={topClients} />
          )}
        </Card>

        <Card title="Top Proyectos" subtitle="Por ingresos" action="Ver análisis →" onAction={() => onNavigate('profitability')}>
          {topProjects.length === 0 ? (
            <EmptyState message="Sin proyectos asignados" />
          ) : (
            <RankingList items={topProjects} showSubtitle />
          )}
        </Card>
      </div>
    </div>
  );
}

function KPICard({ label, value, trend, trendUp, badge, badgeColor, color, bgColor }) {
  return (
    <div style={{
      backgroundColor: bgColor,
      borderRadius: '12px',
      padding: '20px',
      border: `1px solid ${color}20`
    }}>
      <div style={{ fontSize: '13px', fontWeight: '500', color: '#64748b', marginBottom: '8px' }}>{label}</div>
      <div style={{ fontSize: '28px', fontWeight: '700', color: color, fontFamily: 'monospace' }}>{value}</div>
      {trend && (
        <div style={{ fontSize: '13px', color: trendUp ? '#10b981' : '#ef4444', marginTop: '4px' }}>
          {trend} vs periodo anterior
        </div>
      )}
      {badge && (
        <div style={{
          display: 'inline-block',
          marginTop: '8px',
          padding: '4px 10px',
          backgroundColor: `${badgeColor}20`,
          color: badgeColor,
          borderRadius: '20px',
          fontSize: '12px',
          fontWeight: '600'
        }}>
          {badge}
        </div>
      )}
    </div>
  );
}

function Card({ title, subtitle, action, onAction, children }) {
  return (
    <div style={{
      backgroundColor: 'white',
      borderRadius: '12px',
      border: '1px solid #e2e8f0',
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 20px',
        borderBottom: '1px solid #f1f5f9'
      }}>
        <div>
          <div style={{ fontSize: '16px', fontWeight: '600', color: '#1e293b' }}>{title}</div>
          {subtitle && <div style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>{subtitle}</div>}
        </div>
        {action && (
          <button
            onClick={onAction}
            style={{
              background: 'none',
              border: 'none',
              color: '#3b82f6',
              fontSize: '13px',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            {action}
          </button>
        )}
      </div>
      <div style={{ padding: '20px' }}>
        {children}
      </div>
    </div>
  );
}

function StatRow({ label, value, highlight }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '12px 0',
      borderBottom: '1px solid #f1f5f9'
    }}>
      <span style={{ fontSize: '14px', color: '#64748b' }}>{label}</span>
      <span style={{
        fontSize: '18px',
        fontWeight: '700',
        color: highlight ? '#f59e0b' : '#1e293b'
      }}>{value}</span>
    </div>
  );
}

function RankingList({ items, showSubtitle }) {
  const medals = ['🥇', '🥈', '🥉'];
  const maxIncome = items[0]?.income || 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {items.map((item, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '28px', textAlign: 'center', fontSize: '16px' }}>
            {i < 3 ? medals[i] : <span style={{ color: '#94a3b8', fontWeight: '600' }}>#{i + 1}</span>}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: '500', color: '#1e293b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.name}</div>
            {showSubtitle && item.client && (
              <div style={{ fontSize: '12px', color: '#94a3b8' }}>{item.client}</div>
            )}
            <div style={{ marginTop: '6px', height: '4px', backgroundColor: '#f1f5f9', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${(item.income / maxIncome) * 100}%`, backgroundColor: '#3b82f6', borderRadius: '2px' }} />
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontWeight: '600', fontFamily: 'monospace', color: '#1e293b' }}>{formatCurrency(item.income, true)}</div>
            <div style={{ fontSize: '12px', color: item.net >= 0 ? '#10b981' : '#ef4444' }}>
              Neto: {formatCurrency(item.net, true)}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState({ message }) {
  return (
    <div style={{ textAlign: 'center', padding: '32px', color: '#94a3b8' }}>
      <div style={{ fontSize: '32px', marginBottom: '8px' }}>📊</div>
      <div>{message}</div>
    </div>
  );
}
