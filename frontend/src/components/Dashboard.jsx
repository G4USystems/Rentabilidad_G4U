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
    const clientData = {};
    transactions.forEach(t => {
      const client = t.client || t.client_id;
      if (!client) return;
      if (!clientData[client]) clientData[client] = { name: client, income: 0, expenses: 0 };
      if (isIncome(t)) {
        clientData[client].income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        clientData[client].expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });

    return Object.values(clientData)
      .map(c => ({
        ...c,
        net: c.income - c.expenses,
        margin: c.income > 0 ? ((c.income - c.expenses) / c.income) * 100 : 0
      }))
      .sort((a, b) => b.income - a.income)
      .slice(0, 5);
  }, [transactions]);

  // Top projects by profitability
  const topProjects = useMemo(() => {
    const projectData = {};
    transactions.forEach(t => {
      const proj = t.project || t.project_id;
      if (!proj) return;
      if (!projectData[proj]) {
        const info = projects.find(p => p.id === proj || p.name === proj);
        projectData[proj] = { name: info?.name || proj, client: info?.client || '', income: 0, expenses: 0 };
      }
      if (isIncome(t)) {
        projectData[proj].income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        projectData[proj].expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });

    return Object.values(projectData)
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
    return Object.entries(cats)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6);
  }, [transactions]);

  const maxCategoryValue = categoryData[0]?.[1] || 1;

  // Pending count
  const pendingCount = transactions.filter(t =>
    !t.project && !t.project_id && !t.client && !t.client_id && !t.excluded
  ).length;

  return (
    <div className="animate-fadeIn">
      {/* Hero Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {/* Main Margin Card */}
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white">
          <p className="text-blue-100 text-sm font-medium mb-2">Margen Neto</p>
          <p className="text-4xl font-bold font-mono mb-2">{formatPercent(metrics.margin)}</p>
          <div className="inline-flex items-center gap-1 bg-white/20 px-2.5 py-1 rounded-full text-sm">
            <TrendIcon up={metrics.margin >= 0} />
            <span>{metrics.margin >= 0 ? '+' : ''}{metrics.margin.toFixed(1)}%</span>
          </div>
        </div>

        {/* Income */}
        <MetricCard
          label="Ingresos"
          value={formatCurrency(metrics.income)}
          valueClass="text-emerald-600"
          subtitle={`${metrics.incomeCount} transacciones`}
        />

        {/* Expenses */}
        <MetricCard
          label="Gastos"
          value={formatCurrency(metrics.expenses)}
          valueClass="text-red-500"
          subtitle={`${metrics.expenseCount} transacciones`}
        />

        {/* Net Result */}
        <MetricCard
          label="Resultado Neto"
          value={formatCurrency(metrics.net)}
          valueClass={metrics.net >= 0 ? 'text-emerald-600' : 'text-red-500'}
          subtitle={`${metrics.net >= 0 ? 'Beneficio' : 'Perdida'}`}
        />
      </div>

      {/* Dashboard Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left Column - Charts */}
        <div className="col-span-2 space-y-6">
          {/* Category Breakdown */}
          <Card title="Gastos por Categoria" action="Ver todo" onAction={() => onNavigate('transactions')}>
            <div className="space-y-4">
              {categoryData.length === 0 ? (
                <p className="text-slate-400 text-center py-8">Sin datos de gastos</p>
              ) : (
                categoryData.map(([name, value]) => (
                  <div key={name} className="flex items-center gap-4">
                    <div className="w-32 text-sm font-medium text-slate-700 truncate">{name}</div>
                    <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full transition-all duration-500"
                        style={{ width: `${(value / maxCategoryValue) * 100}%` }}
                      />
                    </div>
                    <div className="w-24 text-right text-sm font-semibold font-mono text-slate-900">
                      {formatCurrency(value, true)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>

        {/* Right Column - Lists */}
        <div className="space-y-6">
          {/* Top Clients */}
          <Card title="Top Clientes" action="Ver todos" onAction={() => onNavigate('profitability')}>
            {topClients.length === 0 ? (
              <p className="text-slate-400 text-center py-8">Sin datos de clientes</p>
            ) : (
              <div className="space-y-2">
                {topClients.map((client, i) => (
                  <RankingItem
                    key={client.name}
                    position={i + 1}
                    name={client.name}
                    value={formatCurrency(client.income, true)}
                    subtitle={formatPercent(client.margin)}
                    subtitleClass={client.margin >= 0 ? 'text-emerald-600' : 'text-red-500'}
                    onClick={() => onNavigate('profitability')}
                  />
                ))}
              </div>
            )}
          </Card>

          {/* Top Projects */}
          <Card title="Top Proyectos" action="Ver todos" onAction={() => onNavigate('profitability')}>
            {topProjects.length === 0 ? (
              <p className="text-slate-400 text-center py-8">Sin datos de proyectos</p>
            ) : (
              <div className="space-y-2">
                {topProjects.map((project, i) => (
                  <RankingItem
                    key={project.name}
                    position={i + 1}
                    name={project.name}
                    subtitle2={project.client || 'Sin cliente'}
                    value={formatCurrency(project.income, true)}
                    subtitle={formatPercent(project.margin)}
                    subtitleClass={project.margin >= 0 ? 'text-emerald-600' : 'text-red-500'}
                    onClick={() => onNavigate('profitability')}
                  />
                ))}
              </div>
            )}
          </Card>

          {/* Pending Alert */}
          {pendingCount > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-4">
              <div className="w-10 h-10 bg-amber-500 rounded-lg flex items-center justify-center text-white">
                <AlertIcon className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-slate-900">{pendingCount} transacciones pendientes</p>
                <p className="text-sm text-slate-600">Requieren asignacion</p>
              </div>
              <button
                onClick={() => onNavigate('review')}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                Revisar
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Sub-components
function MetricCard({ label, value, valueClass = '', subtitle }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-md transition-shadow">
      <p className="text-slate-500 text-sm font-medium mb-2">{label}</p>
      <p className={`text-3xl font-bold font-mono mb-1 ${valueClass}`}>{value}</p>
      <p className="text-sm text-slate-400">{subtitle}</p>
    </div>
  );
}

function Card({ title, action, onAction, children }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
        <h3 className="font-semibold text-slate-900">{title}</h3>
        {action && (
          <button
            onClick={onAction}
            className="text-sm text-blue-600 font-medium hover:underline"
          >
            {action}
          </button>
        )}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function RankingItem({ position, name, subtitle2, value, subtitle, subtitleClass, onClick }) {
  const positionColors = [
    'bg-gradient-to-br from-amber-400 to-amber-500',
    'bg-gradient-to-br from-slate-400 to-slate-500',
    'bg-gradient-to-br from-orange-400 to-orange-500',
  ];

  return (
    <div
      onClick={onClick}
      className="flex items-center gap-3 p-2 -mx-2 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors"
    >
      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
        position <= 3 ? positionColors[position - 1] + ' text-white' : 'bg-slate-100 text-slate-500'
      }`}>
        {position}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-900 truncate">{name}</p>
        {subtitle2 && <p className="text-xs text-slate-500">{subtitle2}</p>}
      </div>
      <div className="text-right">
        <p className="font-semibold font-mono text-slate-900">{value}</p>
        <p className={`text-xs font-medium ${subtitleClass}`}>{subtitle}</p>
      </div>
    </div>
  );
}

function TrendIcon({ up }) {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d={up ? "M7 17l5-5 5 5M7 7l5 5 5-5" : "M7 7l5 5 5-5M7 17l5-5 5 5"} />
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
