import { useMemo, useState } from 'react';
import { formatCurrency, formatDate, isIncome } from '../utils/format';

export default function Transactions({ transactions, projects, clients, onAssign }) {
  const [filters, setFilters] = useState({
    type: '',
    category: '',
    search: ''
  });
  const [page, setPage] = useState(1);
  const perPage = 20;

  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set(transactions.map(t => t.category || t.qonto_category).filter(Boolean));
    return [...cats].sort();
  }, [transactions]);

  // Filter transactions
  const filtered = useMemo(() => {
    return transactions
      .filter(t => {
        if (filters.type === 'income' && !isIncome(t)) return false;
        if (filters.type === 'expense' && isIncome(t)) return false;
        if (filters.category && (t.category || t.qonto_category) !== filters.category) return false;
        if (filters.search) {
          const q = filters.search.toLowerCase();
          const match =
            (t.counterparty_name || '').toLowerCase().includes(q) ||
            (t.label || '').toLowerCase().includes(q);
          if (!match) return false;
        }
        return true;
      })
      .sort((a, b) => new Date(b.settled_at || b.emitted_at) - new Date(a.settled_at || a.emitted_at));
  }, [transactions, filters]);

  // Stats
  const stats = useMemo(() => {
    const income = filtered.filter(t => isIncome(t)).reduce((s, t) => s + Math.abs(parseFloat(t.amount) || 0), 0);
    const expenses = filtered.filter(t => !isIncome(t)).reduce((s, t) => s + Math.abs(parseFloat(t.amount) || 0), 0);
    const unassigned = filtered.filter(t => !t.project && !t.project_id && !t.client && !t.client_id).length;
    return { total: filtered.length, income, expenses, unassigned };
  }, [filtered]);

  // Pagination
  const totalPages = Math.ceil(filtered.length / perPage);
  const paginated = filtered.slice((page - 1) * perPage, page * perPage);

  const updateFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1);
  };

  return (
    <div className="space-y-4">
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Total" value={stats.total} />
        <StatCard label="Ingresos" value={formatCurrency(stats.income, true)} color="emerald" />
        <StatCard label="Gastos" value={formatCurrency(stats.expenses, true)} color="red" />
        <StatCard label="Sin asignar" value={stats.unassigned} color="amber" />
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 flex flex-wrap gap-3 items-center">
        <select
          value={filters.type}
          onChange={e => updateFilter('type', e.target.value)}
          className="px-3 py-2 border border-slate-200 rounded-lg text-sm"
        >
          <option value="">Todos los tipos</option>
          <option value="income">Ingresos</option>
          <option value="expense">Gastos</option>
        </select>

        <select
          value={filters.category}
          onChange={e => updateFilter('category', e.target.value)}
          className="px-3 py-2 border border-slate-200 rounded-lg text-sm"
        >
          <option value="">Todas las categorias</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>

        <input
          type="text"
          placeholder="Buscar..."
          value={filters.search}
          onChange={e => updateFilter('search', e.target.value)}
          className="px-3 py-2 border border-slate-200 rounded-lg text-sm w-48"
        />

        <button
          onClick={() => { setFilters({ type: '', category: '', search: '' }); setPage(1); }}
          className="px-3 py-2 text-sm text-slate-500 hover:text-slate-700"
        >
          Limpiar
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Fecha</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Descripcion</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Categoria</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Proyecto</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Cliente</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Monto</th>
              <th className="w-12"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-slate-400">
                  No hay transacciones
                </td>
              </tr>
            ) : (
              paginated.map(tx => (
                <TxRow key={tx.id} tx={tx} projects={projects} clients={clients} onAssign={onAssign} />
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 bg-slate-50">
            <span className="text-sm text-slate-500">
              {(page - 1) * perPage + 1} - {Math.min(page * perPage, filtered.length)} de {filtered.length}
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 text-sm border rounded disabled:opacity-50"
              >
                Anterior
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 text-sm border rounded disabled:opacity-50"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, color = 'slate' }) {
  const colors = {
    slate: 'bg-slate-50 text-slate-900',
    emerald: 'bg-emerald-50 text-emerald-700',
    red: 'bg-red-50 text-red-600',
    amber: 'bg-amber-50 text-amber-700',
  };

  return (
    <div className={`rounded-lg p-4 ${colors[color]}`}>
      <p className="text-sm opacity-70">{label}</p>
      <p className="text-xl font-bold font-mono">{value}</p>
    </div>
  );
}

function TxRow({ tx, projects, clients, onAssign }) {
  const amount = parseFloat(tx.amount) || 0;
  const income = isIncome(tx);

  const projId = tx.project || tx.project_id;
  const clientId = tx.client || tx.client_id;
  const projInfo = projId ? projects.find(p => p.id === projId || p.name === projId) : null;
  const clientInfo = clientId ? clients.find(c => c.id === clientId || c.name === clientId) : null;
  const projName = projInfo?.name || (projId && !projId.startsWith('rec') ? projId : null);
  const clientName = clientInfo?.name || (clientId && !clientId.startsWith('rec') ? clientId : null);

  return (
    <tr className="hover:bg-slate-50">
      <td className="px-4 py-3 text-sm text-slate-600">
        {formatDate(tx.settled_at || tx.emitted_at)}
      </td>
      <td className="px-4 py-3">
        <p className="font-medium text-slate-900 truncate max-w-xs">
          {tx.counterparty_name || tx.label || '-'}
        </p>
      </td>
      <td className="px-4 py-3">
        <span className="text-sm text-slate-600">{tx.category || tx.qonto_category || '-'}</span>
      </td>
      <td className="px-4 py-3">
        {projName ? (
          <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">{projName}</span>
        ) : (
          <span className="text-slate-300">-</span>
        )}
      </td>
      <td className="px-4 py-3 text-sm text-slate-600">
        {clientName || <span className="text-slate-300">-</span>}
      </td>
      <td className={`px-4 py-3 text-right font-mono font-semibold ${income ? 'text-emerald-600' : 'text-red-500'}`}>
        {income ? '+' : ''}{formatCurrency(Math.abs(amount))}
      </td>
      <td className="px-4 py-3">
        <button
          onClick={() => onAssign(tx)}
          className="p-1 text-slate-400 hover:text-blue-600"
          title="Asignar"
        >
          ✏️
        </button>
      </td>
    </tr>
  );
}
