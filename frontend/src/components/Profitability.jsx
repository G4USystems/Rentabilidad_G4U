import { useMemo, useState, useEffect } from 'react';
import { formatCurrency, formatPercent, isIncome } from '../utils/format';

export default function Profitability({ transactions, projects, clients }) {
  const [animate, setAnimate] = useState(false);
  const [tab, setTab] = useState('clients');
  const [sortBy, setSortBy] = useState('income');
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    setAnimate(true);
  }, []);

  // Calculate client profitability
  const clientData = useMemo(() => {
    const data = {};
    transactions.forEach(t => {
      const client = t.client || t.client_id;
      if (!client) return;

      const info = clients.find(c => c.id === client || c.name === client);
      if (!data[client]) {
        data[client] = { id: client, name: info?.name || client, income: 0, expenses: 0, transactions: [] };
      }

      data[client].transactions.push(t);
      if (isIncome(t)) {
        data[client].income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        data[client].expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });

    return Object.values(data)
      .map(c => ({
        ...c,
        net: c.income - c.expenses,
        margin: c.income > 0 ? ((c.income - c.expenses) / c.income) * 100 : 0,
        txCount: c.transactions.length
      }))
      .sort((a, b) => sortBy === 'margin' ? b.margin - a.margin : b.income - a.income);
  }, [transactions, clients, sortBy]);

  // Calculate project profitability
  const projectData = useMemo(() => {
    const data = {};
    transactions.forEach(t => {
      const proj = t.project || t.project_id;
      if (!proj) return;

      const info = projects.find(p => p.id === proj || p.name === proj);
      if (!data[proj]) {
        data[proj] = {
          id: proj,
          name: info?.name || proj,
          client: info?.client || '',
          status: info?.status || 'Active',
          income: 0,
          expenses: 0,
          transactions: []
        };
      }

      data[proj].transactions.push(t);
      if (isIncome(t)) {
        data[proj].income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        data[proj].expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });

    // Add projects without transactions
    projects.forEach(p => {
      const key = p.id || p.name;
      if (!data[key]) {
        data[key] = {
          id: key,
          name: p.name,
          client: p.client || '',
          status: p.status || 'Active',
          income: 0,
          expenses: 0,
          transactions: []
        };
      }
    });

    return Object.values(data)
      .map(p => ({
        ...p,
        net: p.income - p.expenses,
        margin: p.income > 0 ? ((p.income - p.expenses) / p.income) * 100 : 0,
        txCount: p.transactions.length
      }))
      .sort((a, b) => sortBy === 'margin' ? b.margin - a.margin : b.income - a.income);
  }, [transactions, projects, sortBy]);

  const items = tab === 'clients' ? clientData : projectData;

  // Totals
  const totals = useMemo(() => {
    const income = items.reduce((s, i) => s + i.income, 0);
    const expenses = items.reduce((s, i) => s + i.expenses, 0);
    const net = income - expenses;
    const margin = income > 0 ? (net / income) * 100 : 0;
    return { income, expenses, net, margin };
  }, [items]);

  const maxIncome = Math.max(...items.map(i => i.income), 1);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div
        className={`flex items-center justify-between transition-all duration-500 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
      >
        {/* Tab Selector */}
        <div className="flex gap-1 bg-slate-100 p-1 rounded-xl">
          <button
            onClick={() => { setTab('clients'); setExpanded(null); }}
            className={`px-6 py-2.5 text-sm font-medium rounded-lg transition-all ${
              tab === 'clients'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Por Cliente
          </button>
          <button
            onClick={() => { setTab('projects'); setExpanded(null); }}
            className={`px-6 py-2.5 text-sm font-medium rounded-lg transition-all ${
              tab === 'projects'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Por Proyecto
          </button>
        </div>

        {/* Sort */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-500">Ordenar por:</span>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="text-sm border border-slate-200 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
          >
            <option value="income">Ingresos</option>
            <option value="margin">Margen</option>
          </select>
        </div>
      </div>

      {/* Summary Cards */}
      <div
        className={`grid grid-cols-4 gap-4 transition-all duration-500 delay-100 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
      >
        <SummaryCard
          label="Total Ingresos"
          value={formatCurrency(totals.income, true)}
          icon="↑"
          color="emerald"
        />
        <SummaryCard
          label="Total Gastos"
          value={formatCurrency(totals.expenses, true)}
          icon="↓"
          color="red"
        />
        <SummaryCard
          label="Resultado Neto"
          value={formatCurrency(totals.net, true)}
          icon={totals.net >= 0 ? '+' : '-'}
          color={totals.net >= 0 ? 'blue' : 'red'}
        />
        <SummaryCard
          label="Margen Promedio"
          value={formatPercent(totals.margin)}
          icon="%"
          color={totals.margin >= 20 ? 'emerald' : totals.margin >= 0 ? 'amber' : 'red'}
        />
      </div>

      {/* Grid */}
      {items.length === 0 ? (
        <div
          className={`text-center py-20 bg-white rounded-2xl border border-slate-200 transition-all duration-500 delay-200 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
          style={{ boxShadow: '0 4px 24px -4px rgba(0,0,0,0.06)' }}
        >
          <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">📊</span>
          </div>
          <p className="text-slate-700 font-medium text-lg">No hay datos para mostrar</p>
          <p className="text-slate-500 mt-1">Asigna transacciones a {tab === 'clients' ? 'clientes' : 'proyectos'}</p>
        </div>
      ) : (
        <div
          className={`space-y-3 transition-all duration-500 delay-200 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
        >
          {items.map((item, i) => (
            <ProfitabilityCard
              key={item.id}
              item={item}
              isProject={tab === 'projects'}
              maxIncome={maxIncome}
              rank={i + 1}
              expanded={expanded === item.id}
              onToggle={() => setExpanded(expanded === item.id ? null : item.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, icon, color }) {
  const colors = {
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    red: 'bg-red-50 border-red-200 text-red-600',
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
  };

  const iconColors = {
    emerald: 'bg-emerald-100 text-emerald-600',
    red: 'bg-red-100 text-red-600',
    blue: 'bg-blue-100 text-blue-600',
    amber: 'bg-amber-100 text-amber-600',
  };

  return (
    <div
      className={`rounded-2xl border p-5 ${colors[color]}`}
      style={{ boxShadow: '0 2px 8px -2px rgba(0,0,0,0.05)' }}
    >
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg font-bold ${iconColors[color]}`}>
          {icon}
        </div>
        <div>
          <p className="text-sm font-medium opacity-70">{label}</p>
          <p className="text-xl font-bold font-mono">{value}</p>
        </div>
      </div>
    </div>
  );
}

function ProfitabilityCard({ item, isProject, maxIncome, rank, expanded, onToggle }) {
  const marginClass = item.margin >= 20
    ? 'text-emerald-600 bg-emerald-50'
    : item.margin >= 0
    ? 'text-amber-600 bg-amber-50'
    : 'text-red-600 bg-red-50';

  const barWidth = (item.income / maxIncome) * 100;
  const barClass = item.margin >= 20 ? 'bg-emerald-500' : item.margin >= 0 ? 'bg-amber-500' : 'bg-red-500';

  const medals = ['🥇', '🥈', '🥉'];

  return (
    <div
      className="bg-white border border-slate-200 rounded-2xl overflow-hidden transition-all hover:shadow-md"
      style={{ boxShadow: '0 2px 8px -2px rgba(0,0,0,0.05)' }}
    >
      <div
        className="p-5 cursor-pointer"
        onClick={onToggle}
      >
        <div className="flex items-center gap-4">
          {/* Rank */}
          <div className="w-10 h-10 flex items-center justify-center flex-shrink-0">
            {rank <= 3 ? (
              <span className="text-2xl">{medals[rank - 1]}</span>
            ) : (
              <span className="text-lg font-bold text-slate-400">#{rank}</span>
            )}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <h3 className="font-semibold text-slate-900 truncate">{item.name}</h3>
              {isProject && item.status && (
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                  item.status === 'Active' ? 'bg-emerald-100 text-emerald-700' :
                  item.status === 'Completed' ? 'bg-blue-100 text-blue-700' :
                  'bg-slate-100 text-slate-700'
                }`}>
                  {item.status}
                </span>
              )}
            </div>
            {isProject && item.client && (
              <p className="text-sm text-slate-500 truncate">{item.client}</p>
            )}
            <p className="text-xs text-slate-400 mt-1">{item.txCount} transacciones</p>
          </div>

          {/* Metrics */}
          <div className="flex items-center gap-6">
            <div className="text-right">
              <p className="text-xs text-slate-500">Ingresos</p>
              <p className="font-bold font-mono text-emerald-600">{formatCurrency(item.income, true)}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500">Gastos</p>
              <p className="font-bold font-mono text-red-500">{formatCurrency(item.expenses, true)}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500">Resultado</p>
              <p className={`font-bold font-mono ${item.net >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                {formatCurrency(item.net, true)}
              </p>
            </div>
            <div className={`px-4 py-2 rounded-xl ${marginClass}`}>
              <p className="text-xs font-medium opacity-70">Margen</p>
              <p className="text-xl font-bold font-mono">{formatPercent(item.margin)}</p>
            </div>
          </div>

          {/* Toggle */}
          <button
            className={`w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 transition-all ${
              expanded ? 'rotate-180' : ''
            }`}
          >
            <ChevronIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Progress Bar */}
        <div className="mt-4 h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full ${barClass} rounded-full transition-all duration-500`}
            style={{ width: `${barWidth}%` }}
          />
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && item.transactions.length > 0 && (
        <div className="px-5 pb-5 border-t border-slate-100">
          <div className="bg-slate-50 rounded-xl p-4 mt-4">
            <h4 className="text-sm font-semibold text-slate-700 mb-3">Ultimas transacciones</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {item.transactions.slice(0, 10).map(tx => (
                <div key={tx.id} className="flex items-center justify-between py-2 border-b border-slate-200 last:border-0">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      {tx.counterparty_name || tx.label || '-'}
                    </p>
                    <p className="text-xs text-slate-500">{tx.settled_at?.split('T')[0]}</p>
                  </div>
                  <span className={`font-mono font-semibold text-sm ${isIncome(tx) ? 'text-emerald-600' : 'text-red-500'}`}>
                    {isIncome(tx) ? '+' : ''}{formatCurrency(Math.abs(parseFloat(tx.amount) || 0), true)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ChevronIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="m6 9 6 6 6-6"/>
    </svg>
  );
}
