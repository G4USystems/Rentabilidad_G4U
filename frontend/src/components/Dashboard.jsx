import { useMemo, useState, useEffect } from 'react';
import { formatCurrency, isIncome } from '../utils/format';

export default function Dashboard({ transactions, projects, clients, onNavigate }) {
  const [animate, setAnimate] = useState(false);

  useEffect(() => {
    setAnimate(true);
  }, []);

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

    return { income, expenses, net, margin };
  }, [transactions]);

  // Top clients
  const topClients = useMemo(() => {
    const clientMap = {};
    transactions.forEach(t => {
      const clientId = t.client_id || t.client;
      if (!clientId) return;
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
      .map(c => ({ ...c, net: c.income - c.expenses, margin: c.income > 0 ? ((c.income - c.expenses) / c.income) * 100 : 0 }))
      .sort((a, b) => b.income - a.income)
      .slice(0, 5);
  }, [transactions, clients]);

  // Top projects
  const topProjects = useMemo(() => {
    const projectMap = {};
    transactions.forEach(t => {
      const projId = t.project_id || t.project;
      if (!projId) return;
      const projInfo = projects.find(p => p.id === projId || p.name === projId);
      if (!projectMap[projId]) {
        projectMap[projId] = { id: projId, name: projInfo?.name || projId, client: projInfo?.client || '', income: 0, expenses: 0 };
      }
      if (isIncome(t)) {
        projectMap[projId].income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        projectMap[projId].expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });
    return Object.values(projectMap)
      .map(p => ({ ...p, net: p.income - p.expenses, margin: p.income > 0 ? ((p.income - p.expenses) / p.income) * 100 : 0 }))
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
    return Object.entries(cats)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, value], i) => ({
        name,
        value,
        percent: total > 0 ? (value / total) * 100 : 0,
        color: ['#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#6366F1'][i]
      }));
  }, [transactions]);

  const totalExpenses = categoryData.reduce((s, c) => s + c.value, 0);

  // Pending count
  const pendingCount = transactions.filter(t =>
    !t.project && !t.project_id && !t.client && !t.client_id && !t.excluded
  ).length;

  return (
    <div className="space-y-8">
      {/* Hero Section - Main KPI */}
      <div
        className={`relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8 transition-all duration-700 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
      >
        {/* Background Effects */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-1/4 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 right-1/3 w-48 h-48 bg-purple-500/10 rounded-full blur-2xl" />

        <div className="relative z-10">
          {/* Top Label */}
          <div className="flex items-center gap-3 mb-6">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
            <span className="text-slate-400 text-sm font-medium tracking-wide uppercase">Dashboard Ejecutivo</span>
          </div>

          {/* Main Grid */}
          <div className="grid grid-cols-12 gap-8 items-center">
            {/* Left - Main Metric */}
            <div className="col-span-5">
              <p className="text-slate-400 text-sm font-medium mb-2">Margen Neto del Periodo</p>
              <div className="flex items-baseline gap-4">
                <AnimatedNumber
                  value={metrics.margin}
                  suffix="%"
                  className="text-6xl font-bold text-white tracking-tight"
                  decimals={1}
                />
                <StatusBadge margin={metrics.margin} />
              </div>

              {/* Progress to goal */}
              <div className="mt-6">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-400">Progreso al objetivo (30%)</span>
                  <span className="text-white font-medium">{Math.min(100, Math.round((metrics.margin / 30) * 100))}%</span>
                </div>
                <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-emerald-500 rounded-full transition-all duration-1000"
                    style={{ width: `${Math.min(100, (metrics.margin / 30) * 100)}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Center - Divider */}
            <div className="col-span-1 flex justify-center">
              <div className="w-px h-32 bg-gradient-to-b from-transparent via-slate-600 to-transparent" />
            </div>

            {/* Right - Secondary Metrics */}
            <div className="col-span-6 grid grid-cols-3 gap-4">
              <MetricBox
                label="Ingresos"
                value={metrics.income}
                icon="↑"
                color="emerald"
              />
              <MetricBox
                label="Gastos"
                value={metrics.expenses}
                icon="↓"
                color="red"
              />
              <MetricBox
                label="Resultado"
                value={metrics.net}
                icon={metrics.net >= 0 ? "+" : "-"}
                color={metrics.net >= 0 ? "emerald" : "red"}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Secondary Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Column - Categories */}
        <div
          className={`col-span-7 bg-white rounded-2xl border border-slate-200 overflow-hidden transition-all duration-700 delay-100 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
          style={{ boxShadow: '0 4px 24px -4px rgba(0,0,0,0.08)' }}
        >
          <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Distribucion de Gastos</h3>
              <p className="text-sm text-slate-500 mt-0.5">Por categoria</p>
            </div>
            <button
              onClick={() => onNavigate('transactions')}
              className="text-sm text-blue-600 font-medium hover:text-blue-700 flex items-center gap-1 group"
            >
              Ver todo
              <span className="group-hover:translate-x-0.5 transition-transform">→</span>
            </button>
          </div>

          <div className="p-6">
            {categoryData.length === 0 ? (
              <EmptyState message="Sin datos de gastos" />
            ) : (
              <div className="flex gap-8">
                {/* Donut Chart */}
                <div className="relative w-48 h-48 flex-shrink-0">
                  <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                    {categoryData.reduce((acc, cat, i) => {
                      const circumference = 2 * Math.PI * 38;
                      const offset = acc.offset;
                      const dash = (cat.percent / 100) * circumference;
                      acc.elements.push(
                        <circle
                          key={cat.name}
                          cx="50"
                          cy="50"
                          r="38"
                          fill="none"
                          strokeWidth="10"
                          stroke={cat.color}
                          strokeDasharray={`${dash} ${circumference}`}
                          strokeDashoffset={-offset}
                          className="transition-all duration-700"
                          style={{ transitionDelay: `${i * 100}ms` }}
                        />
                      );
                      acc.offset += dash;
                      return acc;
                    }, { offset: 0, elements: [] }).elements}
                    <circle cx="50" cy="50" r="28" fill="white" />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-slate-900">{formatCurrency(totalExpenses, true)}</p>
                      <p className="text-xs text-slate-500 mt-1">Total</p>
                    </div>
                  </div>
                </div>

                {/* Legend */}
                <div className="flex-1 space-y-3">
                  {categoryData.map((cat, i) => (
                    <div
                      key={cat.name}
                      className="flex items-center gap-3 group cursor-pointer hover:bg-slate-50 -mx-2 px-2 py-1.5 rounded-lg transition-colors"
                    >
                      <div
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: cat.color }}
                      />
                      <span className="text-sm text-slate-700 flex-1 truncate group-hover:text-slate-900">{cat.name}</span>
                      <span className="text-sm font-semibold text-slate-900 font-mono">
                        {formatCurrency(cat.value, true)}
                      </span>
                      <span className="text-xs text-slate-400 w-12 text-right">
                        {cat.percent.toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Alert & Stats */}
        <div className="col-span-5 space-y-6">
          {/* Pending Alert */}
          {pendingCount > 0 && (
            <div
              className={`relative overflow-hidden rounded-2xl p-5 transition-all duration-700 delay-200 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
              style={{
                background: 'linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)',
                boxShadow: '0 4px 24px -4px rgba(245,158,11,0.25)'
              }}
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-amber-500 rounded-xl flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xl">⚡</span>
                </div>
                <div className="flex-1">
                  <p className="text-amber-900 font-semibold text-lg">{pendingCount} pendientes</p>
                  <p className="text-amber-700 text-sm mt-0.5">Transacciones sin asignar</p>
                </div>
              </div>
              <button
                onClick={() => onNavigate('review')}
                className="mt-4 w-full py-3 bg-amber-900 text-white font-semibold rounded-xl hover:bg-amber-800 transition-colors flex items-center justify-center gap-2"
              >
                <span>Revisar ahora</span>
                <span>→</span>
              </button>
            </div>
          )}

          {/* Quick Stats */}
          <div
            className={`bg-white rounded-2xl border border-slate-200 p-5 transition-all duration-700 delay-300 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
            style={{ boxShadow: '0 4px 24px -4px rgba(0,0,0,0.08)' }}
          >
            <h4 className="text-sm font-semibold text-slate-900 uppercase tracking-wide mb-4">Resumen</h4>
            <div className="space-y-4">
              <StatRow label="Clientes activos" value={clients.length} />
              <StatRow label="Proyectos" value={projects.length} />
              <StatRow label="Transacciones" value={transactions.length} />
              <StatRow label="Sin asignar" value={pendingCount} highlight={pendingCount > 0} />
            </div>
          </div>
        </div>
      </div>

      {/* Rankings Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Top Clients */}
        <RankingCard
          title="Top Clientes"
          subtitle="Por volumen de ingresos"
          items={topClients}
          onViewAll={() => onNavigate('profitability')}
          animate={animate}
          delay={400}
        />

        {/* Top Projects */}
        <RankingCard
          title="Top Proyectos"
          subtitle="Por volumen de ingresos"
          items={topProjects}
          showClient
          onViewAll={() => onNavigate('profitability')}
          animate={animate}
          delay={500}
        />
      </div>
    </div>
  );
}

// Animated Number Component
function AnimatedNumber({ value, suffix = '', prefix = '', className, decimals = 0 }) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const duration = 1000;
    const steps = 60;
    const increment = value / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= value) {
        setDisplayValue(value);
        clearInterval(timer);
      } else {
        setDisplayValue(current);
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [value]);

  return (
    <span className={className}>
      {prefix}{displayValue >= 0 ? '+' : ''}{displayValue.toFixed(decimals)}{suffix}
    </span>
  );
}

// Status Badge
function StatusBadge({ margin }) {
  const config = margin >= 20
    ? { bg: 'bg-emerald-500/20', text: 'text-emerald-400', label: 'Excelente' }
    : margin >= 0
    ? { bg: 'bg-amber-500/20', text: 'text-amber-400', label: 'Moderado' }
    : { bg: 'bg-red-500/20', text: 'text-red-400', label: 'Critico' };

  return (
    <span className={`${config.bg} ${config.text} px-3 py-1.5 rounded-full text-sm font-medium flex items-center gap-2`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
      {config.label}
    </span>
  );
}

// Metric Box
function MetricBox({ label, value, icon, color }) {
  const colorClasses = {
    emerald: 'text-emerald-400 bg-emerald-500/10',
    red: 'text-red-400 bg-red-500/10',
    blue: 'text-blue-400 bg-blue-500/10',
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur rounded-xl p-4 border border-slate-700/50">
      <div className="flex items-center gap-2 mb-2">
        <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs ${colorClasses[color]}`}>
          {icon}
        </span>
        <span className="text-slate-400 text-sm">{label}</span>
      </div>
      <p className={`text-2xl font-bold font-mono ${color === 'red' ? 'text-red-400' : 'text-emerald-400'}`}>
        {formatCurrency(Math.abs(value), true)}
      </p>
    </div>
  );
}

// Stat Row
function StatRow({ label, value, highlight }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <span className="text-sm text-slate-600">{label}</span>
      <span className={`text-lg font-bold ${highlight ? 'text-amber-600' : 'text-slate-900'}`}>
        {value}
      </span>
    </div>
  );
}

// Ranking Card
function RankingCard({ title, subtitle, items, showClient, onViewAll, animate, delay }) {
  const medals = ['🥇', '🥈', '🥉'];
  const maxIncome = items[0]?.income || 1;

  return (
    <div
      className={`bg-white rounded-2xl border border-slate-200 overflow-hidden transition-all duration-700 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
      style={{
        boxShadow: '0 4px 24px -4px rgba(0,0,0,0.08)',
        transitionDelay: `${delay}ms`
      }}
    >
      <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
          <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>
        </div>
        <button
          onClick={onViewAll}
          className="text-sm text-blue-600 font-medium hover:text-blue-700 flex items-center gap-1 group"
        >
          Ver todo
          <span className="group-hover:translate-x-0.5 transition-transform">→</span>
        </button>
      </div>

      <div className="p-4">
        {items.length === 0 ? (
          <EmptyState message="Sin datos" />
        ) : (
          <div className="space-y-2">
            {items.map((item, i) => (
              <div
                key={item.id}
                onClick={onViewAll}
                className="flex items-center gap-4 p-3 rounded-xl hover:bg-slate-50 cursor-pointer transition-colors group"
              >
                <div className="w-8 h-8 flex items-center justify-center text-lg">
                  {i < 3 ? medals[i] : <span className="text-sm font-bold text-slate-400">#{i + 1}</span>}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900 truncate group-hover:text-blue-600 transition-colors">
                    {item.name}
                  </p>
                  {showClient && item.client && (
                    <p className="text-xs text-slate-500 truncate">{item.client}</p>
                  )}
                  {/* Mini progress bar */}
                  <div className="mt-1.5 h-1 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all duration-500"
                      style={{ width: `${(item.income / maxIncome) * 100}%` }}
                    />
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold font-mono text-slate-900">{formatCurrency(item.income, true)}</p>
                  <p className={`text-xs font-semibold ${item.margin >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                    {item.margin >= 0 ? '+' : ''}{item.margin.toFixed(1)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Empty State
function EmptyState({ message }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-slate-400">
      <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
        <span className="text-2xl">📊</span>
      </div>
      <p className="font-medium">{message}</p>
    </div>
  );
}
