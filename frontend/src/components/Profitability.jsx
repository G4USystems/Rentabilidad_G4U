import { useMemo, useState } from 'react';
import { formatCurrency, formatPercent, isIncome } from '../utils/format';

export default function Profitability({ transactions, projects, clients }) {
  const [tab, setTab] = useState('clients');

  // Calculate client profitability
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

  // Calculate project profitability
  const projectData = useMemo(() => {
    const data = {};
    transactions.forEach(t => {
      const proj = t.project || t.project_id;
      if (!proj) return;

      const info = projects.find(p => p.id === proj || p.name === proj);
      if (!data[proj]) {
        data[proj] = {
          name: info?.name || proj,
          client: info?.client || '',
          status: info?.status || 'Active',
          income: 0,
          expenses: 0
        };
      }

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
          name: p.name,
          client: p.client || '',
          status: p.status || 'Active',
          income: 0,
          expenses: 0
        };
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
    <div className="animate-fadeIn">
      {/* Tab Selector */}
      <div className="flex gap-1 bg-slate-100 p-1 rounded-lg w-fit mb-6">
        <button
          onClick={() => setTab('clients')}
          className={`px-6 py-2 text-sm font-medium rounded-md transition-all ${
            tab === 'clients'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          Por Cliente
        </button>
        <button
          onClick={() => setTab('projects')}
          className={`px-6 py-2 text-sm font-medium rounded-md transition-all ${
            tab === 'projects'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map(item => (
            <ProfitabilityCard
              key={item.name}
              item={item}
              isProject={tab === 'projects'}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ProfitabilityCard({ item, isProject }) {
  const marginClass = item.margin >= 0 ? 'text-emerald-600' : 'text-red-500';
  const barClass = item.margin >= 0 ? 'bg-emerald-500' : 'bg-red-500';
  const barWidth = Math.min(Math.abs(item.margin), 100);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md hover:border-blue-300 transition-all cursor-pointer">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-slate-900">{item.name}</h3>
          {isProject && item.client && (
            <p className="text-sm text-slate-500">{item.client}</p>
          )}
        </div>
        <span className={`text-xl font-bold font-mono ${marginClass}`}>
          {formatPercent(item.margin)}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <StatBox
          label="Ingresos"
          value={formatCurrency(item.income, true)}
          valueClass="text-emerald-600"
        />
        <StatBox
          label="Gastos"
          value={formatCurrency(item.expenses, true)}
          valueClass="text-red-500"
        />
        <StatBox
          label="Resultado"
          value={formatCurrency(item.net, true)}
          valueClass={marginClass}
        />
      </div>

      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${barClass} rounded-full transition-all duration-500`}
          style={{ width: `${barWidth}%` }}
        />
      </div>
    </div>
  );
}

function StatBox({ label, value, valueClass = '' }) {
  return (
    <div className="text-center p-2 bg-slate-50 rounded-lg">
      <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
      <p className={`text-sm font-semibold font-mono mt-1 ${valueClass}`}>{value}</p>
    </div>
  );
}
