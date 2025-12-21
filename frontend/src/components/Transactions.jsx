import { useMemo, useState, useEffect } from 'react';
import { formatCurrency, formatDate, isIncome } from '../utils/format';

const ITEMS_PER_PAGE = 25;

export default function Transactions({ transactions, projects, clients, categories, onAssign }) {
  const [animate, setAnimate] = useState(false);
  const [filters, setFilters] = useState({
    type: '',
    category: '',
    project: '',
    client: '',
    search: ''
  });
  const [page, setPage] = useState(1);

  useEffect(() => {
    setAnimate(true);
  }, []);

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
  const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE);
  const paginatedItems = filtered.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  const updateFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters({ type: '', category: '', project: '', client: '', search: '' });
    setPage(1);
  };

  const activeFilters = Object.entries(filters).filter(([_, v]) => v !== '');

  return (
    <div className="space-y-6">
      {/* Header with Stats */}
      <div
        className={`grid grid-cols-4 gap-4 transition-all duration-500 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
      >
        <StatCard
          icon="📊"
          label="Total"
          value={stats.total.toString()}
          color="slate"
        />
        <StatCard
          icon="↑"
          label="Ingresos"
          value={formatCurrency(stats.income, true)}
          color="emerald"
        />
        <StatCard
          icon="↓"
          label="Gastos"
          value={formatCurrency(stats.expenses, true)}
          color="red"
        />
        <StatCard
          icon="⏳"
          label="Sin asignar"
          value={stats.unassigned.toString()}
          color="amber"
          highlight={stats.unassigned > 0}
        />
      </div>

      {/* Filters */}
      <div
        className={`bg-white rounded-2xl border border-slate-200 p-5 transition-all duration-500 delay-100 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
        style={{ boxShadow: '0 4px 24px -4px rgba(0,0,0,0.06)' }}
      >
        <div className="flex items-center gap-3 flex-wrap">
          {/* Type Filter */}
          <FilterButton
            active={filters.type === 'income'}
            onClick={() => updateFilter('type', filters.type === 'income' ? '' : 'income')}
            color="emerald"
          >
            <span>↑</span> Ingresos
          </FilterButton>
          <FilterButton
            active={filters.type === 'expense'}
            onClick={() => updateFilter('type', filters.type === 'expense' ? '' : 'expense')}
            color="red"
          >
            <span>↓</span> Gastos
          </FilterButton>

          <div className="w-px h-6 bg-slate-200 mx-1" />

          {/* Dropdowns */}
          <FilterSelect
            value={filters.category}
            onChange={e => updateFilter('category', e.target.value)}
            placeholder="Categoria"
          >
            {availableCategories.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </FilterSelect>

          <FilterSelect
            value={filters.project}
            onChange={e => updateFilter('project', e.target.value)}
            placeholder="Proyecto"
          >
            {projects.map(p => (
              <option key={p.id || p.name} value={p.id || p.name}>{p.name}</option>
            ))}
          </FilterSelect>

          <FilterSelect
            value={filters.client}
            onChange={e => updateFilter('client', e.target.value)}
            placeholder="Cliente"
          >
            {clients.map(c => (
              <option key={c.id || c.name} value={c.id || c.name}>{c.name}</option>
            ))}
          </FilterSelect>

          <div className="flex-1" />

          {/* Search */}
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar transacciones..."
              value={filters.search}
              onChange={e => updateFilter('search', e.target.value)}
              className="pl-10 pr-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-64 transition-all"
            />
          </div>
        </div>

        {/* Active Filters */}
        {activeFilters.length > 0 && (
          <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-100">
            <span className="text-sm text-slate-500">Filtros:</span>
            {activeFilters.map(([key, value]) => (
              <FilterChip
                key={key}
                label={getFilterLabel(key, value, projects, clients)}
                onRemove={() => updateFilter(key, '')}
              />
            ))}
            <button
              onClick={clearFilters}
              className="text-sm text-red-500 hover:text-red-600 font-medium ml-2"
            >
              Limpiar todo
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div
        className={`bg-white rounded-2xl border border-slate-200 overflow-hidden transition-all duration-500 delay-200 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
        style={{ boxShadow: '0 4px 24px -4px rgba(0,0,0,0.06)' }}
      >
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50/80">
                <th className="text-left px-5 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Fecha</th>
                <th className="text-left px-5 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Descripcion</th>
                <th className="text-left px-5 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Categoria</th>
                <th className="text-left px-5 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Proyecto</th>
                <th className="text-left px-5 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Cliente</th>
                <th className="text-right px-5 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Monto</th>
                <th className="px-5 py-4 w-14"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedItems.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-20">
                    <div className="flex flex-col items-center">
                      <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                        <span className="text-2xl">🔍</span>
                      </div>
                      <p className="text-slate-500 font-medium">No hay transacciones</p>
                      <p className="text-slate-400 text-sm mt-1">Ajusta los filtros para ver resultados</p>
                    </div>
                  </td>
                </tr>
              ) : (
                paginatedItems.map((tx, i) => (
                  <TransactionRow
                    key={tx.id}
                    tx={tx}
                    projects={projects}
                    clients={clients}
                    onAssign={onAssign}
                    delay={i * 20}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-4 border-t border-slate-100 bg-slate-50/50">
            <p className="text-sm text-slate-500">
              Mostrando <span className="font-medium text-slate-700">{(page - 1) * ITEMS_PER_PAGE + 1}</span>
              {' - '}
              <span className="font-medium text-slate-700">{Math.min(page * ITEMS_PER_PAGE, filtered.length)}</span>
              {' de '}
              <span className="font-medium text-slate-700">{filtered.length}</span>
            </p>
            <div className="flex items-center gap-1">
              <PaginationButton
                onClick={() => setPage(1)}
                disabled={page === 1}
              >
                ««
              </PaginationButton>
              <PaginationButton
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                «
              </PaginationButton>

              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (page <= 3) {
                  pageNum = i + 1;
                } else if (page >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = page - 2 + i;
                }
                return (
                  <PaginationButton
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    active={page === pageNum}
                  >
                    {pageNum}
                  </PaginationButton>
                );
              })}

              <PaginationButton
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                »
              </PaginationButton>
              <PaginationButton
                onClick={() => setPage(totalPages)}
                disabled={page === totalPages}
              >
                »»
              </PaginationButton>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color, highlight }) {
  const colors = {
    slate: 'bg-slate-50 border-slate-200 text-slate-900',
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    red: 'bg-red-50 border-red-200 text-red-600',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
  };

  return (
    <div
      className={`rounded-2xl border p-5 ${colors[color]} transition-all hover:scale-[1.02] ${
        highlight ? 'ring-2 ring-amber-400 ring-offset-2' : ''
      }`}
      style={{ boxShadow: '0 2px 8px -2px rgba(0,0,0,0.05)' }}
    >
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-white/80 rounded-xl flex items-center justify-center text-lg">
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

function FilterButton({ children, active, onClick, color }) {
  const colors = {
    emerald: active
      ? 'bg-emerald-100 text-emerald-700 border-emerald-300'
      : 'bg-white text-slate-600 border-slate-200 hover:border-emerald-300 hover:text-emerald-600',
    red: active
      ? 'bg-red-100 text-red-700 border-red-300'
      : 'bg-white text-slate-600 border-slate-200 hover:border-red-300 hover:text-red-600',
  };

  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-xl border flex items-center gap-2 transition-all ${colors[color]}`}
    >
      {children}
    </button>
  );
}

function FilterSelect({ value, onChange, placeholder, children }) {
  return (
    <select
      value={value}
      onChange={onChange}
      className={`px-4 py-2.5 border rounded-xl text-sm transition-all cursor-pointer ${
        value
          ? 'bg-blue-50 border-blue-300 text-blue-700'
          : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'
      } focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
    >
      <option value="">{placeholder}</option>
      {children}
    </select>
  );
}

function FilterChip({ label, onRemove }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-100 text-blue-700 text-sm rounded-full">
      {label}
      <button
        onClick={onRemove}
        className="w-4 h-4 rounded-full bg-blue-200 hover:bg-blue-300 flex items-center justify-center text-xs transition-colors"
      >
        ×
      </button>
    </span>
  );
}

function getFilterLabel(key, value, projects, clients) {
  switch (key) {
    case 'type':
      return value === 'income' ? 'Ingresos' : 'Gastos';
    case 'project':
      return projects.find(p => p.id === value || p.name === value)?.name || value;
    case 'client':
      return clients.find(c => c.id === value || c.name === value)?.name || value;
    case 'search':
      return `"${value}"`;
    default:
      return value;
  }
}

function TransactionRow({ tx, projects, clients, onAssign, delay }) {
  const amount = parseFloat(tx.amount) || 0;
  const income = isIncome(tx);
  const projId = tx.project || tx.project_id;
  const clientId = tx.client || tx.client_id;

  // Resolve IDs to names
  const projInfo = projId ? projects.find(p => p.id === projId || p.name === projId) : null;
  const clientInfo = clientId ? clients.find(c => c.id === clientId || c.name === clientId) : null;
  const projName = projInfo?.name || (projId && !projId.startsWith('rec') ? projId : null);
  const clientName = clientInfo?.name || (clientId && !clientId.startsWith('rec') ? clientId : null);

  const isUnassigned = !projId && !clientId;

  return (
    <tr
      className={`hover:bg-slate-50/80 transition-colors group ${isUnassigned ? 'bg-amber-50/30' : ''}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <td className="px-5 py-4 whitespace-nowrap">
        <div className="text-sm font-medium text-slate-900">
          {formatDate(tx.settled_at || tx.emitted_at)}
        </div>
      </td>
      <td className="px-5 py-4 max-w-xs">
        <p className="font-medium text-slate-900 truncate">{tx.counterparty_name || tx.label || '-'}</p>
        {tx.note && <p className="text-sm text-slate-500 truncate mt-0.5">{tx.note}</p>}
      </td>
      <td className="px-5 py-4">
        {tx.category || tx.qonto_category ? (
          <span className="inline-flex items-center px-2.5 py-1 bg-slate-100 text-slate-700 rounded-lg text-xs font-medium">
            {tx.category || tx.qonto_category}
          </span>
        ) : (
          <span className="text-slate-300">-</span>
        )}
      </td>
      <td className="px-5 py-4">
        {projName ? (
          <span className="inline-flex items-center px-2.5 py-1 bg-blue-100 text-blue-700 rounded-lg text-xs font-medium">
            {projName}
          </span>
        ) : (
          <span className="text-slate-300">-</span>
        )}
      </td>
      <td className="px-5 py-4">
        {clientName ? (
          <span className="text-sm text-slate-700">{clientName}</span>
        ) : (
          <span className="text-slate-300">-</span>
        )}
      </td>
      <td className={`px-5 py-4 text-right font-mono font-semibold whitespace-nowrap ${
        income ? 'text-emerald-600' : 'text-red-500'
      }`}>
        <span className="inline-flex items-center gap-1">
          {income ? '↑' : '↓'}
          {formatCurrency(Math.abs(amount))}
        </span>
      </td>
      <td className="px-5 py-4">
        <button
          onClick={() => onAssign(tx)}
          className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
          title="Asignar"
        >
          <EditIcon className="w-4 h-4" />
        </button>
      </td>
    </tr>
  );
}

function PaginationButton({ children, onClick, disabled, active }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`min-w-[36px] h-9 px-3 text-sm font-medium rounded-lg transition-all ${
        active
          ? 'bg-blue-600 text-white'
          : disabled
          ? 'text-slate-300 cursor-not-allowed'
          : 'text-slate-600 hover:bg-slate-100'
      }`}
    >
      {children}
    </button>
  );
}

function SearchIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8"/>
      <path d="m21 21-4.35-4.35"/>
    </svg>
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
