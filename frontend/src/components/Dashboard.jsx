import { useMemo } from 'react';
import { formatCurrency, isIncome } from '../utils/format';

export default function Dashboard({ transactions, projects, clients, onNavigate }) {
  // Calculate metrics
  const metrics = useMemo(() => {
    const income = transactions
      .filter(t => isIncome(t))
      .reduce((sum, t) => sum + Math.abs(parseFloat(t.amount) || 0), 0);

    const expenses = transactions
      .filter(t => !isIncome(t))
      .reduce((sum, t) => sum + Math.abs(parseFloat(t.amount) || 0), 0);

    const net = income - expenses;
    // Margen sobre ingresos, limitado a rango razonable
    const margin = income > 0 ? Math.max(-100, Math.min(100, (net / income) * 100)) : 0;

    return { income, expenses, net, margin };
  }, [transactions]);

  // Top clients by income
  const topClients = useMemo(() => {
    const map = {};
    transactions.forEach(t => {
      const id = t.client_id || t.client;
      if (!id) return;
      const info = clients.find(c => c.id === id || c.name === id);
      if (!map[id]) map[id] = { name: info?.name || id, income: 0, expenses: 0 };
      if (isIncome(t)) {
        map[id].income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        map[id].expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });
    return Object.values(map)
      .map(c => ({ ...c, net: c.income - c.expenses }))
      .sort((a, b) => b.income - a.income)
      .slice(0, 5);
  }, [transactions, clients]);

  // Top projects by income
  const topProjects = useMemo(() => {
    const map = {};
    transactions.forEach(t => {
      const id = t.project_id || t.project;
      if (!id) return;
      const info = projects.find(p => p.id === id || p.name === id);
      if (!map[id]) map[id] = { name: info?.name || id, client: info?.client || '', income: 0, expenses: 0 };
      if (isIncome(t)) {
        map[id].income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        map[id].expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });
    return Object.values(map)
      .map(p => ({ ...p, net: p.income - p.expenses }))
      .sort((a, b) => b.income - a.income)
      .slice(0, 5);
  }, [transactions, projects]);

  // Expenses by category
  const categoryData = useMemo(() => {
    const cats = {};
    transactions.filter(t => !isIncome(t)).forEach(t => {
      const cat = t.category || t.qonto_category || 'Otros';
      cats[cat] = (cats[cat] || 0) + Math.abs(parseFloat(t.amount) || 0);
    });
    const total = Object.values(cats).reduce((a, b) => a + b, 0);
    const colors = ['#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#6366F1'];
    return Object.entries(cats)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, value], i) => ({
        name,
        value,
        percent: total > 0 ? (value / total) * 100 : 0,
        color: colors[i % colors.length]
      }));
  }, [transactions]);

  const totalExpenses = categoryData.reduce((s, c) => s + c.value, 0);

  // Pending count
  const pendingCount = transactions.filter(t =>
    !t.project && !t.project_id && !t.client && !t.client_id && !t.excluded
  ).length;

  const marginStatus = metrics.margin >= 20 ? 'good' : metrics.margin >= 0 ? 'warning' : 'bad';

  return (
    <div className="space-y-6">
      {/* KPI Cards Row */}
      <div className="grid grid-cols-4 gap-4">
        <KPICard
          title="Ingresos"
          value={formatCurrency(metrics.income, true)}
          icon="↑"
          color="emerald"
        />
        <KPICard
          title="Gastos"
          value={formatCurrency(metrics.expenses, true)}
          icon="↓"
          color="red"
        />
        <KPICard
          title="Resultado"
          value={formatCurrency(metrics.net, true)}
          icon={metrics.net >= 0 ? '+' : '-'}
          color={metrics.net >= 0 ? 'blue' : 'red'}
        />
        <KPICard
          title="Margen"
          value={`${metrics.margin.toFixed(1)}%`}
          icon="%"
          color={marginStatus === 'good' ? 'emerald' : marginStatus === 'warning' ? 'amber' : 'red'}
          status={marginStatus === 'good' ? 'Excelente' : marginStatus === 'warning' ? 'Moderado' : 'Negativo'}
        />
      </div>

      {/* Alert for pending */}
      {pendingCount > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center text-amber-600 text-xl">
              ⚡
            </div>
            <div>
              <p className="font-semibold text-amber-900">{pendingCount} transacciones pendientes</p>
              <p className="text-sm text-amber-700">Sin asignar a proyecto o cliente</p>
            </div>
          </div>
          <button
            onClick={() => onNavigate('review')}
            className="px-4 py-2 bg-amber-600 text-white font-medium rounded-lg hover:bg-amber-700 transition-colors"
          >
            Revisar ahora →
          </button>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Left: Categories */}
        <div className="bg-white rounded-xl border border-slate-200 p-6" style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold text-slate-900 text-lg">Gastos por Categoria</h3>
            <button onClick={() => onNavigate('transactions')} className="text-sm text-blue-600 hover:underline">
              Ver todo →
            </button>
          </div>

          {categoryData.length === 0 ? (
            <p className="text-slate-400 text-center py-8">Sin datos de gastos</p>
          ) : (
            <div className="flex gap-6">
              {/* Donut Chart */}
              <div className="relative w-40 h-40 flex-shrink-0">
                <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
                  {(() => {
                    let offset = 0;
                    return categoryData.map((cat, i) => {
                      const circumference = 2 * Math.PI * 35;
                      const dash = (cat.percent / 100) * circumference;
                      const currentOffset = offset;
                      offset += dash;
                      return (
                        <circle
                          key={i}
                          cx="50"
                          cy="50"
                          r="35"
                          fill="none"
                          strokeWidth="12"
                          stroke={cat.color}
                          strokeDasharray={`${dash} ${circumference}`}
                          strokeDashoffset={-currentOffset}
                        />
                      );
                    });
                  })()}
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <p className="text-lg font-bold text-slate-900">{formatCurrency(totalExpenses, true)}</p>
                    <p className="text-xs text-slate-500">Total</p>
                  </div>
                </div>
              </div>

              {/* Legend */}
              <div className="flex-1 space-y-2">
                {categoryData.map((cat, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: cat.color }} />
                    <span className="text-sm text-slate-600 flex-1 truncate">{cat.name}</span>
                    <span className="text-sm font-medium text-slate-900">{formatCurrency(cat.value, true)}</span>
                    <span className="text-xs text-slate-400 w-10 text-right">{cat.percent.toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Summary */}
        <div className="bg-white rounded-xl border border-slate-200 p-6" style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
          <h3 className="font-semibold text-slate-900 text-lg mb-6">Resumen</h3>
          <div className="space-y-4">
            <SummaryRow label="Clientes activos" value={clients.length} />
            <SummaryRow label="Proyectos" value={projects.length} />
            <SummaryRow label="Transacciones" value={transactions.length} />
            <SummaryRow label="Sin asignar" value={pendingCount} highlight={pendingCount > 0} />
          </div>
        </div>
      </div>

      {/* Rankings */}
      <div className="grid grid-cols-2 gap-6">
        {/* Top Clients */}
        <div className="bg-white rounded-xl border border-slate-200 p-6" style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-900 text-lg">Top Clientes</h3>
            <button onClick={() => onNavigate('profitability')} className="text-sm text-blue-600 hover:underline">
              Ver todo →
            </button>
          </div>
          {topClients.length === 0 ? (
            <p className="text-slate-400 text-center py-8">Sin datos</p>
          ) : (
            <div className="space-y-3">
              {topClients.map((client, i) => (
                <RankingItem
                  key={i}
                  rank={i + 1}
                  name={client.name}
                  value={formatCurrency(client.income, true)}
                  secondary={`Neto: ${formatCurrency(client.net, true)}`}
                  secondaryColor={client.net >= 0 ? 'text-emerald-600' : 'text-red-500'}
                />
              ))}
            </div>
          )}
        </div>

        {/* Top Projects */}
        <div className="bg-white rounded-xl border border-slate-200 p-6" style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-900 text-lg">Top Proyectos</h3>
            <button onClick={() => onNavigate('profitability')} className="text-sm text-blue-600 hover:underline">
              Ver todo →
            </button>
          </div>
          {topProjects.length === 0 ? (
            <p className="text-slate-400 text-center py-8">Sin datos</p>
          ) : (
            <div className="space-y-3">
              {topProjects.map((proj, i) => (
                <RankingItem
                  key={i}
                  rank={i + 1}
                  name={proj.name}
                  subtitle={proj.client}
                  value={formatCurrency(proj.income, true)}
                  secondary={`Neto: ${formatCurrency(proj.net, true)}`}
                  secondaryColor={proj.net >= 0 ? 'text-emerald-600' : 'text-red-500'}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function KPICard({ title, value, icon, color, status }) {
  const colorStyles = {
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    red: 'bg-red-50 border-red-200 text-red-600',
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
  };

  const iconStyles = {
    emerald: 'bg-emerald-100 text-emerald-600',
    red: 'bg-red-100 text-red-600',
    blue: 'bg-blue-100 text-blue-600',
    amber: 'bg-amber-100 text-amber-600',
  };

  return (
    <div className={`rounded-xl border p-5 ${colorStyles[color]}`}>
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${iconStyles[color]}`}>
          {icon}
        </div>
        <span className="text-sm font-medium opacity-80">{title}</span>
      </div>
      <p className="text-2xl font-bold font-mono">{value}</p>
      {status && <p className="text-xs mt-1 opacity-70">{status}</p>}
    </div>
  );
}

function SummaryRow({ label, value, highlight }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <span className="text-sm text-slate-600">{label}</span>
      <span className={`text-lg font-bold ${highlight ? 'text-amber-600' : 'text-slate-900'}`}>
        {value}
      </span>
    </div>
  );
}

function RankingItem({ rank, name, subtitle, value, secondary, secondaryColor }) {
  const medals = ['🥇', '🥈', '🥉'];

  return (
    <div className="flex items-center gap-3 py-2">
      <div className="w-8 text-center">
        {rank <= 3 ? (
          <span className="text-lg">{medals[rank - 1]}</span>
        ) : (
          <span className="text-sm font-bold text-slate-400">#{rank}</span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-900 truncate">{name}</p>
        {subtitle && <p className="text-xs text-slate-500 truncate">{subtitle}</p>}
      </div>
      <div className="text-right">
        <p className="font-bold font-mono text-slate-900">{value}</p>
        <p className={`text-xs font-medium ${secondaryColor}`}>{secondary}</p>
      </div>
    </div>
  );
}
