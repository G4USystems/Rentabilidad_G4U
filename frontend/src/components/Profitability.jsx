import { useMemo, useState } from 'react';
import { formatCurrency, formatPercent, isIncome } from '../utils/format';

export default function Profitability({ transactions, projects, clients }) {
  const [tab, setTab] = useState('clients');

  // Client profitability
  const clientData = useMemo(() => {
    const data = {};
    transactions.forEach(t => {
      const client = t.client || t.client_id;
      if (!client) return;
      const info = clients.find(c => c.id === client || c.name === client);
      if (!data[client]) {
        data[client] = { name: info?.name || client, income: 0, expenses: 0 };
      }
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
        margin: c.income > 0 ? ((c.income - c.expenses) / c.income) * 100 : 0
      }))
      .sort((a, b) => b.income - a.income);
  }, [transactions, clients]);

  // Project profitability
  const projectData = useMemo(() => {
    const data = {};
    transactions.forEach(t => {
      const proj = t.project || t.project_id;
      if (!proj) return;
      const info = projects.find(p => p.id === proj || p.name === proj);
      if (!data[proj]) {
        data[proj] = { name: info?.name || proj, client: info?.client || '', income: 0, expenses: 0 };
      }
      if (isIncome(t)) {
        data[proj].income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        data[proj].expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });
    return Object.values(data)
      .map(p => ({
        ...p,
        net: p.income - p.expenses,
        margin: p.income > 0 ? ((p.income - p.expenses) / p.income) * 100 : 0
      }))
      .sort((a, b) => b.income - a.income);
  }, [transactions, projects]);

  const items = tab === 'clients' ? clientData : projectData;

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex gap-2 bg-slate-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setTab('clients')}
          className={`px-4 py-2 text-sm font-medium rounded ${
            tab === 'clients' ? 'bg-white shadow-sm' : 'text-slate-600'
          }`}
        >
          Por Cliente
        </button>
        <button
          onClick={() => setTab('projects')}
          className={`px-4 py-2 text-sm font-medium rounded ${
            tab === 'projects' ? 'bg-white shadow-sm' : 'text-slate-600'
          }`}
        >
          Por Proyecto
        </button>
      </div>

      {/* Grid */}
      {items.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          No hay datos para mostrar
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {items.map((item, i) => (
            <ProfitCard key={i} item={item} isProject={tab === 'projects'} />
          ))}
        </div>
      )}
    </div>
  );
}

function ProfitCard({ item, isProject }) {
  const marginColor = item.margin >= 20 ? 'text-emerald-600' : item.margin >= 0 ? 'text-amber-600' : 'text-red-600';
  const barColor = item.margin >= 20 ? 'bg-emerald-500' : item.margin >= 0 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold truncate">{item.name}</h3>
          {isProject && item.client && (
            <p className="text-sm text-slate-500 truncate">{item.client}</p>
          )}
        </div>
        <span className={`text-xl font-bold font-mono ${marginColor}`}>
          {formatPercent(item.margin)}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center mb-3">
        <div className="p-2 bg-slate-50 rounded">
          <p className="text-xs text-slate-500">Ingresos</p>
          <p className="text-sm font-semibold text-emerald-600 font-mono">{formatCurrency(item.income, true)}</p>
        </div>
        <div className="p-2 bg-slate-50 rounded">
          <p className="text-xs text-slate-500">Gastos</p>
          <p className="text-sm font-semibold text-red-500 font-mono">{formatCurrency(item.expenses, true)}</p>
        </div>
        <div className="p-2 bg-slate-50 rounded">
          <p className="text-xs text-slate-500">Neto</p>
          <p className={`text-sm font-semibold font-mono ${item.net >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
            {formatCurrency(item.net, true)}
          </p>
        </div>
      </div>

      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${barColor} rounded-full`}
          style={{ width: `${Math.min(Math.abs(item.margin), 100)}%` }}
        />
      </div>
    </div>
  );
}
