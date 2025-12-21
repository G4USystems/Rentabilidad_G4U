import { useMemo, useState } from 'react';
import { formatCurrency, formatDate, isIncome } from '../utils/format';

export default function Transactions({ transactions, projects, clients, categories, onAssign }) {
  const [filters, setFilters] = useState({
    type: '',
    category: '',
    project: '',
    client: '',
    search: ''
  });

  // Get unique categories from transactions
  const availableCategories = useMemo(() => {
    const cats = new Set(transactions.map(t => t.category || t.qonto_category).filter(Boolean));
    return [...cats].sort();
  }, [transactions]);

  // Filtered transactions
  const filtered = useMemo(() => {
    return transactions
      .filter(t => {
        if (filters.type === 'income' && !isIncome(t)) return false;
        if (filters.type === 'expense' && isIncome(t)) return false;
        if (filters.category && (t.category || t.qonto_category) !== filters.category) return false;
        if (filters.project && (t.project || t.project_id) !== filters.project) return false;
        if (filters.client && (t.client || t.client_id) !== filters.client) return false;
        if (filters.search) {
          const q = filters.search.toLowerCase();
          const match =
            (t.counterparty_name || '').toLowerCase().includes(q) ||
            (t.label || '').toLowerCase().includes(q) ||
            (t.note || '').toLowerCase().includes(q);
          if (!match) return false;
        }
        return true;
      })
      .sort((a, b) => new Date(b.settled_at || b.emitted_at) - new Date(a.settled_at || a.emitted_at))
      .slice(0, 100);
  }, [transactions, filters]);

  // Stats
  const stats = useMemo(() => {
    const income = filtered.filter(t => isIncome(t)).reduce((s, t) => s + Math.abs(parseFloat(t.amount) || 0), 0);
    const expenses = filtered.filter(t => !isIncome(t)).reduce((s, t) => s + Math.abs(parseFloat(t.amount) || 0), 0);
    const unassigned = filtered.filter(t => !t.project && !t.project_id && !t.client && !t.client_id).length;
    return { total: filtered.length, income, expenses, unassigned };
  }, [filtered]);

  const updateFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setFilters({ type: '', category: '', project: '', client: '', search: '' });
  };

  return (
    <div className="animate-fadeIn">
      {/* Filters */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 mb-4 flex flex-wrap gap-3">
        <select
          value={filters.type}
          onChange={e => updateFilter('type', e.target.value)}
          className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">Todos los tipos</option>
          <option value="income">Ingresos</option>
          <option value="expense">Gastos</option>
        </select>

        <select
          value={filters.category}
          onChange={e => updateFilter('category', e.target.value)}
          className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">Todas las categorias</option>
          {availableCategories.map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        <select
          value={filters.project}
          onChange={e => updateFilter('project', e.target.value)}
          className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">Todos los proyectos</option>
          {projects.map(p => (
            <option key={p.id || p.name} value={p.id || p.name}>{p.name}</option>
          ))}
        </select>

        <select
          value={filters.client}
          onChange={e => updateFilter('client', e.target.value)}
          className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">Todos los clientes</option>
          {clients.map(c => (
            <option key={c.id || c.name} value={c.id || c.name}>{c.name}</option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Buscar..."
          value={filters.search}
          onChange={e => updateFilter('search', e.target.value)}
          className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[200px]"
        />

        <button
          onClick={clearFilters}
          className="px-3 py-2 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
        >
          Limpiar
        </button>
      </div>

      {/* Quick Stats */}
      <div className="flex gap-8 p-4 bg-white border border-slate-200 rounded-xl mb-4">
        <Stat label="Total" value={stats.total.toString()} />
        <Stat label="Ingresos" value={formatCurrency(stats.income)} valueClass="text-emerald-600" />
        <Stat label="Gastos" value={formatCurrency(stats.expenses)} valueClass="text-red-500" />
        <Stat label="Sin asignar" value={stats.unassigned.toString()} />
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Fecha</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Descripcion</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Categoria</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Proyecto</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Cliente</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Monto</th>
              <th className="px-4 py-3 w-12"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-16 text-slate-400">
                  No hay transacciones
                </td>
              </tr>
            ) : (
              filtered.map(tx => (
                <TransactionRow key={tx.id} tx={tx} projects={projects} clients={clients} onAssign={onAssign} />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value, valueClass = '' }) {
  return (
    <div>
      <p className={`text-xl font-bold font-mono ${valueClass}`}>{value}</p>
      <p className="text-sm text-slate-500">{label}</p>
    </div>
  );
}

function TransactionRow({ tx, projects, clients, onAssign }) {
  const amount = parseFloat(tx.amount) || 0;
  const income = isIncome(tx);
  const projId = tx.project || tx.project_id;
  const clientId = tx.client || tx.client_id;

  // Resolve IDs to names
  const projInfo = projId ? projects.find(p => p.id === projId || p.name === projId) : null;
  const clientInfo = clientId ? clients.find(c => c.id === clientId || c.name === clientId) : null;
  const projName = projInfo?.name || (projId && !projId.startsWith('rec') ? projId : null);
  const clientName = clientInfo?.name || (clientId && !clientId.startsWith('rec') ? clientId : null);

  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
      <td className="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">
        {formatDate(tx.settled_at || tx.emitted_at)}
      </td>
      <td className="px-4 py-3 max-w-xs">
        <p className="font-medium text-slate-900 truncate">{tx.counterparty_name || tx.label || '-'}</p>
        {tx.note && <p className="text-sm text-slate-500 truncate">{tx.note}</p>}
      </td>
      <td className="px-4 py-3">
        <span className="inline-block px-2 py-1 bg-slate-100 rounded text-xs text-slate-700">
          {tx.category || tx.qonto_category || '-'}
        </span>
      </td>
      <td className="px-4 py-3 text-sm">
        {projName ? (
          <span className="inline-block px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">
            {projName}
          </span>
        ) : (
          <span className="text-slate-400">-</span>
        )}
      </td>
      <td className="px-4 py-3 text-sm text-slate-700">
        {clientName || <span className="text-slate-400">-</span>}
      </td>
      <td className={`px-4 py-3 text-right font-mono font-semibold whitespace-nowrap ${income ? 'text-emerald-600' : 'text-red-500'}`}>
        {income ? '+' : ''}{formatCurrency(amount)}
      </td>
      <td className="px-4 py-3">
        <button
          onClick={() => onAssign(tx)}
          className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          title="Asignar"
        >
          <EditIcon className="w-4 h-4" />
        </button>
      </td>
    </tr>
  );
}

function EditIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
    </svg>
  );
}
