import { useMemo } from 'react';
import { formatCurrency, formatPercent, isIncome } from '../utils/format';

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
    const margin = income > 0 ? (net / income) * 100 : 0;
    const incomeCount = transactions.filter(t => isIncome(t)).length;
    const expenseCount = transactions.filter(t => !isIncome(t)).length;

    return { income, expenses, net, margin, incomeCount, expenseCount };
  }, [transactions]);

  // Top clients by profitability
  const topClients = useMemo(() => {
    const clientMap = {};

    transactions.forEach(t => {
      const clientId = t.client_id || t.client;
      if (!clientId) return;

      // Find client name from clients array
      const clientInfo = clients.find(c => c.id === clientId || c.name === clientId);
      const clientName = clientInfo?.name || clientId;

      if (!clientMap[clientId]) {
        clientMap[clientId] = { id: clientId, name: clientName, income: 0, expenses: 0 };
      }

      if (isIncome(t)) {
        clientMap[clientId].income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        clientMap[clientId].expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });

    return Object.values(clientMap)
      .map(c => ({
        ...c,
        net: c.income - c.expenses,
        margin: c.income > 0 ? ((c.income - c.expenses) / c.income) * 100 : 0
      }))
      .sort((a, b) => b.income - a.income)
      .slice(0, 5);
  }, [transactions, clients]);

  // Top projects by profitability
  const topProjects = useMemo(() => {
    const projectMap = {};

    transactions.forEach(t => {
      const projId = t.project_id || t.project;
      if (!projId) return;

      const projInfo = projects.find(p => p.id === projId || p.name === projId);

      if (!projectMap[projId]) {
        projectMap[projId] = {
          id: projId,
          name: projInfo?.name || projId,
          client: projInfo?.client || '',
          income: 0,
          expenses: 0
        };
      }

      if (isIncome(t)) {
        projectMap[projId].income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        projectMap[projId].expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });

    return Object.values(projectMap)
      .map(p => ({
        ...p,
        net: p.income - p.expenses,
        margin: p.income > 0 ? ((p.income - p.expenses) / p.income) * 100 : 0
      }))
      .sort((a, b) => b.income - a.income)
      .slice(0, 5);
  }, [transactions, projects]);

  // Expenses by category
  const categoryData = useMemo(() => {
    const cats = {};
    transactions.filter(t => !isIncome(t)).forEach(t => {
      const cat = t.category || t.qonto_category || 'Sin categoria';
      cats[cat] = (cats[cat] || 0) + Math.abs(parseFloat(t.amount) || 0);
    });

    const total = Object.values(cats).reduce((a, b) => a + b, 0);

    return Object.entries(cats)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, value]) => ({ name, value, percent: total > 0 ? (value / total) * 100 : 0 }));
  }, [transactions]);

  // Pending count
  const pendingCount = transactions.filter(t =>
    !t.project && !t.project_id && !t.client && !t.client_id && !t.excluded
  ).length;

  const categoryColors = [
    'bg-blue-500',
    'bg-indigo-500',
    'bg-violet-500',
    'bg-purple-500',
    'bg-fuchsia-500',
    'bg-pink-500',
  ];

  return (
    <div className="space-y-6">
      {/* Hero KPI Cards */}
      <div className="grid grid-cols-4 gap-5">
        {/* Main Margin Card - Premium gradient */}
        <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-6 text-white shadow-xl">
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/20 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl" />
          <div className="relative">
            <p className="text-slate-400 text-sm font-medium tracking-wide uppercase mb-3">Margen Neto</p>
            <p className="text-5xl font-bold tracking-tight mb-3">
              {metrics.margin >= 0 ? '+' : ''}{metrics.margin.toFixed(1)}%
            </p>
            <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
              metrics.margin >= 20 ? 'bg-emerald-500/20 text-emerald-400' :
              metrics.margin >= 0 ? 'bg-amber-500/20 text-amber-400' :
              'bg-red-500/20 text-red-400'
            }`}>
              <StatusDot status={metrics.margin >= 20 ? 'success' : metrics.margin >= 0 ? 'warning' : 'error'} />
              <span>{metrics.margin >= 20 ? 'Excelente' : metrics.margin >= 0 ? 'Moderado' : 'Critico'}</span>
            </div>
          </div>
        </div>

        {/* Income Card */}
        <KPICard
          label="Ingresos"
          value={formatCurrency(metrics.income)}
          icon={<ArrowUpIcon className="w-5 h-5 text-emerald-500" />}
          iconBg="bg-emerald-50"
          valueColor="text-emerald-600"
          subtitle={`${metrics.incomeCount} transacciones`}
        />

        {/* Expenses Card */}
        <KPICard
          label="Gastos"
          value={formatCurrency(metrics.expenses)}
          icon={<ArrowDownIcon className="w-5 h-5 text-red-500" />}
          iconBg="bg-red-50"
          valueColor="text-red-500"
          subtitle={`${metrics.expenseCount} transacciones`}
        />

        {/* Net Result Card */}
        <KPICard
          label="Resultado Neto"
          value={formatCurrency(Math.abs(metrics.net))}
          icon={metrics.net >= 0 ? <TrendUpIcon className="w-5 h-5 text-emerald-500" /> : <TrendDownIcon className="w-5 h-5 text-red-500" />}
          iconBg={metrics.net >= 0 ? "bg-emerald-50" : "bg-red-50"}
          valueColor={metrics.net >= 0 ? 'text-emerald-600' : 'text-red-500'}
          subtitle={metrics.net >= 0 ? 'Beneficio neto' : 'Perdida neta'}
          prefix={metrics.net >= 0 ? '+' : '-'}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left - Categories Chart */}
        <div className="col-span-8">
          <div className="bg-white rounded-2xl border border-slate-200/60 shadow-soft overflow-hidden">
            <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">Distribucion de Gastos</h3>
                <p className="text-sm text-slate-500 mt-0.5">Por categoria de gasto</p>
              </div>
              <button
                onClick={() => onNavigate('transactions')}
                className="text-sm text-blue-600 font-medium hover:text-blue-700 transition-colors"
              >
                Ver detalle →
              </button>
            </div>

            <div className="p-6">
              {categoryData.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <ChartIcon className="w-8 h-8 text-slate-400" />
                  </div>
                  <p className="text-slate-500 font-medium">Sin datos de gastos</p>
                  <p className="text-sm text-slate-400 mt-1">Los gastos apareceran aqui</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-6">
                  {/* Bars */}
                  <div className="space-y-4">
                    {categoryData.map((cat, i) => (
                      <div key={cat.name} className="group">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-slate-700 truncate max-w-[200px]">{cat.name}</span>
                          <span className="text-sm font-bold text-slate-900 font-mono">{formatCurrency(cat.value, true)}</span>
                        </div>
                        <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${categoryColors[i]} rounded-full transition-all duration-700 ease-out`}
                            style={{ width: `${cat.percent}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Donut visual */}
                  <div className="flex items-center justify-center">
                    <div className="relative w-44 h-44">
                      <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                        {categoryData.reduce((acc, cat, i) => {
                          const offset = acc.offset;
                          const dashArray = (cat.percent * 251.2) / 100;
                          acc.elements.push(
                            <circle
                              key={cat.name}
                              cx="50"
                              cy="50"
                              r="40"
                              fill="none"
                              strokeWidth="12"
                              className={categoryColors[i].replace('bg-', 'stroke-')}
                              strokeDasharray={`${dashArray} 251.2`}
                              strokeDashoffset={-offset}
                              style={{ transition: 'stroke-dasharray 0.7s ease' }}
                            />
                          );
                          acc.offset += dashArray;
                          return acc;
                        }, { offset: 0, elements: [] }).elements}
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="text-center">
                          <p className="text-2xl font-bold text-slate-900">{formatCurrency(metrics.expenses, true)}</p>
                          <p className="text-xs text-slate-500 font-medium">Total gastos</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right - Alerts & Quick Actions */}
        <div className="col-span-4 space-y-5">
          {/* Pending Alert */}
          {pendingCount > 0 && (
            <div className="bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200/60 rounded-2xl p-5 shadow-soft">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-amber-500 rounded-xl flex items-center justify-center shadow-lg shadow-amber-500/30">
                  <AlertIcon className="w-6 h-6 text-white" />
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-slate-900 text-lg">{pendingCount}</p>
                  <p className="text-sm text-slate-600">Transacciones sin asignar</p>
                </div>
              </div>
              <button
                onClick={() => onNavigate('review')}
                className="mt-4 w-full py-2.5 bg-slate-900 text-white text-sm font-semibold rounded-xl hover:bg-slate-800 transition-colors shadow-lg shadow-slate-900/20"
              >
                Revisar ahora
              </button>
            </div>
          )}

          {/* Quick Stats */}
          <div className="bg-white rounded-2xl border border-slate-200/60 shadow-soft p-5">
            <h4 className="font-semibold text-slate-900 mb-4">Resumen Rapido</h4>
            <div className="space-y-3">
              <QuickStat label="Clientes activos" value={clients.length} />
              <QuickStat label="Proyectos" value={projects.length} />
              <QuickStat label="Transacciones" value={transactions.length} />
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Grid - Rankings */}
      <div className="grid grid-cols-2 gap-6">
        {/* Top Clients */}
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-soft overflow-hidden">
          <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Top Clientes</h3>
              <p className="text-sm text-slate-500 mt-0.5">Por volumen de ingresos</p>
            </div>
            <button
              onClick={() => onNavigate('profitability')}
              className="text-sm text-blue-600 font-medium hover:text-blue-700 transition-colors"
            >
              Ver todos →
            </button>
          </div>

          <div className="p-4">
            {topClients.length === 0 ? (
              <EmptyState icon={<UsersIcon />} message="Sin datos de clientes" />
            ) : (
              <div className="space-y-1">
                {topClients.map((client, i) => (
                  <RankingRow
                    key={client.id}
                    position={i + 1}
                    name={client.name}
                    value={formatCurrency(client.income, true)}
                    margin={client.margin}
                    onClick={() => onNavigate('profitability')}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Top Projects */}
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-soft overflow-hidden">
          <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Top Proyectos</h3>
              <p className="text-sm text-slate-500 mt-0.5">Por volumen de ingresos</p>
            </div>
            <button
              onClick={() => onNavigate('profitability')}
              className="text-sm text-blue-600 font-medium hover:text-blue-700 transition-colors"
            >
              Ver todos →
            </button>
          </div>

          <div className="p-4">
            {topProjects.length === 0 ? (
              <EmptyState icon={<FolderIcon />} message="Sin datos de proyectos" />
            ) : (
              <div className="space-y-1">
                {topProjects.map((project, i) => (
                  <RankingRow
                    key={project.id}
                    position={i + 1}
                    name={project.name}
                    subtitle={project.client || 'Sin cliente'}
                    value={formatCurrency(project.income, true)}
                    margin={project.margin}
                    onClick={() => onNavigate('profitability')}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Sub-components
function KPICard({ label, value, icon, iconBg, valueColor, subtitle, prefix = '' }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-soft hover:shadow-lg transition-shadow duration-300">
      <div className="flex items-center gap-4 mb-4">
        <div className={`w-12 h-12 ${iconBg} rounded-xl flex items-center justify-center`}>
          {icon}
        </div>
        <p className="text-sm font-medium text-slate-500 uppercase tracking-wide">{label}</p>
      </div>
      <p className={`text-3xl font-bold font-mono ${valueColor}`}>
        {prefix}{value}
      </p>
      <p className="text-sm text-slate-400 mt-1">{subtitle}</p>
    </div>
  );
}

function RankingRow({ position, name, subtitle, value, margin, onClick }) {
  const medals = ['🥇', '🥈', '🥉'];

  return (
    <div
      onClick={onClick}
      className="flex items-center gap-4 p-3 rounded-xl hover:bg-slate-50 cursor-pointer transition-colors group"
    >
      <div className="w-8 h-8 flex items-center justify-center">
        {position <= 3 ? (
          <span className="text-xl">{medals[position - 1]}</span>
        ) : (
          <span className="text-sm font-bold text-slate-400">#{position}</span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-900 truncate group-hover:text-blue-600 transition-colors">{name}</p>
        {subtitle && <p className="text-xs text-slate-500 truncate">{subtitle}</p>}
      </div>
      <div className="text-right">
        <p className="font-bold font-mono text-slate-900">{value}</p>
        <p className={`text-xs font-semibold ${margin >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
          {margin >= 0 ? '+' : ''}{margin.toFixed(1)}%
        </p>
      </div>
    </div>
  );
}

function QuickStat({ label, value }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <span className="text-sm text-slate-600">{label}</span>
      <span className="text-lg font-bold text-slate-900">{value}</span>
    </div>
  );
}

function StatusDot({ status }) {
  const colors = {
    success: 'bg-emerald-400',
    warning: 'bg-amber-400',
    error: 'bg-red-400',
  };
  return <span className={`w-2 h-2 rounded-full ${colors[status]} animate-pulse`} />;
}

function EmptyState({ icon, message }) {
  return (
    <div className="text-center py-8">
      <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3">
        {icon}
      </div>
      <p className="text-slate-500 text-sm">{message}</p>
    </div>
  );
}

// Icons
function ArrowUpIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  );
}

function ArrowDownIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M12 5v14M19 12l-7 7-7-7" />
    </svg>
  );
}

function TrendUpIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M23 6l-9.5 9.5-5-5L1 18" />
      <path d="M17 6h6v6" />
    </svg>
  );
}

function TrendDownIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M23 18l-9.5-9.5-5 5L1 6" />
      <path d="M17 18h6v-6" />
    </svg>
  );
}

function ChartIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 20V10M12 20V4M6 20v-6" />
    </svg>
  );
}

function AlertIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10"/>
      <path d="M12 8v4M12 16h.01"/>
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg className="w-6 h-6 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
    </svg>
  );
}

function FolderIcon() {
  return (
    <svg className="w-6 h-6 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
    </svg>
  );
}
